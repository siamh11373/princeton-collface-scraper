"""Dynamic field handling independent of CollFace's field vocabulary."""

import json
import re
from collections.abc import Iterable
from typing import Any

from .errors import ExtractionError
from .models import Fields


def field_key(section: str, label: str) -> str:
    def escape(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    clean_section = " ".join(section.split())
    clean_label = " ".join(label.split())
    if not clean_label:
        raise ExtractionError("A visible profile value has no display label.")
    return "/".join(escape(part) for part in (clean_section, clean_label) if part)


def from_pairs(pairs: Iterable[tuple[str, str, Any]]) -> Fields:
    grouped: dict[str, list[Any]] = {}
    for section, label, value in pairs:
        grouped.setdefault(field_key(section, label), []).append(value)
    if not grouped:
        raise ExtractionError("No dynamically labelled profile fields were found.")
    return {key: values[0] if len(values) == 1 else values for key, values in grouped.items()}


def validate_fields(value: Any) -> Fields:
    if not isinstance(value, dict) or not value:
        raise ExtractionError("Expected a nonempty field mapping.")
    if not all(isinstance(key, str) and key.strip() for key in value):
        raise ExtractionError("Field keys must be nonempty strings.")
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raise ExtractionError("A field value cannot be serialized safely.") from None
    return dict(value)


def csv_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def spreadsheet_sensitive(value: str) -> bool:
    return bool(
        value and (value.lstrip().startswith(("=", "+", "-", "@")) or re.fullmatch(r"0\d+", value))
    )


def sheets_safe(value: Any) -> str:
    rendered = csv_text(value)
    return "'" + rendered if spreadsheet_sensitive(rendered) else rendered

