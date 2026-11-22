"""The Builder Brief schema plus a deterministic (no model) brief used by demo mode and as a fallback."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from . import diff

_FENCE_BLOCK = re.compile(r"```(?:json|JSON|javascript)?\s*\n?(.*?)\n?```", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_SMART_QUOTES = str.maketrans({
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
})


class BriefItem(BaseModel):
    title: str
    url: str | None = None
    why_it_matters: str
    risk: str = Field(description="none, low, medium or high")


class BuilderBrief(BaseModel):
    repo: str
    headline: str
    releases: list[BriefItem] = []
    issues_to_watch: list[BriefItem] = []
    actions: list[str] = Field(default_factory=list, description="Concrete next steps for a builder on this repo")


def offline_brief(repo: str, releases: list[dict], issues: list[dict]) -> BuilderBrief:
    rel_items = []
    for r in releases:
        flags = diff.risk_flags((r.get("name") or "") + " " + (r.get("body") or ""))
        rel_items.append(BriefItem(
            title=f"{r.get('tag')}: {r.get('name')}", url=r.get("url"),
            why_it_matters=("Mentions " + ", ".join(flags)) if flags else "New release; read notes before upgrading.",
            risk="high" if {"breaking", "security"} & set(flags) else ("medium" if flags else "low"),
        ))
    watch = []
    for i in issues:
        if not diff.is_bug(i) and not diff.risk_flags(i.get("title", "")):
            continue
        watch.append(BriefItem(
            title=f"#{i['number']} {i['title']} ({i['kind']}, {i['state']})", url=i.get("url"),
            why_it_matters="Bug or risky change that could affect your agent.",
            risk="medium" if i.get("state") == "open" else "low",
        ))
    actions = []
    if any(x.risk == "high" for x in rel_items):
        actions.append("Read the high risk release notes and pin your current version before upgrading.")
    if rel_items:
        actions.append("Upgrade in a branch and rerun `openminion doctor --check-turn`.")
    if watch:
        actions.append("Subscribe to the open bug issues listed above.")
    headline = f"{len(rel_items)} new release(s), {len(watch)} issue(s) worth watching in {repo}."
    return BuilderBrief(repo=repo, headline=headline, releases=rel_items, issues_to_watch=watch[:8], actions=actions)


def to_markdown(b: BuilderBrief, label: str = "") -> str:
    out = [f"# Builder Brief: {b.repo}", ""]
    if label:
        out += [f"> {label}", ""]
    out += [f"**{b.headline}**", "", "## Releases"]
    out += [f"- [{x.risk.upper()}] [{x.title}]({x.url}): {x.why_it_matters}" for x in b.releases] or ["- None new"]
    out += ["", "## Issues to watch"]
    out += [f"- [{x.risk.upper()}] [{x.title}]({x.url}): {x.why_it_matters}" for x in b.issues_to_watch] or ["- None"]
    out += ["", "## Actions"] + ([f"- {a}" for a in b.actions] or ["- Nothing to do"])
    return "\n".join(out) + "\n"


class BriefParseError(ValueError):
    """Raised when model text cannot be repaired into a BuilderBrief."""


def _candidate_blobs(text: str) -> list[str]:
    """Collect possible JSON object strings from raw model text."""
    blobs: list[str] = []
    raw = (text or "").strip()
    if not raw:
        return blobs

    def add(s: str) -> None:
        s = s.strip()
        if s and s not in blobs:
            blobs.append(s)

    add(raw)
    for match in _FENCE_BLOCK.finditer(raw):
        add(match.group(1))

    # First balanced / decodable object, and a last-brace slice for repair.
    decoder = json.JSONDecoder()
    for start, character in enumerate(raw):
        if character != "{":
            continue
        try:
            value, end = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            close = raw.rfind("}")
            if close > start:
                add(raw[start:close + 1])
            continue
        if isinstance(value, dict):
            add(raw[start:start + end])
            break
    return blobs


def repair_json_text(text: str) -> str | None:
    """Return canonical JSON text for a dict, after light repairs, or None."""
    if not text or not text.strip():
        return None
    variants = [text.strip()]
    translated = text.strip().translate(_SMART_QUOTES)
    if translated not in variants:
        variants.append(translated)
    more: list[str] = []
    for variant in variants:
        trimmed = _TRAILING_COMMA.sub(r"\1", variant)
        if trimmed not in variants and trimmed not in more:
            more.append(trimmed)
    variants.extend(more)
    for variant in variants:
        try:
            value = json.loads(variant)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return json.dumps(value)
    return None


def extract_json_object(text: str) -> str | None:
    """Extract and repair the first JSON object in Markdown, fences, or prose."""
    for blob in _candidate_blobs(text):
        repaired = repair_json_text(blob)
        if repaired:
            return repaired
    return None


def _first_str(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_item(item: Any, kind: str) -> dict:
    if not isinstance(item, dict):
        return {"title": str(item), "why_it_matters": "", "risk": "none"}
    item = dict(item)
    if kind == "release" and not _first_str(item, "title"):
        item["title"] = _first_str(item, "version", "tag", "name")
    if kind != "release":
        ident = _first_str(item, "id", "number")
        title = _first_str(item, "title", "name", "summary")
        if ident and ident not in title:
            item["title"] = f"{ident} {title}".strip()
        elif not title:
            item["title"] = ident
    if not _first_str(item, "why_it_matters"):
        item["why_it_matters"] = _first_str(item, "summary", "description", "details", "action", "why")
    if not _first_str(item, "risk"):
        item["risk"] = "none"
    if "url" not in item or item["url"] == "":
        item["url"] = item.get("html_url") or item.get("link") or None
    return item


def _normalize_brief_dict(obj: dict[str, Any]) -> dict[str, Any]:
    data = dict(obj)
    if "issues_to_watch" not in data:
        for alt in ("issues_prs", "issues", "prs", "issues_or_prs", "watch"):
            if alt in data:
                data["issues_to_watch"] = data.pop(alt)
                break
    data["releases"] = [_normalize_item(x, "release") for x in (data.get("releases") or [])]
    data["issues_to_watch"] = [_normalize_item(x, "issue") for x in (data.get("issues_to_watch") or [])]
    actions = data.get("actions") or []
    if isinstance(actions, str):
        data["actions"] = [actions]
    elif isinstance(actions, list):
        norm_actions = []
        for action in actions:
            if isinstance(action, dict):
                text = _first_str(action, "action", "text", "title", "step")
                if text:
                    norm_actions.append(text)
            else:
                norm_actions.append(str(action))
        data["actions"] = norm_actions
    return data



def _unwrap_payload(text: str) -> Any:
    """Return the first JSON value from raw model text (object or list)."""
    raw = (text or "").strip()
    for match in _FENCE_BLOCK.finditer(raw):
        blob = match.group(1).strip()
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for start, ch in enumerate(raw):
        if ch not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            continue
        return value
    return None


def brief_from_snapshot(repo: str, snapshot: dict[str, Any]) -> BuilderBrief | None:
    """Build a rule-based brief from a radar_snapshot cache. Used only as a last-resort fallback."""
    releases = snapshot.get("releases") if isinstance(snapshot, dict) else None
    issues = snapshot.get("issues") if isinstance(snapshot, dict) else None
    if not isinstance(releases, list) and not isinstance(issues, list):
        return None
    return offline_brief(repo or "unknown", releases or [], issues or [])


_WRAPPER_KEYS = (
    "summary", "radar_snapshot", "snapshot", "data", "result", "brief",
    "output", "builder_brief", "payload",
)


def _why_from_body(body: str, limit: int = 220) -> str:
    """Take a short, useful line from a release or issue body the model included."""
    text = (body or "").strip()
    if not text:
        return ""
    skip = re.compile(
        r"^(highlights|full changelog|this release also|related report|"
        r"problem and resulting behavior|summary|pypi)\b",
        re.I,
    )
    lines: list[str] = []
    for line in text.splitlines():
        s = line.strip().lstrip("-*").strip()
        s = re.sub(r"^(highlights|summary)\s*:\s*", "", s, flags=re.I).strip()
        if not s or skip.match(s) or (s.startswith("http") and " " not in s):
            continue
        lines.append(s)
    chunk = " ".join(lines) or re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", chunk)
    out = parts[0].strip()
    if len(out) < 80 and len(parts) > 1:
        out = (out + " " + parts[1]).strip()
    out = re.sub(r"\s+", " ", out).strip()
    if len(out) > limit:
        cut = out[: limit - 1].rsplit(" ", 1)[0]
        out = (cut or out[: limit - 1]) + "..."
    return out


def _risk_from_text(*parts: str, default: str = "low") -> str:
    flags = set()
    for part in parts:
        flags.update(diff.risk_flags(part or ""))
    if flags & {"breaking", "security"} or "deprecat" in flags:
        return "high"
    if flags:
        return "medium"
    return default


def _release_from_model_item(item: Any) -> dict:
    if not isinstance(item, dict):
        return {"title": str(item), "why_it_matters": str(item), "risk": "low", "url": None}
    item = dict(item)
    tag = _first_str(item, "tag", "version")
    name = _first_str(item, "name", "title")
    title = _first_str(item, "title")
    if not title:
        title = f"{tag}: {name}".strip(": ") if (tag or name) else "release"
    elif tag and tag not in title and not title.lower().startswith("v"):
        title = f"{tag}: {title}"
    body = _first_str(item, "body", "notes")
    why = _first_str(item, "why_it_matters", "summary", "description", "details", "why") or _why_from_body(body)
    if not why:
        why = "New release; read notes before upgrading."
    risk = (_first_str(item, "risk") or "").lower() or _risk_from_text(title, name, body, default="low")
    if risk not in {"none", "low", "medium", "high"}:
        risk = "low"
    url = item.get("url") or item.get("html_url") or item.get("link") or None
    return {"title": title, "url": url, "why_it_matters": why, "risk": risk}


def _issue_from_model_item(item: Any) -> dict:
    if not isinstance(item, dict):
        return {"title": str(item), "why_it_matters": str(item), "risk": "low", "url": None}
    item = dict(item)
    ident = _first_str(item, "number", "id")
    if ident and not ident.startswith("#") and ident.lstrip("#").isdigit():
        ident = ident if ident.startswith("#") else f"#{ident}"
    title_core = _first_str(item, "title", "name", "summary")
    title = title_core
    if ident and ident.lstrip("#") not in title_core.replace("#", ""):
        title = f"{ident} {title_core}".strip()
    elif not title:
        title = ident or "issue"
    kind = _first_str(item, "kind", "type")
    state = _first_str(item, "state")
    extra = ", ".join(x for x in (kind, state) if x)
    if extra and extra not in title:
        title = f"{title} ({extra})"
    body = _first_str(item, "body", "notes")
    labels = item.get("labels") or []
    label_text = " ".join(labels) if isinstance(labels, list) else str(labels)
    why = _first_str(item, "why_it_matters", "summary", "description", "details", "action", "why") or _why_from_body(body)
    if not why:
        why = "Bug or risky change that could affect your agent." if (
            diff.is_bug(item) or diff.risk_flags(title_core + " " + label_text)
        ) else "Open change a builder should watch."
    risk = (_first_str(item, "risk") or "").lower() or _risk_from_text(
        title, body, label_text, default="medium" if (state == "open" or diff.is_bug(item)) else "low"
    )
    if risk not in {"none", "low", "medium", "high"}:
        risk = "medium"
    url = item.get("url") or item.get("html_url") or item.get("link") or None
    return {"title": title, "url": url, "why_it_matters": why, "risk": risk}


def _default_headline(repo: str, releases: list, issues: list) -> str:
    return f"{len(releases)} new release(s), {len(issues)} issue(s) worth watching in {repo}."


def _actions_from_model_items(actions: Any, releases: list[dict], issues: list[dict]) -> list[str]:
    if isinstance(actions, str) and actions.strip():
        return [actions.strip()]
    if isinstance(actions, list) and actions:
        out = []
        for action in actions:
            if isinstance(action, dict):
                text = _first_str(action, "action", "text", "title", "step")
            else:
                text = str(action).strip()
            if text:
                out.append(text)
        if out:
            return out
    out = []
    if any((r.get("risk") or "") == "high" for r in releases):
        out.append("Read the high risk release notes and pin your current version before upgrading.")
    elif releases:
        first = releases[0].get("title") or "the latest release"
        out.append(f"Read the notes for {first} before you upgrade.")
    if issues:
        out.append("Review the open issues and PRs listed above.")
    return out


def _brief_from_model_items(
    repo: str,
    headline: str,
    releases: list,
    issues: list,
    actions: Any = None,
) -> BuilderBrief:
    rel_items = [_release_from_model_item(x) for x in releases or []]
    iss_items = [_issue_from_model_item(x) for x in issues or []]
    data = {
        "repo": repo or "unknown",
        "headline": (headline or "").strip() or _default_headline(repo or "unknown", rel_items, iss_items),
        "releases": rel_items[:5],
        "issues_to_watch": iss_items[:8],
        "actions": _actions_from_model_items(actions, rel_items, iss_items),
    }
    return BuilderBrief.model_validate(data)


def brief_from_model_payload(payload: Any, default_repo: str = "") -> BuilderBrief | None:
    """Turn a model JSON value, including wrapped snapshot shapes, into a BuilderBrief.

    This uses the items and text in the model reply, not the local snapshot cache.
    """
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return None

    def _repo_of(obj: dict) -> str:
        return str(obj.get("repo") or obj.get("repo_spec") or "").strip()

    def _headline_of(obj: dict) -> str:
        value = obj.get("headline")
        if isinstance(value, str) and value.strip():
            return value.strip()
        summary = obj.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        return ""

    # Peel one nesting layer at a time, keeping repo and headline from the outside.
    repo = _repo_of(payload) or default_repo
    headline = _headline_of(payload)
    src = dict(payload)
    for _ in range(4):
        inner = None
        for key in _WRAPPER_KEYS:
            value = src.get(key)
            if isinstance(value, dict) and (
                "releases" in value or "issues" in value or "issues_to_watch" in value
                or any(isinstance(value.get(k), dict) for k in _WRAPPER_KEYS)
            ):
                inner = value
                break
        if inner is None:
            break
        repo = _repo_of(inner) or repo
        headline = _headline_of(inner) or headline
        src = dict(inner)
        if repo and not src.get("repo") and not src.get("repo_spec"):
            src["repo"] = repo
        if headline and not src.get("headline"):
            src["headline"] = headline

    repo = _repo_of(src) or repo or "unknown"
    headline = _headline_of(src) or headline
    releases = src.get("releases") if isinstance(src.get("releases"), list) else []
    if isinstance(src.get("issues_to_watch"), list):
        issues = src["issues_to_watch"]
    elif isinstance(src.get("issues"), list):
        issues = src["issues"]
    elif isinstance(src.get("issues_prs"), list):
        issues = src["issues_prs"]
    else:
        issues = []
    actions = src.get("actions")
    if not releases and not issues:
        return None

    # Prefer a normal BuilderBrief when the model already used schema fields.
    looks_schema = any(
        isinstance(x, dict) and ("why_it_matters" in x or ("title" in x and "risk" in x))
        for x in (releases[:1] + issues[:1])
    )
    if looks_schema or headline:
        try:
            data = _normalize_brief_dict({**src, "repo": repo, "headline": headline or src.get("headline") or ""})
            if not data.get("headline"):
                data["headline"] = _default_headline(repo, data.get("releases") or [], data.get("issues_to_watch") or [])
            if not data.get("actions"):
                data["actions"] = _actions_from_model_items(None, data.get("releases") or [], data.get("issues_to_watch") or [])
            return BuilderBrief.model_validate(data)
        except ValidationError:
            pass
    return _brief_from_model_items(repo, headline, releases, issues, actions)


def parse_builder_brief(text: str) -> BuilderBrief:
    """Parse a BuilderBrief from model text, repairing Markdown-wrapped or messy JSON."""
    blob = extract_json_object(text)
    raw: Any = None
    if blob:
        try:
            return BuilderBrief.model_validate_json(blob)
        except ValidationError:
            pass
        try:
            raw = json.loads(blob)
        except json.JSONDecodeError as exc:
            raise BriefParseError(f"JSON did not validate as BuilderBrief: {exc}") from exc
        if isinstance(raw, dict):
            try:
                return BuilderBrief.model_validate(_normalize_brief_dict(raw))
            except ValidationError:
                brief = brief_from_model_payload(raw)
                if brief is not None:
                    return brief
    payload = _unwrap_payload(text)
    brief = brief_from_model_payload(payload)
    if brief is not None:
        return brief
    if not blob and payload is None:
        raise BriefParseError("no JSON object found in model reply")
    raise BriefParseError("JSON did not validate as BuilderBrief")


def _brief_from_wrapped_payload(payload: Any) -> BuilderBrief | None:
    """Back-compat alias used by tests and older callers."""
    return brief_from_model_payload(payload)


_ISSUE_NUM = re.compile(r"#(\d+)")
_BARE_ISSUE_NUM = re.compile(r"(?:^|#)(\d{1,6})\b")
_RELEASE_TAG_URL = re.compile(r"^(https://github\.com/[^/]+/[^/]+/releases/tag/)(.+)$")


def _issue_number_from_item(item: BriefItem) -> str | None:
    found = _ISSUE_NUM.search(item.title or "") or _ISSUE_NUM.search(item.url or "")
    if found:
        return found.group(1)
    found = _BARE_ISSUE_NUM.search((item.title or "").strip())
    if found:
        return found.group(1)
    return None


def _norm_tag(value: str) -> str:
    return (value or "").strip().lstrip("vV").lower()


def apply_tool_urls(b: BuilderBrief, cache: dict[str, Any] | None) -> BuilderBrief:
    """Replace model-guessed URLs with the exact links returned by the GitHub tools.

    Models sometimes drop the leading v in a GitHub release tag, which 404s.
    """
    if not cache:
        return b
    releases = cache.get("releases") or []
    issues = cache.get("issues") or []
    tag_urls: dict[str, str] = {}
    for row in releases:
        url = (row.get("url") or "").strip()
        if not url:
            continue
        for key in (row.get("tag") or "", row.get("name") or ""):
            if key:
                tag_urls[key.strip().lower()] = url
                tag_urls[_norm_tag(key)] = url
    issue_urls: dict[str, str] = {}
    for row in issues:
        url = (row.get("url") or "").strip()
        number = row.get("number")
        if url and number is not None:
            issue_urls[str(number)] = url

    fixed_releases = []
    for item in b.releases:
        url = item.url
        blob = f"{item.title} {item.url or ""}"
        for key, known in tag_urls.items():
            if key and key in blob.lower():
                url = known
                break
        if url:
            match = _RELEASE_TAG_URL.match(url)
            if match:
                prefix, tag = match.group(1), match.group(2)
                if _norm_tag(tag) in tag_urls:
                    url = tag_urls[_norm_tag(tag)]
                elif tag_urls.get(tag.lower()):
                    url = tag_urls[tag.lower()]
        fixed_releases.append(item.model_copy(update={"url": url}))

    fixed_issues = []
    for item in b.issues_to_watch:
        url = item.url
        number = _issue_number_from_item(item)
        if number and number in issue_urls:
            url = issue_urls[number]
        fixed_issues.append(item.model_copy(update={"url": url}))

    return b.model_copy(update={"releases": fixed_releases, "issues_to_watch": fixed_issues})


def enrich_brief_from_cache(b: BuilderBrief, cache: dict[str, Any] | None) -> BuilderBrief:
    """Fill empty why/risk/title details from the live snapshot the model was given.

    Headline, selected items, and actions stay those of the model. This only
    completes fields the model left blank, using the same snapshot facts.
    """
    if not cache:
        return b
    releases = cache.get("releases") or []
    issues = cache.get("issues") or []

    def match_release(item: BriefItem) -> dict | None:
        blob = f"{item.title} {item.url or ''}".lower()
        for row in releases:
            for key in (row.get("tag") or "", row.get("name") or ""):
                if key and (key.lower() in blob or _norm_tag(key) in _norm_tag(blob)):
                    return row
        return None

    def match_issue(item: BriefItem) -> dict | None:
        number = _issue_number_from_item(item)
        if not number:
            return None
        for row in issues:
            if str(row.get("number")) == number:
                return row
        return None

    fixed_releases = []
    for item in b.releases:
        row = match_release(item)
        if not row:
            fixed_releases.append(item)
            continue
        updates: dict[str, Any] = {}
        tag, name = row.get("tag") or "", row.get("name") or ""
        if tag and tag not in (item.title or "") and _norm_tag(item.title) in {_norm_tag(tag), _norm_tag(name), _norm_tag(item.title)}:
            updates["title"] = f"{tag}: {name or item.title}"
        if not (item.why_it_matters or "").strip():
            why = _why_from_body(row.get("body") or "")
            if why:
                updates["why_it_matters"] = why
        if (item.risk or "none") == "none":
            updates["risk"] = _risk_from_text(item.title, row.get("name") or "", row.get("body") or "", default="low")
        if row.get("url") and not item.url:
            updates["url"] = row.get("url")
        fixed_releases.append(item.model_copy(update=updates) if updates else item)

    fixed_issues = []
    for item in b.issues_to_watch:
        row = match_issue(item)
        if not row:
            fixed_issues.append(item)
            continue
        updates = {}
        if not (item.why_it_matters or "").strip():
            why = _why_from_body(row.get("body") or "") or _first_str(row, "title")
            if why:
                updates["why_it_matters"] = why
        if (item.risk or "none") == "none":
            labels = row.get("labels") or []
            label_text = " ".join(labels) if isinstance(labels, list) else str(labels)
            updates["risk"] = _risk_from_text(
                item.title, row.get("title") or "", row.get("body") or "", label_text,
                default="medium" if (row.get("state") == "open" or diff.is_bug(row)) else "low",
            )
        if row.get("url") and not item.url:
            updates["url"] = row.get("url")
        fixed_issues.append(item.model_copy(update=updates) if updates else item)

    return b.model_copy(update={"releases": fixed_releases, "issues_to_watch": fixed_issues})

