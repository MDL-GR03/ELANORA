"""File processing utilities for ELAN files."""

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from lxml import etree

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_PROJECTS_BASE_PATH

logger = get_logger()


def get_elanora_projects_base_path() -> str:
    """Get the base path for elanora_projects directory."""
    try:
        configured_path = ELAN_PROJECTS_BASE_PATH
        logger.debug("Using the configured ELAN project storage root")

        # If it's a relative path, make it relative to the repo root
        if not Path(configured_path).is_absolute():
            # Navigate up from current file to repo root
            current_dir = Path(__file__).resolve()
            # file_processing.py -> utils -> app -> backend -> website -> repo_root
            repo_root = current_dir.parent.parent.parent.parent.parent
            base_path = str(repo_root / configured_path)
            logger.debug("Resolved the relative ELAN project storage root")
            return base_path
        else:
            # It's already an absolute path
            return configured_path

    except ImportError:
        # Fallback to calculated path
        current_dir = Path(__file__).resolve()
        # Navigate up: file_processing.py -> utils -> app -> backend -> website -> repo_root
        repo_root = current_dir.parent.parent.parent.parent.parent
        base_path = str(repo_root / "elanora_projects")
        logger.debug("Calculated the fallback ELAN project storage root")
        return base_path


def make_path_relative_to_projects(absolute_path: str) -> str:
    """Convert absolute path to relative path from elanora_projects directory."""
    base_path = get_elanora_projects_base_path()
    abs_path = Path(absolute_path).resolve()
    base = Path(base_path).resolve()

    logger.debug("Converting an ELAN project path to its storage-relative form")

    try:
        relative_path = abs_path.relative_to(base)
        result = str(relative_path).replace(
            "\\", "/"
        )  # Use forward slashes for consistency
        logger.debug("Converted an ELAN project path to storage-relative form")
        return result
    except ValueError:
        # Path is not under elanora_projects, return as-is but log warning
        logger.warning("Path is outside the configured ELAN project storage root")
        return absolute_path


def make_path_absolute_from_projects(relative_path: str) -> str:
    """Convert relative path from elanora_projects to absolute path."""
    base_path = get_elanora_projects_base_path()
    return str(Path(base_path) / relative_path)


class ElanFileProcessor:
    """Utilities for processing ELAN XML files."""

    @staticmethod
    def validate_elan_file(file_path: str) -> Path:
        """Validate and return Path object for ELAN file."""
        file_path_obj = Path(file_path)
        logger.info("Validating an ELAN file")
        if not file_path_obj.exists():
            logger.error("ELAN file validation failed: file not found")
            raise FileNotFoundError(f"ELAN file not found: {file_path}")
        if file_path_obj.suffix.lower() != ".eaf":
            logger.error("ELAN file validation failed: unsupported extension")
            raise ValueError(f"Not an ELAN file: {file_path}")
        logger.debug("ELAN file path validation passed")
        return file_path_obj

    @staticmethod
    def get_file_info(file_path_obj: Path) -> dict:
        """Extract basic file information."""
        last_modified_timestamp = os.path.getmtime(file_path_obj)
        last_modified = datetime.fromtimestamp(last_modified_timestamp)

        # Convert absolute path to relative path for storage
        absolute_path = str(file_path_obj.absolute())
        relative_path = make_path_relative_to_projects(absolute_path)

        logger.debug("Converted ELAN file metadata to storage-relative form")

        info = {
            "filename": file_path_obj.name,
            "file_path": relative_path,  # Store relative path
            "file_size": file_path_obj.stat().st_size,
            "last_modified": last_modified,
        }
        logger.info("Extracted ELAN file metadata")
        return info

    @staticmethod
    def extract_time_slots(root: etree._Element) -> dict[str, int]:
        """Extract time slots from ELAN XML root."""
        time_slots = {}
        for time_slot in root.findall(".//TIME_SLOT", namespaces=None):
            slot_id = time_slot.get("TIME_SLOT_ID", None)
            time_value = int(time_slot.get("TIME_VALUE", 0))
            if slot_id:
                time_slots[slot_id] = time_value
        logger.debug(f"Extracted {len(time_slots)} time slots")
        return time_slots

    @staticmethod
    def safe_get_text(element: etree._Element | None) -> str | None:
        """Safely get text from XML element."""
        if element is None or not element.text:
            logger.warning("safe_get_text: element is None or empty")
            return None
        text = element.text.strip()
        logger.debug("Extracted text from an XML element")
        return text

    @staticmethod
    def convert_time_to_decimal(time_value: int) -> Decimal:
        """Convert milliseconds to decimal seconds."""
        decimal_time = Decimal(time_value) / 1000
        logger.debug(f"convert_time_to_decimal: {time_value}ms -> {decimal_time}s")
        return decimal_time

    @staticmethod
    def find_files_in_directory(
        directory_path: str, pattern: str = "*.eaf"
    ) -> list[Path]:
        """Find all ELAN files in flat directory (no recursion)."""
        directory = Path(directory_path)
        logger.info("Searching a project directory for ELAN files")
        if not directory.exists():
            logger.error("ELAN directory scan failed: directory not found")
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        files = list(directory.glob(pattern))
        logger.info(f"Found {len(files)} ELAN files in directory")
        return files

    @staticmethod
    def extract_media_descriptors(root: etree._Element) -> list[dict]:
        """Extract all MEDIA_DESCRIPTOR elements from ELAN XML root."""
        media_descriptors = []
        for media_elem in root.findall(".//MEDIA_DESCRIPTOR", namespaces=None):
            media_info = {
                "media_url": media_elem.get("MEDIA_URL"),
                "mime_type": media_elem.get("MIME_TYPE"),
                "relative_media_url": media_elem.get("RELATIVE_MEDIA_URL"),
            }
            media_descriptors.append(media_info)
        logger.info(f"Extracted {len(media_descriptors)} media descriptors")
        return media_descriptors


