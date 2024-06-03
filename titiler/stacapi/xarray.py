
import attr
# from typing import Dict
import rio_tiler.io as riotio
# import xarray as xr
# import fsspec

@attr.s
class XarrayReader(riotio.XarrayReader):
    """Custom Xarray Reader."""

    # def __attrs_post_init__(self) -> None:
    #     httpfs = fsspec.filesystem("https")
    #     da = xr.open_dataset(httpfs.open(self.input), engine="h5netcdf")[variable]
    #     self.input = da
