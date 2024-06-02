"""Custom XarrayReader for opening data arrays and transforming coordinates."""

import attr
import fsspec
import rio_tiler.io.xarray as rio_tiler_xarray
import xarray as xr


# Probably want to reimplement https://github.com/developmentseed/titiler-cmr/blob/develop/titiler/cmr/reader.py
@attr.s
class XarrayReader(rio_tiler_xarray.XarrayReader):
    """Custom XarrayReader for opening data arrays and transforming coordinates."""

    input: xr.Dataset = attr.ib(init=False, default=None)
    src_path: str = attr.ib(default=None)
    variable: str = attr.ib(default=None)

    def __attrs_post_init__(self):
        """Post Init."""
        httpfs = fsspec.filesystem("http")
        self.input = xr.open_dataset(httpfs.open(self.src_path))[self.variable]
        return super().__attrs_post_init__()
