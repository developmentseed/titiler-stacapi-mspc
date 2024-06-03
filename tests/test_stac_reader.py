"""test titiler-stacapi stac_reader."""

import json
import pytest
import os
from unittest.mock import patch
import pystac
from titiler.stacapi.stac_reader import STACReader, InvalidAssetType
from rio_tiler.io import Reader, XarrayReader
from rio_tiler.errors import MissingAssets

cog_item_json = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)

netcdf_item_json = os.path.join(
    os.path.dirname(__file__), "fixtures", "C3S-LC-L4-LCCS-Map-300m-P1Y-2020-v2.1.1.json"
)

def test_select_asset_reader():
    """Test select_asset_reader."""
    with open(cog_item_json) as f:
        item = json.load(f)
    reader = STACReader(item=pystac.Item.from_dict(item))
    assert reader._select_asset_reader('cog') == Reader

    with open(netcdf_item_json) as f:
        item = json.load(f)
    reader = STACReader(item=pystac.Item.from_dict(item))
    assert reader._select_asset_reader('netcdf') == XarrayReader

def gen_stac_item(media_types: list=[]):
    assets = {}
    for i, media_type in enumerate(media_types):
        assets[f"asset_{i}"] = pystac.Asset(href=f"asset_{i}", media_type=media_type)
    return pystac.Item(**{
        "geometry": None,
        "bbox": None,
        "properties": {},
        "datetime": "2020-02-02",
        "id": "test_stac_item",
        "assets": assets
    })

@pytest.mark.xfail(raises=MissingAssets)
def test_bad_asset_media_types():
    # test with an invalid type - filtered out by stac.STACReader.get_assets 
    stac_item = gen_stac_item(["application/geojson"])
    _ = STACReader(stac_item)

def test_good_asset_media_types():
    # test with 2 different types

    # test with multiple netcdfs

    # test with multiple COGs
    pass