"""Test titiler.stacapi STACReader functions."""

import json
import os
from unittest.mock import patch

import pystac

from titiler.stacapi.stac_reader import STACReader

noaa_emergency_item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
noaa_emergency_item_json = json.loads(open(noaa_emergency_item_file).read())

landcover_item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "esa-cci-lc-2020.json"
)
landcover_item_json = json.loads(open(landcover_item_file).read())


@patch("planetary_computer.sign")
def test_not_signed(pc_sign_mock):
    stac_reader = STACReader(pystac.Item.from_dict(noaa_emergency_item_json))
    asset_url = stac_reader.item.assets["cog"].href
    unsigned_url = stac_reader._signed_url(asset_url)
    assert asset_url == unsigned_url
    pc_sign_mock.assert_not_called()


@patch("planetary_computer.sign")
def test_signed(pc_sign_mock):
    stac_reader = STACReader(
        pystac.Item.from_dict(landcover_item_json),
        include_asset_types={"application/netcdf"},
    )
    asset_url = stac_reader.item.assets["netcdf"].href
    _ = stac_reader._signed_url(asset_url)
    pc_sign_mock.assert_called_once()
