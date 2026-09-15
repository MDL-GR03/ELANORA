"""Readers for XML Schema datatypes used by EAF attributes.

These decide validation outcomes, so this module is part of the validator
release checksum. Keep it limited to datatype interpretation.
"""


def parse_xsd_boolean(value: str | None) -> bool | None:
    """Read an xsd:boolean, which admits "1" and "0" as well as "true"/"false"."""
    if value is None:
        return None
    return value.strip() in {"true", "1"}


def split_references(value: str | None) -> tuple[str, ...]:
    """Split an xsd:IDREFS attribute into its individual references."""
    return tuple((value or "").split())
