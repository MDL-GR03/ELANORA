import json
from pathlib import Path
from typing import TypedDict, cast


class NamingStandardLocation(TypedDict):
    """Configured identifier and display label for a naming location."""

    id: int
    label: str


JSON_PATH = Path(__file__).parent / "effective_naming_standard_locations.json"

with open(JSON_PATH, encoding="utf-8") as f:
    EFFECTIVE_NAMING_STANDARD_LOCATIONS = cast(
        "list[NamingStandardLocation]", json.load(f)
    )


def get_location_id_by_name(name: str) -> int | None:
    for loc in EFFECTIVE_NAMING_STANDARD_LOCATIONS:
        if loc["label"] == name:
            return loc["id"]
    return None


def get_location_name_by_id(location_id: int) -> str | None:
    for loc in EFFECTIVE_NAMING_STANDARD_LOCATIONS:
        if loc["id"] == location_id:
            return loc["label"]
    return None
