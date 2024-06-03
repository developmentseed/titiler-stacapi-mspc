"""Custom STAC reader."""

from typing import Any, Dict, Optional, Set, Type

import attr
import pystac
import rasterio
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import InvalidAssetName, RioTilerError
from rio_tiler.io import BaseReader, Reader, stac, XarrayReader
from rio_tiler.types import AssetInfo

from titiler.stacapi.settings import STACSettings

stac_config = STACSettings()

class InvalidAssetType(RioTilerError):
    """Invalid Asset name."""

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
    "application/netcdf",
}

@attr.s
class STACReader(stac.STACReader):
    """Custom STAC Reader.

    Only accept `pystac.Item` as input (while rio_tiler.io.STACReader accepts url or pystac.Item)

    """

    item: pystac.Item = attr.ib()
    input: str = attr.ib(default=None) # we don't need an input requirement here, as it is required by the default rio_tiler.io.STACReader

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib()
    maxzoom: int = attr.ib()

    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    include_assets: Optional[Set[str]] = attr.ib(default=None)
    exclude_assets: Optional[Set[str]] = attr.ib(default=None)

    include_asset_types: Set[str] = attr.ib(default=valid_types)
    exclude_asset_types: Optional[Set[str]] = attr.ib(default=None)

    reader: Type[BaseReader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    fetch_options: Dict = attr.ib(factory=dict)

    ctx: Any = attr.ib(default=rasterio.Env)

    @minzoom.default
    def _minzoom(self):
        return self.tms.minzoom

    @maxzoom.default
    def _maxzoom(self):
        return self.tms.maxzoom
    
    def asset_media_types_set(self, *asset_names):
        """
        Given a STAC item and multiple asset names, returns the set of asset media types for those assets.

        Parameters:
        asset_names (str): Asset names to retrieve media types for.

        Returns:
        set: A set of media types for the specified assets.
        """
        media_types = set()
        assets = self.item.assets

        for asset_name in asset_names: 
            # TODO: Should we catch and raise if asset name or type are missing?          
            asset = assets.get(asset_name)
            media_type = asset.get('type')
            if media_type:
                # stac.STACReader all ready filters to valid types, so we don't need to do that here            
                media_types.add(media_type)
        return media_types

    def _select_asset_reader(self, asset: str) -> Type[BaseReader]:
        """Select the correct reader based on the asset type."""
        asset_info = self._get_asset_info(asset)
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
        """Validate asset names and return asset's url.

        Args:
            asset (str): STAC asset name.

        Returns:
            str: STAC asset href.

        """
        if asset not in self.assets:
            raise InvalidAssetName(
                f"'{asset}' is not valid, should be one of {self.assets}"
            )

        asset_info = self.item.assets[asset]
        extras = asset_info.extra_fields

        url = asset_info.get_absolute_href() or asset_info.href
        if alternate := stac_config.alternate_url:
            url = asset_info.to_dict()["alternate"][alternate]["href"]

        info = AssetInfo(
            url=url,
            metadata=extras,
            type=asset_info.to_dict()["type"]
        )

        if head := extras.get("file:header_size"):
            info["env"] = {"GDAL_INGESTED_BYTES_AT_OPEN": head}

        if bands := extras.get("raster:bands"):
            stats = [
                (b["statistics"]["minimum"], b["statistics"]["maximum"])
                for b in bands
                if {"minimum", "maximum"}.issubset(b.get("statistics", {}))
            ]
            if len(stats) == len(bands):
                info["dataset_statistics"] = stats

        return info
