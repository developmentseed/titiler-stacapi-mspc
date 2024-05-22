"""Test titiler.stacapi Item endpoints."""

import json
import os
from unittest.mock import patch

import pystac
import pytest

from rio_tiler.io import Reader
from titiler.stacapi.stac_reader import STACReader

item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
item_json = json.loads(open(item_file).read())

def test_stac_items():
    stac_reader = STACReader(pystac.Item.from_dict(item_json))
    _ = stac_reader._get_asset_info("cog")
    assert stac_reader.reader == Reader
