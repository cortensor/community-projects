"""FixBrief command-line interface.

Exit codes mirror the OpenMinion SDK error taxonomy:
  0  success
  1  ProviderError (provider unreachable / auth / rate limit)
  2  AgentOutputValidationError (model output failed schema validation)
  3  TurnTimeoutError (turn deadline exceeded)
  4  usage / local input error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent import BriefError, run_followup, run_model_brief, write_receipt
from .config import PROVIDERS, active_provider_model, ensure_config
from .fallback import build_fallback_brief
from .models import Language, SourceRef
from .render import render_markdown
from .sources import fetch_url, list_samples, load_sample
from .store import get_brief, list_briefs, save_brief

EXIT_USAGE = 4


def _parse_sources(args: argparse.Namespace) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    for name in args.sample or []:
        sources.append(("sample", name))
    for url in args.url or []:
        sources.append(("url", url))
    return sources


def _load_source_texts(
    sources: list[tuple[str, str]],
) -> list[tuple[SourceRef, str]]:
    loaded: list[tuple[SourceRef, str]] = []
    for kind, locator in sources:
        if kind == "sample":
            text = load_sample(locator)
            title = Path(locator).stem.replace("-", " ").title()
            loaded.append(
                (SourceRef(title=title, locator=locator, kind="offline-sample"), text)
            )
        else:
            text = fetch_url(locator)
            loaded.append(
                (SourceRef(title=locator, locator=locator, kind="live-url"), text)
            )
    return loaded


def _emit(brief, fmt: str, out: str | None) -> None:
    if fmt == "json":
        payload = brief.model_dump_json(indent=2)
    else:
        payload = render_markdown(brief)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(payload, encoding="utf-8")
        print(f"wrote {out}")
    print(payload)


def cmd_setup(args: argparse.Namespace) -> int:
    path = ensure_config(args.provider, args.model)
    provider, model = active_provider_model()
    print(f"config: {path}")
    print(f"provider: {provider}")
    print(f"model: {model}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from openminion import __version__ as om_version

    provider, model = active_provider_model()
    print(f"fixbrief {__version__} · openminion {om_version}")
    print(f"provider: {provider} · model: {model}")
    print(f"samples: {', '.join(list_samples()) or '(none)'}")
    if provider == "ollama":
        import httpx

        try:
            resp = httpx.get("http://127.0.0.1:11434/api/version", timeout=5)
            print(f"ollama: reachable ({resp.json().get('version', 'unknown')})")
            tags = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5).json()
            names = [m.get("name") for m in tags.get("models", [])]
            print(f"ollama models: {', '.join(names) or '(none pulled)'}")
        except Exception as exc:  # noqa: BLE001
            print(f"ollama: NOT reachable ({exc}) — start `ollama serve` first")
    if provider == "echo":
        print("echo: demo provider (no model) — plumbing only, not a model run")
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    sources = _parse_sources(args)
    if not sources:
        print("error: pass at least one --sample or --url", file=sys.stderr)
        return EXIT_USAGE
    language = Language(args.lang)

    if args.offline:
        try:
            texts = _load_source_texts(sources)
        except Exception as exc:  # noqa: BLE001
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        brief = build_fallback_brief(args.device, args.symptom, texts, language)
        brief_id = save_brief(brief, session_id=args.session)
        print(f"[offline deterministic brief id={brief_id}]", file=sys.stderr)
        _emit(brief, args.format, args.out)
        return 0

    try:
        run = run_model_brief(
            device=args.device,
            symptom=args.symptom,
            sources=sources,
            language=language,
            provider=args.provider,
            model=args.model,
            session_id=args.session,
            auto_approve_writes=args.yes,
            timeout_seconds=args.timeout,
        )
    except BriefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if not args.fallback:
            return exc.exit_code
        print("falling back to deterministic brief (--fallback)", file=sys.stderr)
        try:
            texts = _load_source_texts(sources)
        except Exception as load_exc:  # noqa: BLE001
            print(f"error: {load_exc}", file=sys.stderr)
            return EXIT_USAGE
        brief = build_fallback_brief(args.device, args.symptom, texts, language)
        save_brief(brief, session_id=args.session)
        _emit(brief, args.format, args.out)
        return 0

    receipt_path = write_receipt(run.receipt)
    print(
        f"[model brief id={run.brief_id} session={run.receipt['session_id']} "
        f"run={run.receipt['run_id']} receipt={receipt_path}]",
        file=sys.stderr,
    )
    _emit(run.brief, args.format, args.out)
    return 0


def cmd_followup(args: argparse.Namespace) -> int:
    try:
        text, receipt = run_followup(
            session_id=args.session,
            message=args.message,
            provider=args.provider,
            model=args.model,
            timeout_seconds=args.timeout,
            auto_approve_writes=args.yes,
        )
    except BriefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    receipt_path = write_receipt(receipt)
    print(text)
    print(
        f"[session={receipt['session_id']} run={receipt['run_id']} "
        f"receipt={receipt_path}]",
        file=sys.stderr,
    )
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    rows = list_briefs(limit=args.limit)
    if not rows:
        print("(no briefs yet)")
        return 0
    for row in rows:
        print(
            f"#{row['id']} {row['created_at']} {row['device']} — "
            f"{row['symptom']} [{row['language']}] via {row['generated_by']}"
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    brief = get_brief(args.brief_id)
    if brief is None:
        print(f"error: brief #{args.brief_id} not found", file=sys.stderr)
        return EXIT_USAGE
    _emit(brief, args.format, None)
    return 0


def cmd_samples(_args: argparse.Namespace) -> int:
    for name in list_samples():
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fixbrief",
        description="Multilingual repair-brief agent on the OpenMinion SDK",
    )
    parser.add_argument("--version", action="version", version=f"fixbrief {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="Write project OpenMinion config")
    p_setup.add_argument("--provider", default="ollama", choices=sorted(PROVIDERS))
    p_setup.add_argument("--model", default=None)
    p_setup.set_defaults(func=cmd_setup)

    p_doctor = sub.add_parser("doctor", help="Check SDK, provider, and samples")
    p_doctor.set_defaults(func=cmd_doctor)

    p_brief = sub.add_parser("brief", help="Generate one repair brief")
    p_brief.add_argument("--device", required=True)
    p_brief.add_argument("--symptom", required=True)
    p_brief.add_argument("--sample", action="append", default=[])
    p_brief.add_argument("--url", action="append", default=[])
    p_brief.add_argument("--lang", default="en", choices=[l.value for l in Language])
    p_brief.add_argument("--provider", default="ollama", choices=sorted(PROVIDERS))
    p_brief.add_argument("--model", default=None)
    p_brief.add_argument("--session", default="fixbrief-session")
    p_brief.add_argument("--offline", action="store_true", help="Deterministic brief, no model")
    p_brief.add_argument("--fallback", action="store_true", help="On model failure, emit deterministic brief")
    p_brief.add_argument("--yes", action="store_true", help="Approve the save_brief_markdown write tool")
    p_brief.add_argument("--timeout", type=float, default=2400.0)
    p_brief.add_argument("--format", default="md", choices=["md", "json"])
    p_brief.add_argument("--out", default=None)
    p_brief.set_defaults(func=cmd_brief)

    p_follow = sub.add_parser("followup", help="Continue an existing session")
    p_follow.add_argument("--session", default="fixbrief-session")
    p_follow.add_argument("--message", required=True)
    p_follow.add_argument("--provider", default="ollama", choices=sorted(PROVIDERS))
    p_follow.add_argument("--model", default=None)
    p_follow.add_argument("--timeout", type=float, default=2400.0)
    p_follow.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve the write tool (save_brief_markdown)",
    )
    p_follow.set_defaults(func=cmd_followup)

    p_history = sub.add_parser("history", help="List stored briefs")
    p_history.add_argument("--limit", type=int, default=20)
    p_history.set_defaults(func=cmd_history)

    p_show = sub.add_parser("show", help="Show one stored brief")
    p_show.add_argument("brief_id", type=int)
    p_show.add_argument("--format", default="md", choices=["md", "json"])
    p_show.set_defaults(func=cmd_show)

    p_samples = sub.add_parser("samples", help="List bundled offline samples")
    p_samples.set_defaults(func=cmd_samples)

    return parser


def main(argv: list[str] | None = None) -> int:
    from .config import normalize_no_proxy

    normalize_no_proxy()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