class XmlAttributeExtractor:
    """Utilities for extracting attributes from XML elements."""

    @staticmethod
    def get_tier_attributes(tier_element: etree._Element) -> dict:
        """Extract tier attributes from XML element."""
        attrs = {
            "tier_name": tier_element.get("TIER_ID", None),
            "parent_tier_name": tier_element.get("PARENT_REF", None),
        }
        logger.debug("Extracted tier relationship attributes")
        return attrs

    @staticmethod
    def get_annotation_attributes(annotation: etree._Element) -> dict:
        """Extract annotation attributes from XML element."""
        attrs = {
            "annotation_id": annotation.get("ANNOTATION_ID", None),
            "time_slot_ref1": annotation.get("TIME_SLOT_REF1", None),
            "time_slot_ref2": annotation.get("TIME_SLOT_REF2", None),
        }
        logger.debug("Extracted annotation timing references")
        return attrs

    @staticmethod
    def get_alignable_annotation_attributes(
        annotation: etree._Element, time_slots: dict[str, int]
    ) -> dict | None:
        """Extract information from an alignable annotation."""
        annotation_value_elem = annotation.find("ANNOTATION_VALUE", namespaces=None)
        if annotation_value_elem is None or not annotation_value_elem.text:
            logger.warning(
                "get_alignable_annotation_attributes: missing annotation value"
            )
            return None
        start_ref = annotation.get("TIME_SLOT_REF1", None)
        end_ref = annotation.get("TIME_SLOT_REF2", None)
        start_time = time_slots.get(start_ref, 0) if start_ref else 0
        end_time = time_slots.get(end_ref, 0) if end_ref else 0
        attrs = {
            "annotation_id": annotation.get("ANNOTATION_ID", None),
            "annotation_value": annotation_value_elem.text.strip(),
            "start_time": Decimal(start_time) / 1000,
            "end_time": Decimal(end_time) / 1000,
        }
        logger.debug("Extracted alignable annotation")
        return attrs

    @staticmethod
    def get_ref_annotation_attributes(
        annotation: etree._Element,
    ) -> dict | None:
        """Extract information from a reference annotation."""
        annotation_value_elem = annotation.find("ANNOTATION_VALUE", namespaces=None)
        if annotation_value_elem is None or not annotation_value_elem.text:
            logger.warning("get_ref_annotation_attributes: missing annotation value")
            return None
        attrs = {
            "annotation_id": annotation.get("ANNOTATION_ID", None),
            "annotation_value": annotation_value_elem.text.strip(),
            "start_time": Decimal(0),
            "end_time": Decimal(0),
        }
        logger.debug("Extracted reference annotation")
        return attrs


def list_untracked_contents(folder_path: Path, parent_path: Path) -> list:
    items = []
    for path in folder_path.rglob("*"):
        rel_path = str(path.relative_to(parent_path))
        if path.is_dir():
            items.append({"filename": rel_path + "/", "status": "untracked"})
        else:
            items.append({"filename": rel_path, "status": "untracked"})
    return items
