"""Test titiler.stacapi STACReader functions."""

import json
import os
from unittest.mock import patch

import pystac
import pytest

from titiler.stacapi.stac_reader import STACReader

item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
item_json = json.loads(open(item_file).read())

@patch("planetary_computer.sign")
def test_signed_url(pc_sign_mock):
    stac_reader = STACReader(pystac.Item.from_dict(item_json))
    asset_url = stac_reader.item.assets["cog"].href
    unsigned_url = stac_reader._signed_url(asset_url)
    assert asset_url == unsigned_url
    pc_sign_mock.assert_not_called()

    pc_asset_url = "https://landcoverdata.blob.core.windows.net/esa-cci-lc/netcdf/C3S-LC-L4-LCCS-Map-300m-P1Y-2020-v2.1.1.nc"
    _ = stac_reader._signed_url(pc_asset_url)
    pc_sign_mock.assert_called_once()