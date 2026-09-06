from decimal import Decimal
from typing import Any

import regex as re

from app.core.centralized_logging import get_logger

logger = get_logger()


class ValidationUtils:
    """Common validation functions."""

    @staticmethod
    def is_valid_string(value: Any, min_length: int = 1) -> bool:
        """Check if the value is a valid string of minimum length."""
        result = isinstance(value, str) and len(value.strip()) >= min_length
        logger.debug(
            f"is_valid_string: value='{value}' min_length={min_length} result={result}"
        )
        return result

    @staticmethod
    def is_valid_time_range(start_time: Decimal, end_time: Decimal) -> bool:
        """Check if the time range is valid."""
        result = (
            isinstance(start_time, Decimal)
            and isinstance(end_time, Decimal)
            and start_time >= 0
            and end_time >= start_time
        )
        logger.debug(
            f"is_valid_time_range: start={start_time} end={end_time} result={result}"
        )
        return result

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize the filename by removing invalid characters."""
        if not filename:
            logger.error("sanitize_filename: empty filename")
            raise ValueError("Filename cannot be empty")
        invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")
        logger.info(
            f"sanitize_filename: original='{filename}' sanitized='{sanitized.strip()}'"
        )
        return sanitized.strip()

    @staticmethod
    def validate_user_id(user_id: Any) -> int:
        """Validate and return the user ID as a positive integer."""
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"validate_user_id: invalid user_id={user_id}")
            raise ValueError("User ID must be a positive integer")
        logger.debug(f"validate_user_id: user_id={user_id} is valid")
        return user_id

    @staticmethod
    def is_filename_compliant(standard: dict | None, filename: str) -> bool:
        """Check if a filename complies with the given naming standard.

        Args:
            standard: Dict containing 'pattern' and 'components'.
            filename: The filename to check (without extension).

        Returns:
            True if compliant, False otherwise.

        """
        logger.debug(
            f"is_filename_compliant called with standard: {standard}, filename: {filename}"
        )
        if (
            not standard
            or not standard.get("pattern")
            or not isinstance(standard.get("components"), list)
        ):
            logger.debug(
                "No valid standard found. Could be no standard or missing pattern/components."
            )
            return True

        name_without_ext = filename.replace(".eaf", "")
        components = standard["components"]
        pattern = standard["pattern"]
        logger.debug(f"Components: {components}, Pattern: {pattern}")

        normalized_components = ValidationUtils._normalize_components(components)
        pattern = ValidationUtils._build_pattern(pattern, normalized_components)
        top_rx = ValidationUtils._compile_regex(pattern)
        if not top_rx:
            return False

        match = top_rx.match(name_without_ext)
        if not match:
            return False

        return ValidationUtils._check_all_components(match, normalized_components)

    @staticmethod
    def _normalize_components(components: list) -> list[dict]:
        """Normalize component fields for consistency."""
        logger.debug(f"_normalize_components called with components: {components}")
        normalized = []
        for i, comp in enumerate(components):
            logger.debug(f"Processing component {i}: {comp}")
            name = comp.get("name")
            if not name:
                logger.warning(f"Component {i} missing 'name': {comp}. Skipping.")
                continue
            accepted_values = []
            if isinstance(comp.get("accepted_values"), list):
                accepted_values = comp["accepted_values"]
            elif isinstance(comp.get("accepted_values_str"), str):
                accepted_values = [
                    v.strip()
                    for v in comp["accepted_values_str"].split(",")
                    if v.strip()
                ]

            normalized.append(
                {
                    "name": comp.get("name"),
                    "regex": comp.get("regex") or comp.get("pattern"),
                    "accepted_values": accepted_values,
                    "fixed_value": comp.get("fixed_value")
                    or comp.get("fixed_value")
                    or comp.get("value"),
                    "numeric_range": comp.get("numeric_range")
                    or comp.get("numericRange")
                    or comp.get("numericRangeValue"),
                }
            )
        return normalized

    @staticmethod
    def _build_pattern(pattern: str, components: list[dict]) -> str | None:
        """Build the final regex pattern by replacing component placeholders."""
        logger.debug(
            f"_build_pattern called with pattern: {pattern}, components: {components}"
        )
        try:
            for i, comp in enumerate(components):
                logger.debug(f"Processing component {i} for pattern: {comp}")
                name = comp["name"]
                regex = comp["regex"]
                # Escape backslashes in the regex for use in re.sub replacement
                escaped_regex = regex.replace("\\", "\\\\")
                replacement = f"({escaped_regex})"
                logger.debug(f"Replacing {{{name}}} with {replacement}")
                pattern = re.sub(f"{{{name}}}", replacement, pattern)
                logger.debug(f"Pattern after replacement for '{name}': {pattern}")
            logger.debug(f"Final pattern: {pattern}")
            return pattern
        except re.error as e:
            logger.error(f"Error during pattern replacement for '{name}': {e}")
            return None

    @staticmethod
    def _compile_regex(pattern: str) -> re.Pattern | None:
        """Compile the regex pattern."""
        logger.debug(f"_compile_regex called with pattern: {pattern}")
        try:
            compiled = re.compile(f"^{pattern}$")
            logger.debug("Regex compiled successfully")
            return compiled
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern}, error: {e}")
            return None

    @staticmethod
    def _check_all_components(match: re.Match, components: list[dict]) -> bool:
        """Check all components against the match."""
        for i, comp in enumerate(components):
            value = match.group(i + 1)
            if not ValidationUtils._check_component(comp, value):
                return False
        return True

    @staticmethod
    def _check_component(comp: dict, value: str) -> bool:
        """Check a single component's constraints.

        Args:
            comp: Component dictionary.
            value: Value to check.

        Returns:
            True if valid, False otherwise.

        """
        if not ValidationUtils._check_regex(comp, value):
            return False
        if not ValidationUtils._check_accepted_values(comp, value):
            return False
        if not ValidationUtils._check_fixed_value(comp, value):
            return False
        return ValidationUtils._check_numeric_range(comp, value)

    @staticmethod
    def _check_regex(comp: dict, value: str) -> bool:
        """Check regex constraint."""
        regex = comp.get("regex")
        if not regex:
            return True
        try:
            rx = re.compile(regex)  # Removed re.UNICODE
            return rx.match(value) is not None
        except re.error:
            return False

    @staticmethod
    def _check_accepted_values(comp: dict, value: str) -> bool:
        """Check accepted values constraint."""
        accepted_values = comp.get("accepted_values")
        if not accepted_values:
            return True
        for av in accepted_values:
            if ValidationUtils._is_accepted_value(av, value):
                return True
        return False

    @staticmethod
    def _check_fixed_value(comp: dict, value: str) -> bool:
        """Check fixed value constraint."""
        fixed = comp.get("fixed_value")
        return fixed is None or str(fixed) == str(value)

    @staticmethod
    def _check_numeric_range(comp: dict, value: str) -> bool:
        """Check numeric range constraint."""
        numeric_range = comp.get("numeric_range")
        if not numeric_range:
            return True
        if isinstance(numeric_range, str):
            return ValidationUtils._check_numeric_range_str(numeric_range, value)
        if isinstance(numeric_range, dict):
            return ValidationUtils._check_numeric_range_dict(numeric_range, value)
        return False

    @staticmethod
    def _check_numeric_range_str(numeric_range: str, value: str) -> bool:
        """Check string-format numeric range."""
        range_match = re.match(r"^(\d+)-(\d+)$", numeric_range.strip())
        if not range_match:
            return False
        min_val, max_val = int(range_match.group(1)), int(range_match.group(2))
        width = len(range_match.group(1))
        try:
            num = int(value)
            return len(value) == width and min_val <= num <= max_val
        except ValueError:
            return False

    @staticmethod
    def _check_numeric_range_dict(numeric_range: dict, value: str) -> bool:
        """Check dict-format numeric range."""
        try:
            num = int(value)
            return not (
                ("width" in numeric_range and len(value) != numeric_range["width"])
                or ("min" in numeric_range and num < numeric_range["min"])
                or ("max" in numeric_range and num > numeric_range["max"])
            )
        except (ValueError, KeyError):
            return False

    @staticmethod
    def _is_accepted_value(av: Any, value: str) -> bool:
        """Check if value matches an accepted value.

        Args:
            av: Accepted value (string, regex, or range).
            value: Value to check.

        Returns:
            True if matches, False otherwise.

        """
        av_str = str(av)
        if av_str == value:
            return True
        if re.match(r"^/.*/[gimsuy]*$", av_str):
            return ValidationUtils._check_regex_literal(av_str, value)
        range_match = re.match(r"^(\d+)-(\d+)$", av_str.strip())
        if range_match:
            return ValidationUtils._check_range_value(range_match, value)
        return False

    @staticmethod
    def _check_regex_literal(av_str: str, value: str) -> bool:
        """Check regex literal accepted value."""
        try:
            parts = re.match(r"^/(.*)/([gimsuy]*)$", av_str)
            rx = re.compile(parts.group(1), parts.group(2))
            return rx.match(value) is not None
        except re.error:
            return False

    @staticmethod
    def _check_range_value(range_match: re.Match, value: str) -> bool:
        """Check range accepted value."""
        min_val, max_val = int(range_match.group(1)), int(range_match.group(2))
        width = len(range_match.group(1))
        try:
            num = int(value)
            return len(value) == width and min_val <= num <= max_val
        except ValueError:
            return False


logger.debug(f"Using re module: {re.__name__}")
