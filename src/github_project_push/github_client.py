from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

from github_project_push.models import RepoCandidate, RepoScore


_GITHUB_API = "https://api.github.com"
_DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_dt(s: str | None) -> datetime:
    if not s:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)
    return datetime.strptime(s, _DATE_FMT).replace(tzinfo=timezone.utc)


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/vnd.github+json"
        self._session.headers["X-GitHub-Api-Version"] = "2022-11-28"
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

    def search_repos(self, query: str, per_page: int = 15) -> list[dict]:
        url = f"{_GITHUB_API}/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
        try:
            resp = self._session.get(url, params=params, timeout=15)
            # Respect rate-limit: if secondary rate limit hit, back off briefly
            if resp.status_code == 403:
                retry_after = int(resp.headers.get("Retry-After", 10))
                time.sleep(min(retry_after, 30))
                resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception:
            return []

    def to_candidate(self, raw: dict, category: str) -> RepoCandidate | None:
        full_name = raw.get("full_name", "")
        if not full_name:
            return None
        description = (raw.get("description") or "").strip()
        return RepoCandidate(
            full_name=full_name,
            html_url=raw.get("html_url", f"https://github.com/{full_name}"),
            name=raw.get("name", ""),
            owner=(raw.get("owner") or {}).get("login", ""),
            description=description,
            stars=raw.get("stargazers_count", 0),
            language=raw.get("language"),
            topics=raw.get("topics") or [],
            pushed_at=_parse_dt(raw.get("pushed_at")),
            created_at=_parse_dt(raw.get("created_at")),
            category=category,
        )


def score_repo(repo: RepoCandidate, now: datetime) -> RepoScore:
    # Stars score: log scale, 100k stars → 40 pts
    stars_score = min(40.0, math.log10(max(repo.stars, 1)) / math.log10(100_000) * 40)

    # Recency score: days since last push
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    days_since = max(0, (now - repo.pushed_at).days)
    if days_since <= 30:
        recency_score = 30.0
    elif days_since <= 90:
        recency_score = 20.0
    elif days_since <= 365:
        recency_score = 10.0
    else:
        recency_score = 0.0

    # Completeness: description + topics
    completeness_score = 0.0
    if repo.description:
        completeness_score += 15.0
    if repo.topics:
        completeness_score += min(15.0, len(repo.topics) * 3.0)

    final_score = stars_score + recency_score + completeness_score
    return RepoScore(
        stars_score=stars_score,
        recency_score=recency_score,
        completeness_score=completeness_score,
        final_score=final_score,
    )
