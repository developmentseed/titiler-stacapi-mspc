"""titiler-stacapi Asset Reader."""

import warnings
from typing import Any, Dict, Optional, Sequence, Set, Type, Union

import attr
import rasterio
from morecantile import TileMatrixSet
from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.errors import (
    AssetAsBandError,
    ExpressionMixingWarning,
    InvalidAssetName,
    MissingAssets,
    TileOutsideBounds,
)
from rio_tiler.io import Reader
from rio_tiler.io.base import BaseReader, MultiBaseReader
from rio_tiler.models import ImageData
from rio_tiler.tasks import multi_arrays
from rio_tiler.types import Indexes

from titiler.stacapi.models import AssetInfo
from titiler.stacapi.settings import CacheSettings, RetrySettings, STACSettings
from titiler.stacapi.xarray import XarrayReader

cache_config = CacheSettings()
retry_config = RetrySettings()
stac_config = STACSettings()

valid_types = {
    "image/tiff; application=geotiff",
    "image/tiff; application=geotiff; profile=cloud-optimized",
    "image/tiff; profile=cloud-optimized; application=geotiff",
    "image/vnd.stac.geotiff; cloud-optimized=true",
    "image/tiff",
    "image/x.geotiff",
    "image/jp2",
    "application/x-hdf5",
    "application/x-hdf",
    "application/vnd+zarr",
    "application/x-netcdf",
}


@attr.s
class AssetReader(MultiBaseReader):
    """
    Asset reader for STAC items.
    """

    input: Any = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib()
    maxzoom: int = attr.ib()

    reader: Type[BaseReader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    ctx: Any = attr.ib(default=rasterio.Env)

    include_asset_types: Set[str] = attr.ib(default=valid_types)

    @minzoom.default
    def _minzoom(self):
        return self.tms.minzoom

    @maxzoom.default
    def _maxzoom(self):
        return self.tms.maxzoom

    def _get_reader(self, asset_info: AssetInfo) -> Type[BaseReader]:
        """Get Asset Reader."""
        asset_type = asset_info.get("type", None)

        if asset_type and asset_type in [
            "application/x-hdf5",
            "application/x-hdf",
            "application/vnd.zarr",
            "application/x-netcdf",
            "application/netcdf",
        ]:
            return XarrayReader

        return Reader

    def _get_asset_info(self, asset: str) -> AssetInfo:
        """
        Validate asset names and return asset's info.

        Args:
            asset (str): asset name.

        Returns:
            AssetInfo: Asset info

        """
        if asset not in self.assets:
            raise InvalidAssetName(
                f"{asset} is not valid. Should be one of {self.assets}"
            )

        asset_info = self.input["assets"][asset]

        url = asset_info["href"]
        if alternate := stac_config.alternate_url:
            url = asset_info["alternate"][alternate]["href"]

        info = AssetInfo(url=url, env={})

        if asset_info.get("type"):
            info["type"] = asset_info["type"]

        if header_size := asset_info.get("file:header_size"):
            info["env"]["GDAL_INGESTED_BYTES_AT_OPEN"] = header_size  # type: ignore

        if bands := asset_info.get("raster:bands"):
            stats = [
                (b["statistics"]["minimum"], b["statistics"]["maximum"])
                for b in bands
                if {"minimum", "maximum"}.issubset(b.get("statistics", {}))
            ]
            if len(stats) == len(bands):
                info["dataset_statistics"] = stats

        return info

    def tile(  # noqa: C901
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        assets: Union[Sequence[str], str] = (),
        expression: Optional[str] = None,
        asset_indexes: Optional[Dict[str, Indexes]] = None,  # Indexes for each asset
        asset_as_band: bool = False,
        **kwargs: Any,
    ) -> ImageData:
        """Read and merge Wep Map tiles from multiple assets.

        Args:
            tile_x (int): Tile's horizontal index.
            tile_y (int): Tile's vertical index.
            tile_z (int): Tile's zoom level index.
            assets (sequence of str or str, optional): assets to fetch info from.
            expression (str, optional): rio-tiler expression for the asset list (e.g. asset1/asset2+asset3).
            asset_indexes (dict, optional): Band indexes for each asset (e.g {"asset1": 1, "asset2": (1, 2,)}).
            kwargs (optional): Options to forward to the `self.reader.tile` method.

        Returns:
            rio_tiler.models.ImageData: ImageData instance with data, mask and tile spatial info.

        """
        if not self.tile_exists(tile_x, tile_y, tile_z):
            raise TileOutsideBounds(
                f"Tile {tile_z}/{tile_x}/{tile_y} is outside image bounds"
            )

        if isinstance(assets, str):
            assets = (assets,)

        if assets and expression:
            warnings.warn(
                "Both expression and assets passed; expression will overwrite assets parameter.",
                ExpressionMixingWarning,
                stacklevel=2,
            )

        if expression:
            assets = self.parse_expression(expression, asset_as_band=asset_as_band)

        if not assets:
            raise MissingAssets(
                "assets must be passed either via `expression` or `assets` options."
            )

        asset_indexes = asset_indexes or {}

        # We fall back to `indexes` if provided
        indexes = kwargs.pop("indexes", None)

        def _reader(asset: str, *args: Any, **kwargs: Any) -> ImageData:
            idx = asset_indexes.get(asset) or indexes  # type: ignore

            asset_info = self._get_asset_info(asset)
            reader = self._get_reader(asset_info)

            with self.ctx(**asset_info.get("env", {})):
                with reader(
                    asset_info["url"], tms=self.tms, **self.reader_options
                ) as src:
                    if type(src) == XarrayReader:
                        raise NotImplementedError("XarrayReader not yet implemented")
                    data = src.tile(*args, indexes=idx, **kwargs)

                    self._update_statistics(
                        data,
                        indexes=idx,
                        statistics=asset_info.get("dataset_statistics"),
                    )

                    metadata = data.metadata or {}
                    if m := asset_info.get("metadata"):
                        metadata.update(m)
                    data.metadata = {asset: metadata}

                    if asset_as_band:
                        if len(data.band_names) > 1:
                            raise AssetAsBandError(
                                "Can't use `asset_as_band` for multibands asset"
                            )
                        data.band_names = [asset]
                    else:
                        data.band_names = [f"{asset}_{n}" for n in data.band_names]

                    return data

        img = multi_arrays(assets, _reader, tile_x, tile_y, tile_z, **kwargs)
        if expression:
            return img.apply_expression(expression)

        return img
