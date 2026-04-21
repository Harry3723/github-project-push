from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests

from github_project_push.models import RepoCandidate


_TRENDING_URL = "https://github.com/trending"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _TrendingParser(HTMLParser):
    """Minimal state-machine parser for github.com/trending HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.repos: list[dict] = []
        self._in_article = False
        self._article: dict = {}
        self._depth = 0                # nesting depth inside current article
        self._capture_h2_link = False
        self._capture_desc = False
        self._capture_lang = False
        self._capture_stars_week = False
        self._desc_depth = 0

    # ------------------------------------------------------------------ helpers
    def _start_article(self) -> None:
        self._in_article = True
        self._article = {"full_name": "", "description": "", "language": None, "stars_week": 0}
        self._depth = 0

    def _end_article(self) -> None:
        self._in_article = False
        if self._article.get("full_name"):
            self.repos.append(self._article)
        self._article = {}

    # ------------------------------------------------------------------ parser callbacks
    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr = dict(attrs)
        if tag == "article" and "Box-row" in attr.get("class", ""):
            self._start_article()
            return

        if not self._in_article:
            return

        self._depth += 1

        # Repo link inside <h2>
        if tag == "a" and not self._article["full_name"]:
            href = attr.get("href", "").strip("/")
            if href.count("/") == 1:
                self._article["full_name"] = href
                self._capture_h2_link = True
                return

        # Description <p>
        if tag == "p" and "color-fg-muted" in attr.get("class", ""):
            self._capture_desc = True
            self._desc_depth = self._depth
            return

        # Language
        if tag == "span" and attr.get("itemprop") == "programmingLanguage":
            self._capture_lang = True
            return

        # Stars this week <span class="... float-sm-right">
        if tag == "span" and "float-sm-right" in attr.get("class", ""):
            self._capture_stars_week = True
            return

    def handle_endtag(self, tag: str) -> None:
        if not self._in_article:
            return
        if tag == "article":
            self._end_article()
            return
        if tag == "a" and self._capture_h2_link:
            self._capture_h2_link = False
        if tag == "p" and self._capture_desc and self._depth == self._desc_depth:
            self._capture_desc = False
        if tag == "span":
            self._capture_lang = False
            self._capture_stars_week = False
        self._depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._in_article:
            return
        text = _clean(data)
        if not text:
            return
        if self._capture_desc:
            self._article["description"] += text
        if self._capture_lang:
            self._article["language"] = text
        if self._capture_stars_week:
            m = re.search(r"[\d,]+", text)
            if m:
                self._article["stars_week"] = int(m.group().replace(",", ""))


def scrape_trending(since: str = "weekly") -> list[RepoCandidate]:
    try:
        resp = requests.get(
            _TRENDING_URL,
            params={"since": since},
            headers=_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
    except Exception:
        return []

    parser = _TrendingParser()
    parser.feed(resp.text)

    now = datetime.now(timezone.utc)
    results: list[RepoCandidate] = []
    for raw in parser.repos:
        full_name = raw["full_name"]
        parts = full_name.split("/", 1)
        if len(parts) != 2:
            continue
        owner, name = parts
        results.append(
            RepoCandidate(
                full_name=full_name,
                html_url=f"https://github.com/{full_name}",
                name=name,
                owner=owner,
                description=_clean(raw.get("description", "")),
                stars=raw.get("stars_week", 0),   # use weekly stars as proxy
                language=raw.get("language"),
                topics=[],
                pushed_at=now,   # trending → assumed very recent
                created_at=now,
                category="GitHub Trending",
            )
        )
    return results
