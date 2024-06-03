"""titiler-stacapi custom Mosaic Backend and Custom STACReader."""

import json
from typing import Any, Dict, List, Optional, Tuple, Type

import attr
import planetary_computer as pc
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from cogeo_mosaic.backends import BaseBackend
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.mosaic import MosaicJSON
from geojson_pydantic import Point, Polygon
from geojson_pydantic.geometries import Geometry
from morecantile import Tile, TileMatrixSet
from pystac_client import ItemSearch
from pystac_client.stac_api_io import StacApiIO
from rasterio.crs import CRS
from rasterio.warp import transform, transform_bounds
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.models import ImageData
from rio_tiler.mosaic import mosaic_reader
from rio_tiler.types import BBox
from urllib3 import Retry

from titiler.stacapi.settings import CacheSettings, RetrySettings, STACSettings
from titiler.stacapi.asset_reader import AssetReader
from titiler.stacapi.utils import Timer

cache_config = CacheSettings()
retry_config = RetrySettings()
stac_config = STACSettings()


@attr.s
class STACAPIBackend(BaseBackend):
    """STACAPI Mosaic Backend."""

    # STAC API URL
    url: str = attr.ib()
    headers: Dict = attr.ib(factory=dict)

    # Because we are not using mosaicjson we are not limited to the WebMercator TMS
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib()
    maxzoom: int = attr.ib()

    # Use custom asset reader (outside init)
    reader: Type[AssetReader] = attr.ib(init=False, default=AssetReader)
    reader_options: Dict = attr.ib(factory=dict)

    # default values for bounds
    bounds: BBox = attr.ib(default=(-180, -90, 180, 90))

    crs: CRS = attr.ib(default=WGS84_CRS)
    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    input: str = attr.ib(init=False)
    mosaic_def: MosaicJSON = attr.ib(init=False)

    _backend_name = "STACAPI"

    def __attrs_post_init__(self) -> None:
        """Post Init."""
        self.input = self.url

        # Construct a FAKE mosaicJSON
        # mosaic_def has to be defined.
        # we set `tiles` to an empty list.
        self.mosaic_def = MosaicJSON(
            mosaicjson="0.0.3",
            name=self.input,
            bounds=self.bounds,
            minzoom=self.minzoom,
            maxzoom=self.maxzoom,
            tiles={},
        )

    @minzoom.default
    def _minzoom(self):
        return self.tms.minzoom

    @maxzoom.default
    def _maxzoom(self):
        return self.tms.maxzoom

    def write(self, overwrite: bool = True) -> None:
        """This method is not used but is required by the abstract class."""
        pass

    def update(self) -> None:
        """We overwrite the default method."""
        pass

    def _read(self) -> MosaicJSON:
        """This method is not used but is required by the abstract class."""
        pass

    def assets_for_tile(self, x: int, y: int, z: int, **kwargs: Any) -> List[Dict]:
        """Retrieve assets for tile."""
        bbox = self.tms.bounds(Tile(x, y, z))
        return self.get_assets(Polygon.from_bounds(*bbox), **kwargs)

    def assets_for_point(
        self,
        lng: float,
        lat: float,
        coord_crs: CRS = WGS84_CRS,
        **kwargs: Any,
    ) -> List[Dict]:
        """Retrieve assets for point."""
        if coord_crs != WGS84_CRS:
            xs, ys = transform(coord_crs, WGS84_CRS, [lng], [lat])
            lng, lat = xs[0], ys[0]

        return self.get_assets(Point(type="Point", coordinates=(lng, lat)), **kwargs)

    def assets_for_bbox(
        self,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        coord_crs: CRS = WGS84_CRS,
        **kwargs: Any,
    ) -> List[Dict]:
        """Retrieve assets for bbox."""
        if coord_crs != WGS84_CRS:
            xmin, ymin, xmax, ymax = transform_bounds(
                coord_crs,
                WGS84_CRS,
                xmin,
                ymin,
                xmax,
                ymax,
            )

        return self.get_assets(Polygon.from_bounds(xmin, ymin, xmax, ymax), **kwargs)

    @cached(  # type: ignore
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, geom, search_query, **kwargs: hashkey(
            self.url,
            str(geom),
            json.dumps(search_query),
            json.dumps(self.headers),
            **kwargs,
        ),
    )
    def get_assets(
        self,
        geom: Geometry,
        search_query: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Find assets."""
        search_query = search_query or {}
        fields = fields or ["assets", "id", "bbox", "collection"]

        stac_api_io = StacApiIO(
            max_retries=Retry(
                total=retry_config.retry,
                backoff_factor=retry_config.retry_factor,
            ),
            headers=self.headers,
        )

        params = {
            **search_query,
            "intersects": geom.model_dump_json(exclude_none=True),
            "fields": fields,
        }
        params.pop("bbox", None)

        results = ItemSearch(
            f"{self.url}/search",
            stac_io=stac_api_io,
            **params,
            modifier=pc.sign_inplace,
        )
        return list(results.items_as_dicts())

    @property
    def _quadkeys(self) -> List[str]:
        return []

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        search_query: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Tuple[ImageData, List[str]]:
        """Get Tile from multiple observation."""
        timings = []

        with Timer() as t:
            mosaic_assets = self.assets_for_tile(
                tile_x,
                tile_y,
                tile_z,
                search_query=search_query,
            )

        timings.append(("search", round(t.elapsed * 1000, 2)))

        if not mosaic_assets:
            raise NoAssetFoundError(
                f"No assets found for tile {tile_z}-{tile_x}-{tile_y}"
            )

        def _reader(
            item: Dict[str, Any], x: int, y: int, z: int, **kwargs: Any
        ) -> ImageData:
            with self.reader(item, tms=self.tms, **self.reader_options) as src_dst:
                return src_dst.tile(x, y, z, **kwargs)

        with Timer() as t:
            img, used_assets = mosaic_reader(
                mosaic_assets, _reader, tile_x, tile_y, tile_z, **kwargs
            )

        timings.append(("mosaicking", round(t.elapsed * 1000, 2)))
        img.metadata = {**img.metadata, "timings": timings}
        return img, used_assets

    def point(
        self,
        lon: float,
        lat: float,
        coord_crs: CRS = WGS84_CRS,
        search_query: Optional[Dict] = None,
        **kwargs: Any,
    ) -> List:
        """Get Point value from multiple observation."""
        raise NotImplementedError

    def part(
        self,
        bbox: BBox,
        dst_crs: Optional[CRS] = None,
        bounds_crs: CRS = WGS84_CRS,
        search_query: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Tuple[ImageData, List[str]]:
        """Create an Image from multiple items for a bbox."""
        raise NotImplementedError

    def feature(
        self,
        shape: Dict,
        shape_crs: CRS = WGS84_CRS,
        max_size: int = 1024,
        search_query: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Tuple[ImageData, List[str]]:
        """Create an Image from multiple items for a GeoJSON feature."""
        raise NotImplementedError
