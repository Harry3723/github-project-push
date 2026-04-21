from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from github_project_push.config import Config  # noqa: E402
from github_project_push.service import GitHubProjectPushService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GitHub project weekly push service for ECE PhD students")
    parser.add_argument("--dry-run", action="store_true", help="Generate report without sending notifications")
    parser.add_argument("--force", action="store_true", help="Run even if today is not the scheduled push day")
    parser.add_argument("--print-report", action="store_true", help="Print the full markdown report to stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = Config.load(PROJECT_ROOT)
    service = GitHubProjectPushService(config)
    result = service.run(force=args.force, dry_run=args.dry_run)

    if result.skipped:
        print(result.message)
        return 0

    print(result.message)
    print(f"报告已保存到: {result.report_path}")

    if args.print_report or args.dry_run:
        print()
        print(result.report)

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
