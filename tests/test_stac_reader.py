"""Test titiler.stacapi.stac_reader functions."""

import json
import os

import pystac
import pytest
from rio_tiler.io import Reader

from titiler.stacapi.stac_reader import CustomSTACReader
from titiler.stacapi.xarray import XarrayReader
from titiler.stacapi.models import AssetInfo

@pytest.mark.skip(reason="To be implemented.")
def test_asset_info():
    """Test get_asset_info function"""
    pass

empty_stac_reader = CustomSTACReader({'assets': [], 'bbox': []})
def test_stac_reader_cog():
    """Test reader is rio_tiler.io.Reader"""
    asset_info = AssetInfo(
        url="https://file.tif",
        type="image/tiff"
    )
    assert empty_stac_reader._get_reader(asset_info) == Reader


def test_stac_reader_netcdf():
    """Test reader attribute is titiler.stacapi.XarrayReader"""
    asset_info = AssetInfo(
        url="https://file.nc",
        type="application/netcdf"
    )
    assert empty_stac_reader._get_reader(asset_info) == XarrayReader

def test_tile_cog():
    pass

def test_tile_netcdf():
    pass
