"""Test titiler.stacapi.stac_reader functions."""

import json
import os
from unittest.mock import patch

import pytest
from rio_tiler.io import Reader
from rio_tiler.models import ImageData

from titiler.stacapi.asset_reader import AssetReader
from titiler.stacapi.models import AssetInfo

from .conftest import mock_rasterio_open

item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
item_json = json.loads(open(item_file).read())


def test_get_asset_info():
    """Test get_asset_info function"""
    asset_reader = AssetReader(item_json)
    expected_asset_info = AssetInfo(
        url=item_json["assets"]["cog"]["href"],
        type=item_json["assets"]["cog"]["type"],
        env={},
    )
    assert asset_reader._get_asset_info("cog") == expected_asset_info


def test_get_reader_any():
    """Test reader is rio_tiler.io.Reader"""
    asset_info = AssetInfo(url="https://file.tif")
    empty_stac_reader = AssetReader({"bbox": [], "assets": []})
    assert empty_stac_reader._get_reader(asset_info) == Reader


@pytest.mark.xfail(reason="To be implemented.")
def test_get_reader_netcdf():
    """Test reader attribute is titiler.stacapi.XarrayReader"""
    asset_info = AssetInfo(url="https://file.nc", type="application/netcdf")
    empty_stac_reader = AssetReader({"bbox": [], "assets": []})
    empty_stac_reader._get_reader(asset_info)


@pytest.mark.skip(reason="Too slow.")
@patch("rio_tiler.io.rasterio.rasterio")
def test_tile_cog(rio):
    """Test tile function with COG asset."""
    rio.open = mock_rasterio_open

    with AssetReader(item_json) as reader:
        img = reader.tile(0, 0, 0, assets=["cog"])
        assert isinstance(img, ImageData)


@pytest.mark.skip(reason="To be implemented.")
def test_tile_netcdf():
    """Test tile function with netcdf asset."""
    pass
