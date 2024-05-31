"""Custom STAC reader."""

from typing import Any, Dict, Optional, Set, Type

import attr
import pystac
import rasterio
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import InvalidAssetName
from rio_tiler.io import BaseReader, Reader, XarrayReader, stac

# Also replace with rio_tiler import when https://github.com/cogeotiff/rio-tiler/pull/711 is merged and released.
from titiler.stacapi.models import AssetInfo
from titiler.stacapi.settings import STACSettings

stac_config = STACSettings()


valid_types = {
    "image/tiff; application=geotiff",
    "image/tiff; application=geotiff; profile=cloud-optimized",
    "image/tiff; profile=cloud-optimized; application=geotiff",
    "image/tiff; application=geotiff; profile=cloud-optimized",
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
class STACReader(stac.STACReader):
    """Custom STAC Reader.

    Only accept `pystac.Item` as input (while rio_tiler.io.STACReader accepts url or pystac.Item)

    """

    input: pystac.Item = attr.ib()

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib()
    maxzoom: int = attr.ib()

    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    include_assets: Optional[Set[str]] = attr.ib(default=None)
    exclude_assets: Optional[Set[str]] = attr.ib(default=None)

    include_asset_types: Set[str] = attr.ib(default=stac.DEFAULT_VALID_TYPE)
    exclude_asset_types: Optional[Set[str]] = attr.ib(default=None)

    reader: Type[BaseReader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    fetch_options: Dict = attr.ib(factory=dict)

    ctx: Any = attr.ib(default=rasterio.Env)

    item: pystac.Item = attr.ib(init=False)

    include_asset_types: Set[str] = attr.ib(default=valid_types)

    def _get_reader(self, asset_info: AssetInfo) -> Type[BaseReader]:
        """Get Asset Reader."""
        asset_type = asset_info.get("type", None)

        if asset_type and asset_type in [
            "application/x-hdf5",
            "application/x-hdf",
            "application/vnd.zarr",
            "application/x-netcdf",

        ]:
            return XarrayReader

        return Reader

    def __attrs_post_init__(self):
        """Fetch STAC Item and get list of valid assets."""
        self.item = self.input
        super().__attrs_post_init__()

    @minzoom.default
    def _minzoom(self):
        return self.tms.minzoom

    @maxzoom.default
    def _maxzoom(self):
        return self.tms.maxzoom

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
        )
        
        # Replace this and the _get_reader method once https://github.com/cogeotiff/rio-tiler/pull/711 is merged and released.
        self.reader = self._get_reader(info)        

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
