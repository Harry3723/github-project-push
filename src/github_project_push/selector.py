from __future__ import annotations

import json

import anthropic

from github_project_push.categories import USER_PROFILE
from github_project_push.models import RepoCandidate, RepoScore


def _format_candidates(pairs: list[tuple[RepoCandidate, RepoScore]]) -> str:
    lines: list[str] = []
    for i, (repo, score) in enumerate(pairs, start=1):
        stars_str = f"{repo.stars / 1000:.1f}k" if repo.stars >= 1000 else str(repo.stars)
        topic_str = ", ".join(repo.topics[:6]) if repo.topics else "none"
        lines.append(
            f"{i}. {repo.full_name} (⭐ {stars_str}, {repo.language or 'N/A'})\n"
            f"   Description: {repo.description or '(none)'}\n"
            f"   Topics: {topic_str}\n"
            f"   URL: {repo.html_url}"
        )
    return "\n\n".join(lines)


_SYSTEM = "You are a research productivity advisor. Respond only with valid JSON — no markdown fences, no extra text."

_USER_TEMPLATE = """\
User profile:
{profile}

From the {n} GitHub projects below, select exactly 3 that would be MOST useful for this user's \
day-to-day research life. The candidates come from two sources:
- GitHub Search API (established tools with high star counts)
- GitHub Trending this week (newly emerging projects with momentum)

Prioritize:
1. Tools that save time finding or aggregating information (AI assistants, paper feeds, search tools)
2. Tools that improve daily workflow (terminal, automation, writing, note-taking)
3. Tools with strong general utility that any researcher would genuinely benefit from
4. Aim for variety — ideally not all 3 from the same category

Return a JSON array of exactly 3 objects — no other text:
[{{"full_name": "owner/repo", "reason": "1-2 句中文推荐理由，说明为什么对这个用户有用"}}, ...]

Candidates:
{candidates}
"""


class LLMSelector:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def select(
        self,
        pairs: list[tuple[RepoCandidate, RepoScore]],
        count: int = 3,
    ) -> list[tuple[RepoCandidate, RepoScore, str]]:
        """Return (repo, score, reason) for the top `count` selected by the LLM."""
        if len(pairs) <= count:
            return [(r, s, "") for r, s in pairs]

        candidates_text = _format_candidates(pairs)
        prompt = _USER_TEMPLATE.format(
            profile=USER_PROFILE.strip(),
            n=len(pairs),
            candidates=candidates_text,
        )

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            selections: list[dict] = json.loads(raw)
        except Exception as exc:
            # Fallback: return top `count` by existing score order, no reasons
            print(f"[selector] LLM call failed ({exc}), falling back to score-based selection.")
            return [(r, s, "") for r, s in pairs[:count]]

        # Map full_name back to (repo, score) pairs
        lookup = {repo.full_name.lower(): (repo, score) for repo, score in pairs}
        results: list[tuple[RepoCandidate, RepoScore, str]] = []
        for sel in selections[:count]:
            key = sel.get("full_name", "").lower()
            reason = sel.get("reason", "")
            if key in lookup:
                repo, score = lookup[key]
                results.append((repo, score, reason))

        # If LLM returned fewer than count valid results, pad with top scored
        if len(results) < count:
            used = {r.full_name.lower() for r, _, _ in results}
            for repo, score in pairs:
                if repo.full_name.lower() not in used:
                    results.append((repo, score, ""))
                if len(results) >= count:
                    break

        return results
