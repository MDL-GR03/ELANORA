"""Create safe, smaller EAF research copies without mutating project data."""

import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256

from lxml import etree

from app.elan.validation import secure_xml_parser, validate_eaf

PROVENANCE_PROPERTY = "ELANORA_RESEARCH_EXTRACT"


class TierReintegrationConflictError(ValueError):
    """The accepted copy changed in the same tier since it was exported."""

    def __init__(self, filename: str, tiers: list[str]) -> None:
        self.filename = filename
        self.tiers = tiers
        super().__init__(
            f"{filename} has newer accepted changes in: {', '.join(tiers)}. "
            "Download a fresh research copy or ask a reviewer to reconcile these tiers."
        )


class ProtectedContextModifiedError(ValueError):
    """A research copy changed baseline context without declaring a correction."""

    def __init__(self, filename: str, tiers: list[str]) -> None:
        self.filename = filename
        self.tiers = tiers
        super().__init__(
            f"{filename} changes protected baseline context: {', '.join(tiers)}. "
            "Prepare a new research copy and mark these tiers as baseline corrections."
        )


@dataclass(frozen=True, slots=True)
class TierExportResult:
    content: bytes
    included_tiers: tuple[str, ...]
    automatically_included_tiers: tuple[str, ...]


def _tier_fingerprint(tier: etree._Element) -> str:
    canonical = etree.tostring(tier, method="c14n", with_comments=False)
    return sha256(canonical).hexdigest()


def research_extract_metadata(content: bytes) -> dict[str, object] | None:
    """Read provenance from an ELANORA extract, or None for an ordinary EAF."""
    root = etree.fromstring(content, parser=secure_xml_parser())
    marker = root.find(f"HEADER/PROPERTY[@NAME='{PROVENANCE_PROPERTY}']")
    if marker is None or not marker.text:
        return None
    try:
        metadata = json.loads(marker.text)
    except json.JSONDecodeError as exc:
        raise ValueError("Research-copy provenance is invalid") from exc
    if not isinstance(metadata, dict) or metadata.get("purpose") != "tier_scoped_edit":
        raise ValueError("Research-copy provenance is invalid")
    return metadata


def build_tier_subset(
    content: bytes,
    selected_tier_names: list[str],
    source_filename: str,
    *,
    topic_id: int | None = None,
    topic_name: str | None = None,
    allowed_new_tier_names: list[str] | None = None,
    context_tier_names: list[str] | None = None,
    editable_baseline_tier_names: list[str] | None = None,
) -> TierExportResult:
    """Return a valid EAF containing selected tiers and their required parents."""
    root = etree.fromstring(content, parser=secure_xml_parser())
    tiers = {
        tier_id: tier
        for tier in root.findall("TIER")
        if (tier_id := tier.get("TIER_ID"))
    }
    editable_baseline = set(editable_baseline_tier_names or [])
    requested_input = set(selected_tier_names) | editable_baseline
    context = (set(context_tier_names or []) - editable_baseline) & tiers.keys()
    unknown = sorted(requested_input - tiers.keys())
    if unknown:
        raise ValueError(f"Unknown tier(s): {', '.join(unknown)}")
    requested = requested_input - context
    if not requested:
        raise ValueError("Select at least one editable research tier")

    included = requested | context
    for tier_id in tuple(included):
        parent_id = tiers[tier_id].get("PARENT_REF")
        visited: set[str] = set()
        while parent_id:
            if parent_id in visited or parent_id not in tiers:
                raise ValueError(f"Tier {tier_id!r} has an invalid parent hierarchy")
            visited.add(parent_id)
            included.add(parent_id)
            parent_id = tiers[parent_id].get("PARENT_REF")

    for tier_id, tier in tiers.items():
        if tier_id not in included:
            root.remove(tier)

    used_time_slots = {
        time_ref
        for tier_id in included
        for annotation in tiers[tier_id].iter()
        for attribute in ("TIME_SLOT_REF1", "TIME_SLOT_REF2")
        if (time_ref := annotation.get(attribute))
    }
    time_order = root.find("TIME_ORDER")
    if time_order is not None:
        for slot in tuple(time_order.findall("TIME_SLOT")):
            if slot.get("TIME_SLOT_ID") not in used_time_slots:
                time_order.remove(slot)

    metadata = {
        "source_filename": source_filename,
        "selected_tiers": sorted(requested),
        "context_tiers": sorted(context - requested),
        "editable_baseline_tiers": sorted(editable_baseline & requested),
        "context_tier_sha256": {
            tier_id: _tier_fingerprint(tiers[tier_id]) for tier_id in sorted(context)
        },
        "included_parent_tiers": sorted(included - requested),
        "purpose": "tier_scoped_edit",
        "research_topic_id": topic_id,
        "research_topic": topic_name,
        "allowed_new_tiers": sorted(set(allowed_new_tier_names or []) - requested),
        "source_sha256": sha256(content).hexdigest(),
        "base_tier_sha256": {
            tier_id: _tier_fingerprint(tiers[tier_id]) for tier_id in sorted(requested)
        },
        "base_time_slots": {
            slot.get("TIME_SLOT_ID"): slot.get("TIME_VALUE")
            for slot in root.findall("TIME_ORDER/TIME_SLOT")
            if slot.get("TIME_SLOT_ID")
            in {
                time_ref
                for tier_id in requested
                for annotation in tiers[tier_id].iter()
                for attribute in ("TIME_SLOT_REF1", "TIME_SLOT_REF2")
                if (time_ref := annotation.get(attribute))
            }
        },
    }
    property_element = etree.Element("PROPERTY", NAME=PROVENANCE_PROPERTY)
    property_element.text = json.dumps(
        metadata, ensure_ascii=False, separators=(",", ":")
    )
    header = root.find("HEADER")
    if header is None:
        raise ValueError("EAF header is missing")
    header.append(property_element)

    result = etree.tostring(
        root.getroottree(), encoding="UTF-8", xml_declaration=True, pretty_print=True
    )
    validate_eaf(result)
    return TierExportResult(
        content=result,
        included_tiers=tuple(sorted(included)),
        automatically_included_tiers=tuple(sorted(included - requested)),
    )


