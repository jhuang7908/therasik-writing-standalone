from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CommunityEvent:
    title: str
    start_date: str  # YYYY-MM-DD
    source: str
    url: str = ""
    start_time: str = ""
    end_time: str = ""
    location: str = ""
    borough: str = ""
    category: str = "general"
    cost: str = ""
    description: str = ""
    is_free: bool | None = None
    score: int = 0
    score_reasons: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    routine: bool = False
    published_at: str = ""  # source announcement ISO or YYYY-MM-DD

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommunityEvent:
        return cls(
            title=str(data.get("title") or ""),
            start_date=str(data.get("start_date") or ""),
            source=str(data.get("source") or ""),
            url=str(data.get("url") or ""),
            start_time=str(data.get("start_time") or ""),
            end_time=str(data.get("end_time") or ""),
            location=str(data.get("location") or ""),
            borough=str(data.get("borough") or ""),
            category=str(data.get("category") or "general"),
            cost=str(data.get("cost") or ""),
            description=str(data.get("description") or ""),
            is_free=data.get("is_free"),
            score=int(data.get("score") or 0),
            score_reasons=list(data.get("score_reasons") or []),
            tags=list(data.get("tags") or []),
            routine=bool(data.get("routine")),
            published_at=str(data.get("published_at") or ""),
        )
