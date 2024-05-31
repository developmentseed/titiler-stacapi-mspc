"""Test titiler.stacapi Item endpoints."""

import json
import os

import pystac
from rio_tiler.io import Reader

from titiler.stacapi.stac_reader import STACReader

item_file = os.path.join(
    os.path.dirname(__file__), "fixtures", "20200307aC0853900w361030.json"
)
item_json = json.loads(open(item_file).read())


def test_stac_items():
    """ Test reader attribute is rio_tiler.io.Reader """
    stac_reader = STACReader(pystac.Item.from_dict(item_json))
    _ = stac_reader._get_asset_info("cog")
    assert stac_reader.reader == Reader
