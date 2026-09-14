"""Validated, sanitized description of observed CollFace structures."""

import json
from pathlib import Path

from .config import TARGET
from .errors import ConfigurationError


def load_contract(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ConfigurationError(
            "No verified CollFace contract exists. Run an authorized inspection first."
        ) from None
    if not isinstance(value, dict) or value.get("target") != TARGET:
        raise ConfigurationError("The site contract does not describe the approved target.")
    if value.get("mode") != "dom":
        raise ConfigurationError("Only an observed DOM contract is currently supported.")
    if not isinstance(value.get("evidence"), str) or not value["evidence"].strip():
        raise ConfigurationError("The site contract must record sanitized observation evidence.")
    if type(value.get("exhaustive")) is not bool:
        raise ConfigurationError("The contract must make an explicit exhaustive claim.")
    if value["exhaustive"] and not value.get("enumeration_evidence"):
        raise ConfigurationError("Exhaustive discovery requires recorded enumeration evidence.")
    listing = value.get("listing")
    profile = value.get("profile")
    if not isinstance(listing, dict) or not isinstance(profile, dict):
        raise ConfigurationError("The contract must describe listing and profile structures.")
    if not {"url", "cards", "profile_link"}.issubset(listing):
        raise ConfigurationError("The listing contract is incomplete.")
    if not listing.get("id_attribute") and not listing.get("id_from_url"):
        raise ConfigurationError("The listing contract must define a stable identity source.")
    if not {"root", "sections", "heading", "rows", "label", "value"}.issubset(profile):
        raise ConfigurationError("The profile contract is incomplete.")
    return value
