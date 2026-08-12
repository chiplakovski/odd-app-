"""Core data model for a parsed work-list line item."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WorkItem:
    number: int
    owner_no: str
    status: str
    description: str
    summary: str = ""
    group: str = ""
    included: bool = True

    @property
    def number_text(self) -> str:
        return str(self.number)
