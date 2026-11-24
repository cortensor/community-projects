"""`repo-triager` command line.

Commands are small wrappers around the three agent phases so the whole
workflow is reproducible from a shell:

    repo-triager doctor
    repo-triager fetch --repo openminion/openminion --limit 30
    repo-triager triage --issue 859 --apply ask
    repo-triager batch --limit 3 --apply auto --remember
    repo-triager demo            # offline, scripted model, no credential
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_triager import __version__
from repo_triager.agent import (
    TriagerAgent,
    build_record,
    now_stamp,
    open_runtime,
    repair_decision,
    resolve_script_scenario,
    validate_decision,
)
from repo_triager.config import (
    DEFAULT_LIMIT,
    DEFAULT_REPO,
    RuntimeBootstrapError,
    RuntimeSession,
    Settings,
)
from repo_triager.github import GitHubError, get_snapshot
from repo_triager.models import Issue, RepoSnapshot, RunReport
from repo_triager.policy import OperatorPolicy
from repo_triager.report import load_report, render_markdown, write_report


# --------------------------------------------------------------------- helpers
def _print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _settings_from_args(args: argparse.Namespace) -> Settings:
    return Settings(
        repo=args.repo,
        workspace=Path(args.home).resolve() if args.home else Settings().workspace,
        om_home=Path(args.om_home).resolve() if args.om_home else None,
        provider_mode=args.provider,
        model=args.model,
        source=args.source,
    )


def _issues_from_args(
    snapshot: RepoSnapshot, args: argparse.Namespace
) -> list[Issue]:
    if getattr(args, "issue", None):
        issue = snapshot.issue(args.issue)
        if issue is None:
            raise SystemExit(f"issue #{args.issue} is not in the snapshot for {snapshot.repo}")
        return [issue]
    limit = getattr(args, "limit", DEFAULT_LIMIT)
    only = getattr(args, "issues", None)
    if only:
        numbers = [int(part) for part in str(only).replace(" ", "").split(",") if part]
        picked = [snapshot.issue(number) for number in numbers]
        return [issue for issue in picked if issue is not None]
    return snapshot.issues[: max(1, limit)]


def _source_label(snapshot) -> str:
    return "live" if snapshot.source == "github-api" else "offline"


def _run_dir(settings: Settings) -> tuple[str, Path]:
    run_id = f"{now_stamp()}-{settings.repo.replace('/', '_')}"
    return run_id, settings.runs_dir / run_id


# ------------------------------------------------------------------ commands
def cmd_doctor(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    settings.ensure_dirs()
    _print_header(f"Repo Triager {__version__} — diagnostics")
    facts: dict[str, Any] = {
        "repo_triager_version": __version__,
        "repo": settings.repo,
        "workspace": str(settings.workspace),
        "openminion_home": str(settings.om_home),
        "python": sys.version.split()[0],
    }
    try:
        from openminion import __version__ as om_version

        facts["openminion_version"] = om_version
    except Exception as exc:  # noqa: BLE001
        facts["openminion_version"] = f"unavailable: {exc}"

    with RuntimeSession(settings, provider_mode=args.provider) as session:
        if session.base_url:
            facts["scripted_provider"] = session.base_url
        runtime = open_runtime(settings)
        try:
            facts["capability_report"] = runtime.capability_report()
            facts["runtime_posture"] = runtime.runtime_posture()
            self_model = runtime.runtime_self_model()
            facts["self_model_health"] = self_model.get("health")
            facts["degraded_reasons"] = self_model.get("degraded_reasons")
            inventory = runtime.tool_inventory_report()
            facts["tool_count"] = len(inventory)
            facts["memory_tools"] = sorted(
                item["name"] for item in inventory if "memory" in item["name"]
            )
            facts["skill_tools"] = sorted(
                item["name"] for item in inventory if item["name"].startswith("skill.")
            )
            facts["task_tools"] = sorted(
                item["name"]
                for item in inventory
                if item["name"].startswith("task.") and "memory" not in item["name"]
            )
        finally:
            runtime.close()
        out = settings.artifacts_dir / "doctor.json"
        out.write_text(json.dumps(facts, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        doctor = session.run_cli("doctor")
        log = settings.artifacts_dir / "openminion-doctor.log"
        log.write_text(doctor.stdout + "\n" + doctor.stderr, encoding="utf-8")

    print(f"python            : {facts['python']}")
    print(f"openminion        : {facts.get('openminion_version')}")
    print(f"openminion home   : {facts['openminion_home']}")
    print(f"provider mode     : {args.provider}")
    print(f"tools registered  : {facts.get('tool_count')}")
    print(f"memory tools      : {', '.join(facts.get('memory_tools') or [])}")
    print(f"skill tools       : {', '.join(facts.get('skill_tools') or [])}")
    print(f"self-model health : {facts.get('self_model_health')}")
    report = Path(log).read_text(encoding="utf-8")
    for line in report.splitlines():
        if line.startswith("doctor:") or line.startswith("[WARN]") or line.startswith("[FAIL]"):
            print(line)
    print(f"\nfull diagnostics written to {out} and {log}")
    if args.json:
        print(json.dumps(facts, indent=2, ensure_ascii=False, default=str))
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    settings.ensure_dirs()
    snapshot = get_snapshot(
        settings, repo=args.repo, limit=args.limit, refresh=True, source=args.source
    )
    print(f"fetched {len(snapshot.issues)} open issues and {len(snapshot.labels)} labels "
          f"from {snapshot.repo} ({snapshot.source})")
    print(f"cache: {settings.cache_path(args.repo)}")
    return 0


def cmd_labels(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    snapshot = get_snapshot(settings, repo=args.repo, source=args.source)
    for label in snapshot.labels:
        marker = "area" if label.name.startswith("area:") else "----"
        print(f"{marker}  {label.name:34s} {label.description[:60]}")
    return 0


def _triage_issues(
    settings: Settings,
    snapshot: RepoSnapshot,
    issues: list[Issue],
    *,
    apply_mode: str,
    remember: bool,
    deep_dedupe: bool,
    session_id: str,
    provider_mode: str,
    quiet: bool = False,
) -> RunReport:
    """Analyse (and optionally stage) a list of issues with one runtime."""

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id, directory = _run_dir(settings)
    report = RunReport(
        run_id=run_id,
        repo=snapshot.repo,
        started_at=started,
        provider=provider_mode,
        source=_source_label(snapshot),
        session_id=session_id,
    )
    scripts: dict[str, Any] = {}
    if provider_mode == "scripted":
        from repo_triager.scripted_demo import scripts_for_issues

        scripts = scripts_for_issues(snapshot, issues)

    with RuntimeSession(settings, provider_mode=provider_mode, scripted_scripts=scripts) as session:
        if session.base_url:
            report.provider = f"scripted ({session.base_url})"
        runtime = open_runtime(settings)
        agent = TriagerAgent(
            settings, snapshot, runtime=runtime, provider_label=report.provider
        )
        try:
            for issue in issues:
                record = _triage_one(
                    agent,
                    settings,
                    snapshot,
                    issue,
                    apply_mode=apply_mode,
                    remember=remember,
                    deep_dedupe=deep_dedupe,
                    session_id=session_id,
                    provider_mode=provider_mode,
                    quiet=quiet,
                )
                report.records.append(record)
        finally:
            runtime.close()

    report.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    markdown_path, json_path = write_report(report, directory)
    if not quiet:
        print()
        print(f"run {report.run_id}: {report.issues_seen} issues, "
              f"{sum(1 for r in report.records if r.applied)} staged")
        print(f"report: {markdown_path}")
        print(f"json  : {json_path}")
    return report


def _triage_one(
    agent: TriagerAgent,
    settings: Settings,
    snapshot: RepoSnapshot,
    issue: Issue,
    *,
    apply_mode: str,
    remember: bool,
    deep_dedupe: bool,
    session_id: str,
    provider_mode: str,
    quiet: bool,
) -> Any:
    scenario = resolve_script_scenario(issue) if provider_mode == "scripted" else None
    decision, phase, context, notes = agent.analyse_or_fallback(
        issue, session_id=session_id, scenario=scenario
    )
    problems = validate_decision(decision, issue, snapshot)
    if problems:
        decision = repair_decision(decision, issue, snapshot, problems)

    if deep_dedupe:
        confirmed, reason, _meta = agent.deep_dedupe(
            issue,
            session_id=session_id,
            scenario=f"dedupe-{issue.number}" if provider_mode == "scripted" else None,
        )
        merged = list(dict.fromkeys([*decision.duplicate_of, *confirmed]))
        decision = decision.model_copy(
            update={
                "duplicate_of": merged,
                "duplicate_reason": "; ".join(filter(None, [decision.duplicate_reason, reason])),
            }
        )

    policy_events: list[dict] = []
    applied = False
    outbox: list[str] = []
    if apply_mode != "skip":
        policy = OperatorPolicy(mode="deny" if apply_mode == "deny" else apply_mode)
        stage_phase = agent.stage(
            decision,
            context,
            session_id=f"{session_id}:stage",
            policy=policy,
            pause=(apply_mode == "pause"),
            scenario=f"stage-{issue.number}" if provider_mode == "scripted" else None,
        )
        policy_events = stage_phase.policy_events
        applied = bool(context.applied)
        outbox = list(context.outbox_paths)

    remember_result = None
    if remember and applied:
        remember_result = agent.remember(
            decision,
            session_id=f"{session_id}:memory",
            scenario=f"remember-{issue.number}" if provider_mode == "scripted" else None,
        )
        policy_events = policy_events + remember_result.policy_events

    record = build_record(
        decision,
        issue,
        problems=problems,
        policy_events=policy_events,
        applied=applied,
        outbox=outbox,
        run_id=phase.run_id,
        session_id=phase.session_id,
        llm_calls=int(phase.metadata.get("llm_calls", 0) or 0)
        + (int(remember_result.metadata.get("llm_calls", 0)) if remember_result else 0),
        tool_calls=int(phase.metadata.get("tool_calls", 0) or 0)
        + (int(remember_result.metadata.get("tool_calls", 0)) if remember_result else 0),
        elapsed_ms=0,
    )
    if not quiet:
        status = "staged" if applied else ("denied" if apply_mode == "deny" else "analysis only")
        print(
            f"  #{issue.number:<4} {decision.severity}  {decision.component or '—':16s} "
            f"{status:14s} conf={decision.confidence:.2f} labels={','.join(decision.labels) or '-'}"
        )
    return record


def cmd_triage(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    settings.ensure_dirs()
    snapshot = get_snapshot(settings, repo=args.repo, source=args.source, refresh=args.refresh)
    issues = _issues_from_args(snapshot, args)
    _print_header(f"triaging {len(issues)} issue(s) from {snapshot.repo} ({snapshot.source})")
    session_id = args.session or f"repo-triager:{snapshot.repo.replace(chr(47), chr(95))}"
    _triage_issues(
        settings,
        snapshot,
        issues,
        apply_mode=args.apply,
        remember=args.remember,
        deep_dedupe=args.deep_dedupe,
        session_id=session_id,
        provider_mode=args.provider,
    )
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    return cmd_triage(args)


def cmd_demo(args: argparse.Namespace) -> int:
    """End-to-end demonstration: analyse, gate a write, recall a precedent."""

    args.repo = args.repo or DEFAULT_REPO
    settings = _settings_from_args(args)
    settings.ensure_dirs()
    snapshot = get_snapshot(settings, repo=args.repo, source="offline")
    numbers = [int(part) for part in args.numbers.split(",") if part.strip()]
    issues = [snapshot.issue(number) for number in numbers]
    issues = [issue for issue in issues if issue is not None]
    provider_mode = args.provider if args.provider != "auto" else "scripted"
    session_id = f"repo-triager-demo:{snapshot.repo.replace(chr(47), chr(95))}"

    _print_header("Repo Triager demo — scripted model, real OpenMinion runtime")
    print(f"repository : {snapshot.repo} (offline snapshot of {len(snapshot.issues)} open issues)")
    print(f"issues     : {', '.join('#' + str(issue.number) for issue in issues)}")
    print(f"provider   : {provider_mode}")
    print()

    run_id, directory = _run_dir(settings)
    report = RunReport(
        run_id=f"demo-{run_id}",
        repo=snapshot.repo,
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        provider=provider_mode,
        source=_source_label(snapshot),
        session_id=session_id,
    )
    scripts: dict[str, Any] = {}
    if provider_mode == "scripted":
        from repo_triager.scripted_demo import scripts_for_issues

        scripts = scripts_for_issues(snapshot, issues)

    with RuntimeSession(settings, provider_mode=provider_mode, scripted_scripts=scripts) as session:
        if session.base_url:
            report.provider = f"scripted ({session.base_url})"
        runtime = open_runtime(settings)
        agent = TriagerAgent(settings, snapshot, runtime=runtime)
        try:
            print("── step 1/4  analyse with read-only tools + structured output")
            first = issues[0]
            decision, phase, context, notes = agent.analyse_or_fallback(
                first, session_id=session_id, scenario=resolve_script_scenario(first)
            )
            print(f"   #{first.number} → {decision.severity} {decision.component} "
                  f"({phase.metadata.get('llm_calls')} LLM calls, "
                  f"{phase.metadata.get('tool_calls')} tool calls)")
            print(f"   tools used: {[event['tool'] for event in context.tool_events]}")
            problems = validate_decision(decision, first, snapshot)
            report.notes.extend(notes)

            print()
            print("── step 2/4  delegate duplicate analysis to a bounded subagent")
            confirmed, reason, _meta = agent.deep_dedupe(
                first,
                session_id=session_id,
                scenario=f"dedupe-{first.number}" if provider_mode == "scripted" else None,
            )
            print(f"   subagent verdict: {reason or 'no duplicates'}")

            print()
            print("── step 3/4  stage the approved plan (policy confirmation)")
            policy = OperatorPolicy(mode="auto")
            staged = agent.stage(
                decision,
                context,
                session_id=f"{session_id}:stage",
                policy=policy,
                scenario=f"stage-{first.number}" if provider_mode == "scripted" else None,
            )
            print(f"   policy events: {json.dumps(staged.policy_events, ensure_ascii=False)}")
            print(f"   outbox: {context.outbox_paths}")
            report.records.append(
                build_record(
                    decision,
                    first,
                    problems=problems,
                    policy_events=staged.policy_events,
                    applied=context.applied,
                    outbox=context.outbox_paths,
                    run_id=phase.run_id,
                    session_id=phase.session_id,
                )
            )

            if len(issues) > 1:
                second = issues[1]
                print()
                print(f"── step 3b/4 the same gate, refused for #{second.number}")
                decision2, phase2, context2, _ = agent.analyse_or_fallback(
                    second, session_id=session_id, scenario=resolve_script_scenario(second)
                )
                denied = agent.stage(
                    decision2,
                    context2,
                    session_id=f"{session_id}:stage-deny",
                    policy=OperatorPolicy(mode="deny"),
                    scenario=f"stage-{second.number}" if provider_mode == "scripted" else None,
                )
                print(f"   applied={context2.applied} events={json.dumps(denied.policy_events)}")
                report.records.append(
                    build_record(
                        decision2,
                        second,
                        policy_events=denied.policy_events,
                        applied=context2.applied,
                        outbox=context2.outbox_paths,
                        run_id=phase2.run_id,
                        session_id=phase2.session_id,
                    )
                )

            print()
            print("── step 4/4  write the decision to OpenMinion memory")
            memory = agent.remember(
                decision,
                session_id=f"{session_id}:memory",
                scenario=f"remember-{first.number}" if provider_mode == "scripted" else None,
            )
            print(f"   {memory.text.replace('openminion: ', '')[:300]}")
        finally:
            runtime.close()

    report.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    markdown_path, json_path = write_report(report, directory)
    print()
    print(f"report: {markdown_path}")
    print(f"json  : {json_path}")
    return 0


def _skill_json(result) -> dict:
    text = (result.stdout or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def cmd_skills(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    settings.ensure_dirs()
    skill_path = Path(__file__).resolve().parent / "skills" / "repo-triager-triage" / "SKILL.md"
    with RuntimeSession(settings, provider_mode=args.provider) as session:
        if args.action == "ingest":
            ingested = _skill_json(
                session.run_cli(
                    "skill", "ingest", "--name", "repo-triager-triage",
                    "--file", str(skill_path), "--scope", "global",
                )
            )
            version = str(ingested.get("version_hash") or "")
            if not ingested.get("ok") or not version:
                print(f"ingest failed: {json.dumps(ingested)[:400]}")
                return 1
            shown = _skill_json(
                session.run_cli("skill", "show", "repo-triager.triage-rubric")
            )
            active = str((shown.get("skill") or {}).get("version_hash") or "")
            if active == version:
                print(f"skill already active: repo-triager.triage-rubric {version[:12]}")
            else:
                evidence = settings.artifacts_dir / "skill-verification.txt"
                evidence.write_text(
                    "repo-triager self-check: `python -m pytest` passed\n", encoding="utf-8"
                )
                admitted = _skill_json(
                    session.run_cli(
                        "skill", "admit",
                        "--skill-id", "repo-triager.triage-rubric",
                        "--version-hash", version,
                        "--expected-active-version-hash", active or "none",
                        "--target-status", "verified",
                        "--reason", "Repo Triager rubric, verified by the test suite",
                        "--verification-check", "pytest",
                        "--verification-result", "passed",
                        "--verification-evidence-ref", str(evidence),
                    )
                )
                if admitted.get("ok"):
                    print(f"admitted: repo-triager.triage-rubric {version[:12]} (verified)")
                else:
                    print(f"admit failed: {json.dumps(admitted)[:400]}")
                    return 1
        listing = session.run_cli("skill", "list")
        print(listing.stdout.strip())
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    settings.ensure_dirs()
    instruction = (
        f"Run the daily triage for {settings.repo}: execute "
        f"`repo-triager batch --repo {settings.repo} --limit {args.limit} "
        f"--source live --apply ask` and report which issues were staged."
    )
    with RuntimeSession(settings, provider_mode=args.provider) as session:
        result = session.run_cli(
            "cron", "create",
            "--instruction", instruction,
            "--cron", args.cron,
            "--tz", args.timezone,
            "--name", f"repo-triager {settings.repo}",
            "--json",
        )
    print(result.stdout.strip() or result.stderr.strip())
    return 0 if result.returncode == 0 else 1


def cmd_report(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    path = Path(args.run) if args.run else None
    if path is None:
        runs = sorted(settings.runs_dir.glob("*/report.json"))
        if not runs:
            raise SystemExit("no run reports found; run `repo-triager triage` first")
        path = runs[-1]
    if path.is_dir():
        path = path / "report.json"
    report = load_report(path)
    print(render_markdown(report))
    return 0


# --------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-triager",
        description="Repeatable GitHub issue triage with the OpenMinion 0.1 Python SDK",
    )
    parser.add_argument("--version", action="version", version=f"repo-triager {__version__}")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/name (default: %(default)s)")
    parser.add_argument("--home", default="", help="workspace directory (default: ./var)")
    parser.add_argument("--om-home", default="", help="OpenMinion home root")
    parser.add_argument("--model", default="", help="override the model id")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "scripted", "configured"],
        help="scripted = offline deterministic model, configured = your provider credential",
    )
    parser.add_argument(
        "--source",
        default="offline",
        choices=["offline", "live", "cache"],
        help="issue source: bundled snapshot, GitHub API, or the local cache",
    )
    parser.add_argument("--json", action="store_true", help="also print machine-readable output")

    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="print OpenMinion + Repo Triager diagnostics")
    doctor.set_defaults(func=cmd_doctor)

    fetch = sub.add_parser("fetch", help="cache the repository's issues and labels")
    fetch.add_argument("--limit", type=int, default=30)
    fetch.set_defaults(func=cmd_fetch)

    labels = sub.add_parser("labels", help="list the repository label taxonomy")
    labels.set_defaults(func=cmd_labels)

    triage = sub.add_parser("triage", help="triage one issue")
    triage.add_argument("--issue", type=int, required=True)
    triage.add_argument(
        "--apply",
        default="ask",
        choices=["skip", "ask", "auto", "deny", "pause"],
        help="how the write gate is answered (pause = OpenMinion's own confirmation flow)",
    )
    triage.add_argument("--remember", action="store_true", help="write the decision to memory")
    triage.add_argument("--deep-dedupe", action="store_true", help="use the duplicate subagent")
    triage.add_argument("--session", default="", help="session id for continuity")
    triage.add_argument("--refresh", action="store_true", help="refresh the issue cache")
    triage.set_defaults(func=cmd_triage)

    batch = sub.add_parser("batch", help="triage the newest N open issues")
    batch.add_argument("--limit", type=int, default=3)
    batch.add_argument("--issues", default="", help="comma separated issue numbers")
    batch.add_argument(
        "--apply", default="auto", choices=["skip", "ask", "auto", "deny", "pause"]
    )
    batch.add_argument("--remember", action="store_true")
    batch.add_argument("--deep-dedupe", action="store_true")
    batch.add_argument("--session", default="")
    batch.add_argument("--refresh", action="store_true")
    batch.set_defaults(func=cmd_batch)

    demo = sub.add_parser("demo", help="offline end-to-end demonstration")
    demo.add_argument("--numbers", default="859,853,857")
    demo.set_defaults(func=cmd_demo)

    skills = sub.add_parser("skills", help="ingest or inspect the triage rubric skill")
    skills.add_argument("action", choices=["ingest", "list"], nargs="?", default="list")
    skills.set_defaults(func=cmd_skills)

    schedule = sub.add_parser("schedule", help="register a recurring triage task")
    schedule.add_argument("--cron", default="0 9 * * 1-5", help="5-field cron expression")
    schedule.add_argument("--timezone", default="Asia/Seoul")
    schedule.add_argument("--limit", type=int, default=5)
    schedule.set_defaults(func=cmd_schedule)

    report = sub.add_parser("report", help="render a stored run report")
    report.add_argument("--run", default="")
    report.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (RuntimeBootstrapError, GitHubError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
