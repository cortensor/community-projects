from __future__ import annotations

import argparse
from pathlib import Path

from .github_source import GitHubClient, load_json_file
from .llm import OpenAICompatibleModelClient
from .orchestrator import TriageAgent


def _write_report(report_json: str, output: str | None) -> None:
    if output:
        Path(output).write_text(report_json + "\n", encoding="utf-8")
    print(report_json)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GitHub issue and release triage agent")
    parser.add_argument("--session-db", default=".triage/triage.db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser("issue", help="triage one issue")
    issue.add_argument("repo")
    issue.add_argument("--number", type=int)
    issue.add_argument("--file")
    issue.add_argument("--out")
    issue.add_argument("--model")
    issue.add_argument("--base-url")

    release = subparsers.add_parser("release", help="validate one release")
    release.add_argument("repo")
    release.add_argument("--tag")
    release.add_argument("--file")
    release.add_argument("--out")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    Path(args.session_db).parent.mkdir(parents=True, exist_ok=True)
    if args.command == "issue":
        if not args.file and not args.number:
            raise SystemExit("issue requires a file or number")
        if args.file:
            payload = load_json_file(args.file)
        else:
            payload = GitHubClient().fetch_issue(args.repo, args.number)
        model = None
        if args.model:
            model = OpenAICompatibleModelClient(base_url=args.base_url, model=args.model)
        report = TriageAgent(session_db=args.session_db, model_client=model).triage_issue(
            args.repo, payload
        )
    else:
        if not args.file and not args.tag:
            raise SystemExit("release requires a file or tag")
        if args.file:
            payload = load_json_file(args.file)
        else:
            payload = GitHubClient().fetch_release(args.repo, args.tag)
        report = TriageAgent(session_db=args.session_db).triage_release(args.repo, payload)
    _write_report(report.model_dump_json(indent=2), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

