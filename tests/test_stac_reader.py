"""Test titiler.stacapi.stac_reader functions."""

import json
import os
from unittest.mock import patch

import pytest
from rio_tiler.io import Reader
from rio_tiler.models import ImageData

from titiler.stacapi.models import AssetInfo
from titiler.stacapi.stac_reader import CustomSTACReader
from titiler.stacapi.xarray import XarrayReader

from .conftest import mock_rasterio_open

item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
item_json = json.loads(open(item_file).read())


@pytest.mark.skip(reason="To be implemented.")
def test_asset_info():
    """Test get_asset_info function"""
    pass


empty_stac_reader = CustomSTACReader({"assets": [], "bbox": []})


def test_get_reader_cog():
    """Test reader is rio_tiler.io.Reader"""
    asset_info = AssetInfo(url="https://file.tif")
    assert empty_stac_reader._get_reader(asset_info) == Reader


def test_get_reader_netcdf():
    """Test reader attribute is titiler.stacapi.XarrayReader"""
    asset_info = AssetInfo(url="https://file.nc", type="application/netcdf")
    assert empty_stac_reader._get_reader(asset_info) == XarrayReader


@patch("rio_tiler.io.rasterio.rasterio")
def test_tile_cog(rio):
    """Test tile function with COG asset."""
    rio.open = mock_rasterio_open
    with CustomSTACReader(item_json) as reader:
        img = reader.tile(0, 0, 0, assets=["cog"])
        assert type(img) == ImageData


@pytest.mark.skip(reason="To be implemented.")
def test_tile_netcdf():
    """Test tile function with netcdf asset."""
    pass
