from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileRef:
    source_id: str
    url: str


@dataclass(frozen=True)
class ListingPage:
    profiles: tuple[ProfileRef, ...]
    next_cursor: str | None
    total: int | None
    exhaustive: bool


Fields = dict[str, Any]
