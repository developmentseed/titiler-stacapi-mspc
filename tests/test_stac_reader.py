"""Test titiler.stacapi.stac_reader functions."""

import json
import os

import pytest
import pystac
from rio_tiler.io import Reader

from titiler.stacapi.stac_reader import STACReader

item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
item_json = json.loads(open(item_file).read())

@pytest.mark.skip(reason="To be implemented.")
def test_asset_info():
    """Test get_asset_info function"""
    pass

def test_stac_reader_cog():
    """Test reader is rio_tiler.io.Reader"""
    stac_reader = STACReader(pystac.Item.from_dict(item_json))
    asset_info = stac_reader._get_asset_info("cog")
    assert stac_reader._get_asset_reader(asset_info) == Reader

@pytest.mark.skip(reason="To be implemented.")
def test_stac_reader_netcdf():
    """Test reader attribute is titiler.stacapi.XarrayReader"""
    pass


