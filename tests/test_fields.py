import math

import pytest

from collface_scraper.errors import ExtractionError
from collface_scraper.fields import field_key, from_pairs, sheets_safe, validate_fields


def test_exact_labels_preserve_section_context_and_repetitions():
    value = from_pairs(
        [
            ("Academics", "Major", "Computer Science"),
            ("Activities", "Group", "First"),
            ("Activities", "Group", "Second"),
            ("Contact", "Phone / Mobile", "00123"),
            ("Contact", "Missing", ""),
        ]
    )
    assert value["Academics/Major"] == "Computer Science"
    assert value["Activities/Group"] == ["First", "Second"]
    assert value["Contact/Phone ~1 Mobile"] == "00123"
    assert value["Contact/Missing"] == ""


def test_empty_label_and_non_json_value_are_rejected():
    with pytest.raises(ExtractionError, match="display label"):
        field_key("Profile", " ")
    with pytest.raises(ExtractionError, match="serialized"):
        validate_fields({"Profile/Value": math.nan})


@pytest.mark.parametrize("value", ["=1+1", "+12", "-10", "@name", "00123"])
def test_spreadsheet_sensitive_values_import_as_text(value):
    assert sheets_safe(value) == "'" + value


def test_unicode_and_ordinary_values_are_unchanged():
    assert sheets_safe("東京, café") == "東京, café"

