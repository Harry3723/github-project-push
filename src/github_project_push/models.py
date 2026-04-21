from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RepoCandidate:
    full_name: str          # owner/repo, used as unique_id
    html_url: str
    name: str
    owner: str
    description: str
    stars: int
    language: str | None
    topics: list[str]
    pushed_at: datetime
    created_at: datetime
    category: str           # the search category that found this repo
    matched_queries: set[str] = field(default_factory=set)

    @property
    def unique_id(self) -> str:
        return self.full_name.lower()


@dataclass
class RepoScore:
    stars_score: float
    recency_score: float
    completeness_score: float
    final_score: float
    reason: str = ""


@dataclass
class RunResult:
    success: bool
    skipped: bool
    message: str
    report: str
    report_path: str