def reintegrate_tier_subset(  # noqa: PLR0912, PLR0915
    current_content: bytes, extract_content: bytes
) -> bytes:
    """Apply only an extract's declared editable tiers to the current full EAF."""
    metadata = research_extract_metadata(extract_content)
    if metadata is None:
        raise ValueError("This is not an ELANORA research copy")
    filename = str(metadata.get("source_filename") or "source EAF")
    selected_value = metadata.get("selected_tiers")
    fingerprints_value = metadata.get("base_tier_sha256")
    base_time_slots = metadata.get("base_time_slots")
    allowed_new_value = metadata.get("allowed_new_tiers", [])
    context_value = metadata.get("context_tiers", [])
    context_fingerprints = metadata.get("context_tier_sha256", {})
    if not isinstance(selected_value, list) or not all(
        isinstance(item, str) for item in selected_value
    ):
        raise ValueError("Research-copy tier scope is invalid")
    if not isinstance(fingerprints_value, dict):
        raise ValueError("This research copy is outdated; download it again")
    if not isinstance(base_time_slots, dict):
        raise ValueError("This research copy is outdated; download it again")
    if not isinstance(allowed_new_value, list) or not all(
        isinstance(item, str) for item in allowed_new_value
    ):
        raise ValueError("Research-copy new-tier scope is invalid")
    if not isinstance(context_value, list) or not all(
        isinstance(item, str) for item in context_value
    ):
        raise ValueError("Research-copy baseline context is invalid")
    if not isinstance(context_fingerprints, dict):
        raise ValueError("This research copy is outdated; download it again")
    selected = set(selected_value)
    allowed_new = set(allowed_new_value)
    context = set(context_value)

    current_root = etree.fromstring(current_content, parser=secure_xml_parser())
    extract_root = etree.fromstring(extract_content, parser=secure_xml_parser())
    current_tiers = {
        tier_id: tier
        for tier in current_root.findall("TIER")
        if (tier_id := tier.get("TIER_ID"))
    }
    extract_tiers = {
        tier_id: tier
        for tier in extract_root.findall("TIER")
        if (tier_id := tier.get("TIER_ID"))
    }
    changed_context = sorted(
        tier_id
        for tier_id in context
        if tier_id in extract_tiers
        and context_fingerprints.get(tier_id)
        != _tier_fingerprint(extract_tiers[tier_id])
    )
    if changed_context:
        raise ProtectedContextModifiedError(filename, changed_context)
    missing = sorted(
        (selected - current_tiers.keys()) | (selected - extract_tiers.keys())
    )
    if missing:
        raise TierReintegrationConflictError(filename, missing)
    changed = sorted(
        tier_id
        for tier_id in selected
        if fingerprints_value.get(tier_id) != _tier_fingerprint(current_tiers[tier_id])
    )
    if changed:
        raise TierReintegrationConflictError(filename, changed)

    new_tiers = set(extract_tiers) - set(current_tiers)
    unauthorized_new = sorted(new_tiers - allowed_new)
    if unauthorized_new:
        raise ValueError(
            "This research copy added tiers outside its topic: "
            f"{', '.join(unauthorized_new)}. Add them to the research topic and download a fresh copy."
        )
    editable = selected | new_tiers

    incoming_unchanged = all(
        fingerprints_value.get(tier_id) == _tier_fingerprint(extract_tiers[tier_id])
        for tier_id in selected
    )
    extract_time_values = {
        slot_id: slot.get("TIME_VALUE")
        for slot in extract_root.findall("TIME_ORDER/TIME_SLOT")
        if (slot_id := slot.get("TIME_SLOT_ID"))
    }
    times_unchanged = all(
        extract_time_values.get(slot_id) == base_value
        for slot_id, base_value in base_time_slots.items()
    )
    if incoming_unchanged and times_unchanged and not new_tiers:
        return current_content

    outside_annotation_ids = {
        annotation_id
        for tier_id, tier in current_tiers.items()
        if tier_id not in editable
        for annotation in tier.iter()
        if (annotation_id := annotation.get("ANNOTATION_ID"))
    }
    incoming_ids = {
        annotation_id
        for tier_id in editable
        for annotation in extract_tiers[tier_id].iter()
        if (annotation_id := annotation.get("ANNOTATION_ID"))
    }
    if outside_annotation_ids & incoming_ids:
        raise TierReintegrationConflictError(filename, sorted(editable))

    replacement_tiers = {
        tier_id: deepcopy(extract_tiers[tier_id]) for tier_id in editable
    }

    current_slots = {
        slot_id: slot
        for slot in current_root.findall("TIME_ORDER/TIME_SLOT")
        if (slot_id := slot.get("TIME_SLOT_ID"))
    }
    extract_slots = {
        slot_id: slot
        for slot in extract_root.findall("TIME_ORDER/TIME_SLOT")
        if (slot_id := slot.get("TIME_SLOT_ID"))
    }
    needed_slots = {
        time_ref
        for tier_id in editable
        for annotation in extract_tiers[tier_id].iter()
        for attribute in ("TIME_SLOT_REF1", "TIME_SLOT_REF2")
        if (time_ref := annotation.get(attribute))
    }
    time_order = current_root.find("TIME_ORDER")
    if time_order is None:
        raise ValueError("Accepted EAF has no time order")
    outside_time_refs = {
        time_ref
        for tier_id, tier in current_tiers.items()
        if tier_id not in editable
        for annotation in tier.iter()
        for attribute in ("TIME_SLOT_REF1", "TIME_SLOT_REF2")
        if (time_ref := annotation.get(attribute))
    }
    reserved_slot_ids = set(current_slots) | set(extract_slots)
    for slot_id in sorted(needed_slots):
        incoming_slot = extract_slots.get(slot_id)
        if incoming_slot is None:
            raise ValueError(f"Research copy is missing time slot {slot_id}")
        existing_slot = current_slots.get(slot_id)
        if existing_slot is None:
            time_order.append(deepcopy(incoming_slot))
        elif existing_slot.get("TIME_VALUE") != incoming_slot.get("TIME_VALUE"):
            if existing_slot.get("TIME_VALUE") != base_time_slots.get(slot_id):
                raise TierReintegrationConflictError(filename, sorted(editable))
            if slot_id in outside_time_refs:
                suffix = 1
                new_slot_id = f"{slot_id}_elanora_{suffix}"
                while new_slot_id in reserved_slot_ids:
                    suffix += 1
                    new_slot_id = f"{slot_id}_elanora_{suffix}"
                reserved_slot_ids.add(new_slot_id)
                new_slot = deepcopy(incoming_slot)
                new_slot.set("TIME_SLOT_ID", new_slot_id)
                time_order.append(new_slot)
                for tier in replacement_tiers.values():
                    for annotation in tier.iter():
                        for attribute in ("TIME_SLOT_REF1", "TIME_SLOT_REF2"):
                            if annotation.get(attribute) == slot_id:
                                annotation.set(attribute, new_slot_id)
            else:
                existing_slot.set("TIME_VALUE", incoming_slot.get("TIME_VALUE"))

    for tier_id in selected:
        old_tier = current_tiers[tier_id]
        old_tier.getparent().replace(old_tier, replacement_tiers[tier_id])

    # New topic tiers are appended after existing tiers. Their parent references
    # remain valid because required parent tiers were retained in the extract.
    first_linguistic_type = current_root.find("LINGUISTIC_TYPE")
    insert_at = (
        current_root.index(first_linguistic_type)
        if first_linguistic_type is not None
        else len(current_root)
    )
    for tier_id in sorted(new_tiers):
        current_root.insert(insert_at, replacement_tiers[tier_id])
        insert_at += 1

    current_types = {
        item.get("LINGUISTIC_TYPE_ID")
        for item in current_root.findall("LINGUISTIC_TYPE")
    }
    for tier_id in sorted(new_tiers):
        type_id = extract_tiers[tier_id].get("LINGUISTIC_TYPE_REF")
        if not type_id or type_id in current_types:
            continue
        source_type = extract_root.find(
            f"LINGUISTIC_TYPE[@LINGUISTIC_TYPE_ID='{type_id}']"
        )
        if source_type is None:
            raise ValueError(f"New tier {tier_id} has no valid linguistic type")
        first_locale = current_root.find("LOCALE")
        type_insert_at = (
            current_root.index(first_locale)
            if first_locale is not None
            else len(current_root)
        )
        current_root.insert(type_insert_at, deepcopy(source_type))
        current_types.add(type_id)

    result = etree.tostring(
        current_root.getroottree(),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )
    validate_eaf(result)
    return result
