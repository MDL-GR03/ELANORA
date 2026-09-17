"""Typed response models for upload naming compliance."""

from typing import TypedDict


class NamingStandardComponent(TypedDict, total=False):
    """A component from a naming standard used for filename validation."""

    id: int
    file_type_id: int
    name: str
    regex: str
    description: str | None


class UploadNamingStandardResponse(TypedDict):
    """The naming standard configuration for upload filename validation."""

    pattern: str
    components: list[NamingStandardComponent]
