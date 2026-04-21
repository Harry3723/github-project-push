from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from github_project_push.models import RepoCandidate


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _default(self) -> dict:
        return {"schema_version": 1, "sent_ids": [], "runs": []}

    def load(self) -> dict:
        if not self.path.exists():
            return self._default()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def sent_ids(self) -> set[str]:
        return set(self.load().get("sent_ids", []))

    def record_run(
        self,
        generated_at: datetime,
        repos: list[RepoCandidate],
        report_path: Path,
    ) -> None:
        payload = self.load()
        sent_ids = set(payload.get("sent_ids", []))
        sent_ids.update(repo.unique_id for repo in repos)
        payload["sent_ids"] = sorted(sent_ids)
        payload.setdefault("runs", []).append(
            {
                "generated_at": generated_at.isoformat(),
                "report_path": str(report_path),
                "repos": [repo.full_name for repo in repos],
            }
        )
        payload["runs"] = payload["runs"][-200:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
