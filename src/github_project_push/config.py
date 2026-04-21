from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_csv(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Config:
    project_root: Path
    history_path: Path
    report_dir: Path
    pushplus_token: str | None
    pushplus_topic: str | None
    pushplus_api_url: str
    pushplus_max_bytes: int
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_use_starttls: bool
    smtp_use_ssl: bool
    email_from: str | None
    email_to: list[str]
    github_token: str | None
    anthropic_api_key: str | None
    llm_model: str
    candidate_pool_size: int
    push_frequency: str
    push_weekday: int
    timezone: str
    push_hour: int
    push_minute: int
    push_window_minutes: int
    project_count: int
    per_page: int

    @classmethod
    def load(cls, project_root: Path) -> "Config":
        _load_dotenv(project_root / ".env")
        return cls(
            project_root=project_root,
            history_path=project_root / "data" / "push_history.json",
            report_dir=project_root / "reports",
            pushplus_token=os.getenv("PUSHPLUS_TOKEN"),
            pushplus_topic=os.getenv("PUSHPLUS_TOPIC"),
            pushplus_api_url=os.getenv("PUSHPLUS_API_URL", "https://www.pushplus.plus/send"),
            pushplus_max_bytes=_get_int("PUSHPLUS_MAX_BYTES", 20000),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=_get_int("SMTP_PORT", 587),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_use_starttls=_get_bool("SMTP_USE_STARTTLS", True),
            smtp_use_ssl=_get_bool("SMTP_USE_SSL", False),
            email_from=os.getenv("EMAIL_FROM"),
            email_to=_get_csv("EMAIL_TO"),
            github_token=os.getenv("GITHUB_TOKEN"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            llm_model=os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001"),
            candidate_pool_size=_get_int("CANDIDATE_POOL_SIZE", 10),
            push_frequency=os.getenv("PUSH_FREQUENCY", "weekly").strip().lower(),
            push_weekday=_get_int("PUSH_WEEKDAY", 5),   # 5 = Saturday
            timezone=os.getenv("TIMEZONE", "America/Chicago"),
            push_hour=_get_int("PUSH_HOUR", 20),         # 8pm
            push_minute=_get_int("PUSH_MINUTE", 0),
            push_window_minutes=_get_int("PUSH_WINDOW_MINUTES", 30),
            project_count=_get_int("PROJECT_COUNT", 3),
            per_page=_get_int("GITHUB_PER_PAGE", 15),
        )

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def should_run_today(self, weekday: int) -> bool:
        if self.push_frequency == "daily":
            return True
        if self.push_frequency == "weekly":
            return weekday == self.push_weekday
        return True

    def should_run_now(self, now: datetime) -> bool:
        if not self.should_run_today(now.weekday()):
            return False
        scheduled_minutes = self.push_hour * 60 + self.push_minute
        current_minutes = now.hour * 60 + now.minute
        return scheduled_minutes <= current_minutes < scheduled_minutes + self.push_window_minutes
