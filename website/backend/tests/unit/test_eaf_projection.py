"""Coverage for the complete versioned EAF JSON projection."""

import json
from pathlib import Path

from app.elan.parser import parse_eaf
from app.elan.projection import EAF_PROJECTION_VERSION, document_projection

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


def test_projection_preserves_queryable_eaf_structure() -> None:
    projection = document_projection(parse_eaf(FIXTURE.read_bytes()))

    assert projection["projection_version"] == EAF_PROJECTION_VERSION
    assert len(projection["tiers"]) == 2
    assert len(projection["linguistic_types"]) == 2
    assert len(projection["controlled_vocabularies"]) == 1
    assert len(projection["languages"]) == 2
    assert len(projection["locales"]) == 2
    assert len(projection["header"]["media_descriptors"]) == 1
    assert len(projection["header"]["properties"]) == 2
    assert projection["tiers"][0]["annotations"][0]["kind"] == "alignable"
    assert projection["tiers"][1]["annotations"][0]["kind"] == "reference"
    json.dumps(projection)
