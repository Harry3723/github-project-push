from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from github_project_push.categories import SEARCH_QUERIES
from github_project_push.config import Config
from github_project_push.email_sender import EmailSender
from github_project_push.github_client import GitHubClient, score_repo
from github_project_push.history import HistoryStore
from github_project_push.models import RepoCandidate, RepoScore, RunResult
from github_project_push.pushplus import PushplusSender
from github_project_push.reporting import render_report
from github_project_push.selector import LLMSelector
from github_project_push.trending_client import scrape_trending


class GitHubProjectPushService:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = GitHubClient(token=config.github_token)
        self.history = HistoryStore(config.history_path)
        self.selector = LLMSelector(
            api_key=config.anthropic_api_key or "",
            model=config.llm_model,
        ) if config.anthropic_api_key else None
        self.pushplus_sender = PushplusSender(
            token=config.pushplus_token,
            topic=config.pushplus_topic,
            api_url=config.pushplus_api_url,
            max_bytes=config.pushplus_max_bytes,
        )
        self.email_sender = EmailSender(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_username=config.smtp_username,
            smtp_password=config.smtp_password,
            smtp_use_starttls=config.smtp_use_starttls,
            smtp_use_ssl=config.smtp_use_ssl,
            email_from=config.email_from,
            email_to=config.email_to,
        )

    def _collect_candidates(self, now: datetime) -> dict[str, tuple[RepoCandidate, RepoScore]]:
        unique: OrderedDict[str, tuple[RepoCandidate, RepoScore]] = OrderedDict()

        # Source 1: GitHub Search API
        for query, category in SEARCH_QUERIES:
            items = self.client.search_repos(query, per_page=self.config.per_page)
            for raw in items:
                candidate = self.client.to_candidate(raw, category)
                if candidate is None:
                    continue
                uid = candidate.unique_id
                if uid in unique:
                    unique[uid][0].matched_queries.add(query)
                else:
                    candidate.matched_queries.add(query)
                    unique[uid] = (candidate, score_repo(candidate, now))
            time.sleep(0.5 if self.config.github_token else 2.0)

        # Source 2: GitHub Trending (weekly)
        for candidate in scrape_trending(since="weekly"):
            uid = candidate.unique_id
            if uid not in unique:
                unique[uid] = (candidate, score_repo(candidate, now))

        return unique

    def _top_by_score(
        self,
        candidates: dict[str, tuple[RepoCandidate, RepoScore]],
        exclude_ids: set[str],
        n: int,
    ) -> list[tuple[RepoCandidate, RepoScore]]:
        available = [
            (repo, score)
            for uid, (repo, score) in candidates.items()
            if uid not in exclude_ids
        ]
        available.sort(key=lambda x: x[1].final_score, reverse=True)
        return available[:n]

    def _write_report(self, report: str, now: datetime) -> Path:
        self.config.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.config.report_dir / f"github_project_report_{now.strftime('%Y%m%d_%H%M%S')}.md"
        report_path.write_text(report, encoding="utf-8")
        (self.config.report_dir / "latest_report.md").write_text(report, encoding="utf-8")
        return report_path

    def run(self, force: bool = False, dry_run: bool = False) -> RunResult:
        now = datetime.now(self.config.tzinfo)

        if not force and not self.config.should_run_now(now):
            return RunResult(
                success=True,
                skipped=True,
                message=(
                    f"Current time is outside the configured push window. timezone={self.config.timezone}, "
                    f"local_time={now.strftime('%Y-%m-%d %H:%M')}, "
                    f"schedule=weekday {self.config.push_weekday} "
                    f"{self.config.push_hour:02d}:{self.config.push_minute:02d}, "
                    f"window={self.config.push_window_minutes} minutes."
                ),
                report="",
                report_path="",
            )

        candidates = self._collect_candidates(now)
        historical_ids = self.history.sent_ids()

        # Get top N candidates (excluding already sent), pass to LLM selector
        pool = self._top_by_score(candidates, historical_ids, self.config.candidate_pool_size)
        if len(pool) < self.config.project_count:
            # Not enough new repos — allow repeats
            pool = self._top_by_score(candidates, set(), self.config.candidate_pool_size)

        if self.selector:
            triples = self.selector.select(pool, count=self.config.project_count)
        else:
            # No LLM: just take top 3 by score with empty reasons
            triples = [(r, s, "") for r, s in pool[: self.config.project_count]]

        report = render_report(now, triples)
        report_path = self._write_report(report, now)

        if dry_run:
            return RunResult(
                success=True,
                skipped=False,
                message=(
                    f"dry-run completed. candidates={len(candidates)}, "
                    f"pool={len(pool)}, selected={len(triples)}, "
                    f"llm={'yes' if self.selector else 'no (ANTHROPIC_API_KEY not set)'}."
                ),
                report=report,
                report_path=str(report_path),
            )

        title = f"GitHub 项目周推 - {now.strftime('%Y-%m-%d')}"
        delivered = False
        channel_results: list[str] = []

        if self.pushplus_sender.is_available():
            try:
                self.pushplus_sender.send(report, title)
                delivered = True
                channel_results.append("pushplus:ok")
            except Exception as exc:
                channel_results.append(f"pushplus:error:{exc}")
        else:
            channel_results.append("pushplus:skipped")

        if self.email_sender.is_available():
            try:
                self.email_sender.send(report, title)
                delivered = True
                channel_results.append("email:ok")
            except Exception as exc:
                channel_results.append(f"email:error:{exc}")
        else:
            channel_results.append("email:skipped")

        if delivered:
            self.history.record_run(
                generated_at=now,
                repos=[repo for repo, _, _ in triples],
                report_path=report_path,
            )

        message = (
            f"Run completed. candidates={len(candidates)}, pool={len(pool)}, selected={len(triples)}. "
            f"channels={','.join(channel_results)}."
        )
        if not delivered:
            message += " No delivery channel succeeded."

        return RunResult(success=delivered, skipped=False, message=message, report=report, report_path=str(report_path))
