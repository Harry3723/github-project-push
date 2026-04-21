from __future__ import annotations

from datetime import datetime

from github_project_push.models import RepoCandidate, RepoScore


def _stars_label(stars: int) -> str:
    if stars >= 1000:
        return f"{stars / 1000:.1f}k"
    return str(stars)


def _days_ago(pushed_at: datetime, now: datetime) -> str:
    from datetime import timezone as _tz
    _now = now.astimezone(_tz.utc)
    _pushed = pushed_at.astimezone(_tz.utc) if pushed_at.tzinfo else pushed_at.replace(tzinfo=_tz.utc)
    days = max(0, (_now - _pushed).days)
    if days == 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days < 30:
        return f"{days} 天前"
    if days < 365:
        return f"{days // 30} 个月前"
    return f"{days // 365} 年前"


def _repo_block(index: int, repo: RepoCandidate, score: RepoScore, reason: str, now: datetime) -> str:
    lang_str = repo.language or "多语言"
    topic_str = ", ".join(f"`{t}`" for t in repo.topics[:5]) if repo.topics else "—"
    desc = repo.description or "（暂无描述）"
    pushed_str = _days_ago(repo.pushed_at, now)
    reason_str = reason or "适合 ECE 博士生日常研究使用"

    lines = [
        f"### {index}. [{repo.full_name}]({repo.html_url})",
        "",
        f"⭐ **{_stars_label(repo.stars)}** | **语言**: {lang_str} | **最近更新**: {pushed_str}",
        "",
        f"**简介**: {desc}",
        "",
        f"**话题标签**: {topic_str}",
        "",
        f"**为什么推荐**: {reason_str}",
    ]
    return "\n".join(lines)


def render_report(
    generated_at: datetime,
    triples: list[tuple[RepoCandidate, RepoScore, str]],
) -> str:
    header_lines = [
        f"# GitHub 项目周推 | {generated_at.strftime('%Y-%m-%d %H:%M')} ({generated_at.tzname()})",
        "",
        "> 光子计算 AI 加速方向 ECE 博士生周度精选",
        "",
        f"> 本期共 {len(triples)} 个项目，由 AI 从候选池中择优推荐",
        "",
        "---",
    ]

    body_lines: list[str] = ["## 本周推荐", ""]
    for i, (repo, score, reason) in enumerate(triples, start=1):
        body_lines.append(_repo_block(i, repo, score, reason, generated_at))
        if i < len(triples):
            body_lines.append("")
            body_lines.append("---")
            body_lines.append("")

    return "\n".join(header_lines + body_lines).strip() + "\n"
