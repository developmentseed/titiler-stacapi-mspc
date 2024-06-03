"""STAC Item Tiler."""
from dataclasses import dataclass, field
from typing import Any, Callable, List, Literal, Optional, Type, Union

import numpy
from fastapi import APIRouter, Depends, Path, Query
from morecantile import tms as default_tms
from morecantile.defaults import TileMatrixSets
from pydantic import conint
from rio_tiler.io import BaseReader
from rio_tiler.types import RIOResampling, WarpResampling
from starlette.requests import Request
from starlette.responses import Response
from typing_extensions import Annotated

from titiler.core import BaseTilerFactory, dependencies
from titiler.core.algorithm import algorithms as available_algorithms
from titiler.core.dependencies import DatasetPathParams
from titiler.core.factory import img_endpoint_params
from titiler.core.resources.enums import ImageType
from titiler.core.utils import render_image
from titiler.stacapi.stac_reader import STACReader


@dataclass
class StacItemTiler(BaseTilerFactory):
    """STAC Item Tiler."""

    # Path Dependency
    path_dependency: Callable[..., Any] = DatasetPathParams

    # FastAPI router
    router: APIRouter = field(default_factory=APIRouter)

    supported_tms: TileMatrixSets = default_tms

    # Router Prefix is needed to find the path for routes when prefixed
    # e.g if you mount the route with `/foo` prefix, set router_prefix to foo
    router_prefix: str = ""

    title: str = "TiTiler-STACAPI-MSPC"
    reader: Type[BaseReader] = STACReader

    def register_routes(self):
        """Post Init: register routes."""
        self.register_tiles()

    def register_tiles(self):  # noqa: C901
        """Register tileset endpoints."""

        @self.router.get(
            "/tiles/{tileMatrixSetId}/{z}/{x}/{y}",
            **img_endpoint_params,
            tags=["Raster Tiles"],
        )
        @self.router.get(
            "/tiles/{tileMatrixSetId}/{z}/{x}/{y}.{format}",
            **img_endpoint_params,
            tags=["Raster Tiles"],
        )
        @self.router.get(
            "/tiles/{tileMatrixSetId}/{z}/{x}/{y}@{scale}x",
            **img_endpoint_params,
            tags=["Raster Tiles"],
        )
        @self.router.get(
            "/tiles/{tileMatrixSetId}/{z}/{x}/{y}@{scale}x.{format}",
            **img_endpoint_params,
            tags=["Raster Tiles"],
        )
        def tiles_endpoint(
            request: Request,
            tileMatrixSetId: Annotated[
                Literal[tuple(self.supported_tms.list())],
                Path(description="Identifier for a supported TileMatrixSet"),
            ],
            z: Annotated[
                int,
                Path(
                    description="Identifier (Z) selecting one of the scales defined in the TileMatrixSet and representing the scaleDenominator the tile.",
                ),
            ],
            x: Annotated[
                int,
                Path(
                    description="Column (X) index of the tile on the selected TileMatrix. It cannot exceed the MatrixHeight-1 for the selected TileMatrix.",
                ),
            ],
            y: Annotated[
                int,
                Path(
                    description="Row (Y) index of the tile on the selected TileMatrix. It cannot exceed the MatrixWidth-1 for the selected TileMatrix.",
                ),
            ],
            scale: Annotated[  # type: ignore
                conint(gt=0, le=4), "Tile size scale. 1=256x256, 2=512x512..."
            ] = 1,
            format: Annotated[
                ImageType,
                "Default will be automatically defined if the output image needs a mask (png) or not (jpeg).",
            ] = None,
            asset: Annotated[
                str,
                "Asset name to read from (STAC Item asset name)",
            ] = "",
            ###################################################################
            # XarrayReader Options
            ###################################################################
            variable: Annotated[
                Optional[str],
                Query(description="Xarray Variable"),
            ] = None,
            drop_dim: Annotated[
                Optional[str],
                Query(description="Dimension to drop"),
            ] = None,
            time_slice: Annotated[
                Optional[str], Query(description="Slice of time to read (if available)")
            ] = None,
            decode_times: Annotated[
                Optional[bool],
                Query(
                    title="decode_times",
                    description="Whether to decode times",
                ),
            ] = None,
            ###################################################################
            # Rasterio Reader Options
            ###################################################################
            indexes: Annotated[
                Optional[List[int]],
                Query(
                    title="Band indexes",
                    alias="bidx",
                    description="Dataset band indexes",
                ),
            ] = None,
            expression: Annotated[
                Optional[str],
                Query(
                    title="Band Math expression",
                    description="rio-tiler's band math expression",
                ),
            ] = None,
            bands: Annotated[
                Optional[List[str]],
                Query(
                    title="Band names",
                    description="Band names.",
                ),
            ] = None,
            bands_regex: Annotated[
                Optional[str],
                Query(
                    title="Regex expression to parse dataset links",
                    description="Regex expression to parse dataset links.",
                ),
            ] = None,
            unscale: Annotated[
                Optional[bool],
                Query(
                    title="Apply internal Scale/Offset",
                    description="Apply internal Scale/Offset. Defaults to `False`.",
                ),
            ] = None,
            resampling_method: Annotated[
                Optional[RIOResampling],
                Query(
                    alias="resampling",
                    description="RasterIO resampling algorithm. Defaults to `nearest`.",
                ),
            ] = None,
            ###################################################################
            # Reader options
            ###################################################################
            nodata: Annotated[
                Optional[Union[str, int, float]],
                Query(
                    title="Nodata value",
                    description="Overwrite internal Nodata value",
                ),
            ] = None,
            reproject_method: Annotated[
                Optional[WarpResampling],
                Query(
                    alias="reproject",
                    description="WarpKernel resampling algorithm (only used when doing re-projection). Defaults to `nearest`.",
                ),
            ] = None,
            ###################################################################
            # Rendering Options
            ###################################################################
            post_process=Depends(available_algorithms.dependency),
            rescale=Depends(dependencies.RescalingParams),
            color_formula=Depends(dependencies.ColorFormulaParams),
            colormap=Depends(dependencies.ColorMapParams),
            render_params=Depends(dependencies.ImageRenderingParams),
            item=Depends(self.path_dependency),
        ) -> Response:
            """Create map tile from a dataset."""
            resampling_method = resampling_method or "nearest"
            reproject_method = reproject_method or "nearest"
            if nodata is not None:
                nodata = numpy.nan if nodata == "nan" else float(nodata)

            asset_url = item.assets[asset].href
            stac_item_reader = self.reader(input=asset_url, item=item)
            asset_info = stac_item_reader._get_asset_info(asset)

            # Add me - function for parsing reader options specific to the asset type
            reader_options = {
                "src_path": asset_url,
                "variable": variable,
            }

            with stac_item_reader._get_asset_reader(asset_info)(
                **reader_options
            ) as src_dst:
                image, _ = src_dst.tile(
                    x,
                    y,
                    z,
                    tilesize=scale * 256,
                    nodata=nodata,
                    reproject_method=reproject_method,
                    assets=[asset]
                    # **read_options,
                )

            if post_process:
                image = post_process(image)

            if rescale:
                image.rescale(rescale)

            if color_formula:
                image.apply_color_formula(color_formula)

            content, media_type = render_image(
                image,
                output_format=format,
                colormap=colormap,
                **render_params,
            )

            return Response(content, media_type=media_type)
