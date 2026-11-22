import json
from datetime import datetime, timezone

from minion_radar import brief, diff, github, state
from minion_radar.agent import session_id_for
from minion_radar.brief import BriefParseError, extract_json_object, parse_builder_brief, repair_json_text


def test_new_items_and_checkpoint(tmp_path):
    rel = github.fetch_releases("x/y", demo=True)
    iss = github.fetch_issues("x/y", demo=True)
    st = state.load("x/y", tmp_path)
    assert len(diff.new_releases(rel, st)) == 2
    assert len(diff.new_or_updated_issues(iss, st)) == 3
    st2 = diff.next_state(st, rel, iss, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    state.save(st2, tmp_path)
    again = state.load("x/y", tmp_path)
    assert diff.new_releases(rel, again) == []
    assert diff.new_or_updated_issues(iss, again) == []
    iss[0]["updated_at"] = "2026-12-01T00:00:00Z"
    assert len(diff.new_or_updated_issues(iss, again)) == 1


def test_risk_and_bug_detection():
    assert diff.risk_flags("Breaking: removed X") == ["breaking", "remove", "removed"]
    assert diff.is_bug({"labels": ["Bug"], "title": "x"})
    assert not diff.is_bug({"labels": ["docs"], "title": "typo"})


def test_offline_brief_marks_breaking_high():
    b = brief.offline_brief("x/y", github.fetch_releases("x/y", demo=True), github.fetch_issues("x/y", demo=True))
    assert b.releases[0].risk == "high"
    assert len(b.issues_to_watch) == 2  # bug + deprecate, not the docs PR
    md = brief.to_markdown(b, "DEMO")
    assert "> DEMO" in md and "Actions" in md


def test_tools_register_with_openminion(tmp_path):
    from minion_radar.agent import build_tools
    tools, cache = build_tools("x/y", demo=True, state_root=tmp_path)
    assert len(tools) == 3


def test_session_id_has_no_slash():
    sid = session_id_for("openminion/openminion")
    assert "/" not in sid
    assert sid == "minion-radar:openminion__openminion"
    assert session_id_for("owner/name") == "minion-radar:owner__name"


VALID = {
    "repo": "openminion/openminion",
    "headline": "Two releases, one bug.",
    "releases": [
        {"title": "v9.9.1: breaking registry", "url": "https://example.com/r",
         "why_it_matters": "Migration required.", "risk": "high"}
    ],
    "issues_to_watch": [
        {"title": "#101 streaming tool call", "url": None,
         "why_it_matters": "Arguments drop.", "risk": "high"}
    ],
    "actions": ["Read the migration guide."],
}


def _json(obj=None, **kwargs):
    import json
    return json.dumps(obj if obj is not None else VALID, **kwargs)


def test_parse_plain_json():
    b = parse_builder_brief(_json())
    assert b.repo == "openminion/openminion"
    assert b.releases[0].risk == "high"
    assert b.actions == ["Read the migration guide."]


def test_parse_fenced_json():
    text = f"Here is the brief:\n```json\n{_json(indent=2)}\n```\nThanks."
    b = parse_builder_brief(text)
    assert b.headline == "Two releases, one bug."
    assert extract_json_object(text)


def test_parse_fenced_json_without_language_tag():
    b = parse_builder_brief(f"```\n{_json()}\n```")
    assert b.repo.endswith("openminion")


def test_parse_prose_wrapped_json():
    text = "radar: **BuilderBrief**\n" + _json() + "\nDone."
    b = parse_builder_brief(text)
    assert len(b.issues_to_watch) == 1


def test_repair_trailing_comma_and_smart_quotes():
    messy = (
        '{\n'
        '  "repo": “openminion/openminion”,\n'
        '  "headline": "Two releases, one bug.",\n'
        '  "releases": [\n'
        '    {"title": "v9.9.1", "url": null, "why_it_matters": "Migration.", "risk": "high"},\n'
        '  ],\n'
        '  "issues_to_watch": [],\n'
        '  "actions": ["Pin the version.",],\n'
        '}'
    )
    assert repair_json_text(messy)
    b = parse_builder_brief("```json\n" + messy + "\n```")
    assert b.repo == "openminion/openminion"
    assert b.actions == ["Pin the version."]
    assert b.releases[0].title == "v9.9.1"


def test_parse_markdown_without_json_raises():
    markdown = """radar: **BuilderBrief**

* Release: v9.9.1 - Breaking change to tool registry. (High)
* Issue: #101 - streaming tool call drops arguments. (Bug, High)
"""
    assert extract_json_object(markdown) is None
    try:
        parse_builder_brief(markdown)
        assert False, "expected BriefParseError"
    except BriefParseError as exc:
        assert "no JSON object" in str(exc)


def test_repair_aliased_fields_from_real_model():
    """oss-20b first pass used version/summary and issues_prs instead of the schema names."""
    text = """radar: {
      "repo": "openminion/openminion",
      "headline": "A useful headline",
      "releases": [
        {"version": "0.1.23", "date": "2026-11-17", "summary": "Config diff and CLI fixes.", "risk": "low"}
      ],
      "issues_prs": [
        {"id": "#815", "title": "memctl default memory.yaml", "type": "pr", "risk": "low",
         "action": "Add a default memory.yaml before running memctl"}
      ],
      "actions": ["Validate the new release in CI."]
    }
    """
    b = parse_builder_brief(text)
    assert b.repo == "openminion/openminion"
    assert b.releases[0].title == "0.1.23"
    assert b.releases[0].why_it_matters == "Config diff and CLI fixes."
    assert b.releases[0].risk == "low"
    assert b.issues_to_watch[0].title == "#815 memctl default memory.yaml"
    assert "memory.yaml" in b.issues_to_watch[0].why_it_matters
    assert b.actions == ["Validate the new release in CI."]


def test_apply_tool_urls_restores_leading_v():
    b = parse_builder_brief(_json())
    # model dropped the v in the tag url
    b.releases[0].url = "https://github.com/openminion/openminion/releases/tag/0.1.23"
    b.releases[0].title = "0.1.23: config diff"
    b.issues_to_watch[0].title = "#815 memctl default memory.yaml"
    b.issues_to_watch[0].url = "https://example.com/wrong"
    cache = {
        "releases": [{
            "tag": "v0.1.23", "name": "0.1.23",
            "url": "https://github.com/openminion/openminion/releases/tag/v0.1.23",
        }],
        "issues": [{
            "number": 815,
            "url": "https://github.com/openminion/openminion/pull/815",
        }],
    }
    fixed = brief.apply_tool_urls(b, cache)
    assert fixed.releases[0].url.endswith("/releases/tag/v0.1.23")
    assert fixed.issues_to_watch[0].url.endswith("/pull/815")


def test_film_tools_are_compact(tmp_path):
    from minion_radar.agent import build_tools
    tools, cache = build_tools("x/y", demo=True, state_root=tmp_path, compact=True)
    assert [fn.__name__ for fn in tools] == ["radar_snapshot", "radar_save_checkpoint"]
    payload = json.loads(tools[0]())
    assert "releases" in payload and "issues" in payload
    assert cache["releases"] and cache["issues"]


def test_parse_snapshot_wrapper_from_model():
    text = """```json
    [{
      "type": "BuilderBrief",
      "repo_spec": "openminion/openminion",
      "radar_snapshot": {
        "releases": [
          {"id": 1, "tag": "v0.1.23", "name": "0.1.23",
           "url": "https://github.com/openminion/openminion/releases/tag/v0.1.23",
           "body": "Breaking: removed the old flag. Migration required."}
        ],
        "issues": [
          {"id": 2, "number": 642, "title": "security audit stores", "kind": "issue",
           "state": "open", "labels": ["security"], "url": "https://github.com/openminion/openminion/issues/642",
           "body": "PII in 0644 stores"}
        ]
      }
    }]
    ```"""
    b = parse_builder_brief(text)
    assert b.repo == "openminion/openminion"
    assert b.releases
    assert "v0.1.23" in b.releases[0].title
    assert b.releases[0].url.endswith("/releases/tag/v0.1.23")
    assert b.releases[0].risk == "high"
    assert "Migration" in b.releases[0].why_it_matters or "Breaking" in b.releases[0].why_it_matters
    assert "New release; read notes before upgrading." not in b.releases[0].why_it_matters
    assert any("642" in i.title for i in b.issues_to_watch)


def test_parse_summary_wrapper_is_model_brief():
    """oss-20b film replies nested the snapshot under summary instead of BuilderBrief keys."""
    text = """```json
    {
      "repo": "openminion/openminion",
      "summary": {
        "releases": [
          {
            "tag": "v0.1.23",
            "name": "0.1.23",
            "url": "https://github.com/openminion/openminion/releases/tag/v0.1.23",
            "body": "OpenMinion 0.1.23 improves configuration previews and CLI error handling. Highlights: Add openminion config diff."
          },
          {
            "tag": "v0.1.22",
            "name": "0.1.22",
            "url": "https://github.com/openminion/openminion/releases/tag/v0.1.22",
            "body": "Highlights: update the MiniMax profile to MiniMax-M3.1-Flash"
          }
        ],
        "issues": [
          {
            "number": 815,
            "title": "memctl: derive the default config when memory.yaml is absent",
            "kind": "pr",
            "state": "open",
            "url": "https://github.com/openminion/openminion/pull/815",
            "body": "In the standard layout, memctl cannot run at all."
          },
          {
            "number": 642,
            "title": "security audit: PII sits in 0644 stores",
            "kind": "issue",
            "state": "open",
            "labels": ["bug", "security"],
            "url": "https://github.com/openminion/openminion/issues/642",
            "body": "PII sits in 0644 stores and approval events are missing."
          }
        ]
      }
    }
    ```"""
    b = parse_builder_brief(text)
    assert b.repo == "openminion/openminion"
    assert b.releases[0].url.endswith("/releases/tag/v0.1.23")
    assert "configuration previews" in b.releases[0].why_it_matters
    assert "New release; read notes before upgrading." not in b.releases[0].why_it_matters
    assert "MiniMax" in b.releases[1].why_it_matters
    assert any("815" in i.title for i in b.issues_to_watch)
    assert any("642" in i.title for i in b.issues_to_watch)
    assert any(i.risk == "high" for i in b.issues_to_watch)
    # Keep the model's selected PR, not only bug-filtered items.
    assert len(b.issues_to_watch) == 2


def test_parse_data_and_result_wrappers():
    wrapped = {
        "data": {
            "result": {
                "repo_spec": "owner/name",
                "releases": [
                    {"tag": "v1.2.0", "name": "1.2.0",
                     "url": "https://github.com/owner/name/releases/tag/v1.2.0",
                     "why_it_matters": "Adds a safer default.", "risk": "low"}
                ],
                "issues": [],
                "actions": ["Upgrade in a branch."]
            }
        }
    }
    b = parse_builder_brief("```json\n" + json.dumps(wrapped) + "\n```")
    assert b.repo == "owner/name"
    assert b.releases[0].title.startswith("v1.2.0") or "1.2.0" in b.releases[0].title
    assert b.releases[0].why_it_matters == "Adds a safer default."
    assert b.actions == ["Upgrade in a branch."]


def test_parse_string_releases_and_enrich_from_cache():
    """The film model returned release versions as strings and omitted urls, why, and risk."""
    text = """{
      "repo": "openminion/openminion",
      "headline": "OpenMinion 0.1.23 latest improvements for runtime, CLI, and SDK",
      "releases": ["0.1.21", "0.1.22", "0.1.23"],
      "issues_to_watch": [
        {"id": 642, "number": 642,
         "title": "security audit: approval binding holds and guards fail closed, PII sits in 0644 stores"},
        {"id": 612, "number": 612,
         "title": "tools: async @tool handlers are never awaited; tool result is a coroutine object"}
      ],
      "actions": [
        "Verify that all async @tool handlers are awaited before returning results.",
        "Make sure memctl can auto-derive default config when implicit defaults are missing."
      ]
    }"""
    b = parse_builder_brief(text)
    assert b.headline.startswith("OpenMinion 0.1.23")
    assert [r.title for r in b.releases] == ["0.1.21", "0.1.22", "0.1.23"]
    assert b.actions[0].startswith("Verify that all async")
    cache = {
        "releases": [
            {"tag": "v0.1.23", "name": "0.1.23",
             "url": "https://github.com/openminion/openminion/releases/tag/v0.1.23",
             "body": "OpenMinion 0.1.23 improves configuration previews and CLI error handling."},
            {"tag": "v0.1.22", "name": "0.1.22",
             "url": "https://github.com/openminion/openminion/releases/tag/v0.1.22",
             "body": "Highlights:\n- update the MiniMax profile to MiniMax-M3.1-Flash"},
            {"tag": "v0.1.21", "name": "0.1.21",
             "url": "https://github.com/openminion/openminion/releases/tag/v0.1.21",
             "body": "OpenMinion 0.1.21 improves runtime correctness, security, and packaged policy data."},
        ],
        "issues": [
            {"number": 642,
             "title": "security audit: approval binding holds and guards fail closed, but PII sits in 0644 stores",
             "url": "https://github.com/openminion/openminion/issues/642",
             "labels": ["bug", "security"], "state": "open",
             "body": "PII sits in 0644 stores and approval/rollback events are missing."},
            {"number": 612,
             "title": "tools: async @tool handlers are never awaited",
             "url": "https://github.com/openminion/openminion/issues/612",
             "labels": ["bug"], "state": "open",
             "body": "The tool result is a coroutine object."},
        ],
    }
    filled = brief.enrich_brief_from_cache(brief.apply_tool_urls(b, cache), cache)
    assert filled.releases[2].url.endswith("/releases/tag/v0.1.23")
    assert "configuration previews" in filled.releases[2].why_it_matters
    assert filled.releases[0].url.endswith("/releases/tag/v0.1.21")
    assert filled.releases[0].risk == "high"  # notes mention security
    assert filled.issues_to_watch[0].url.endswith("/issues/642")
    assert filled.issues_to_watch[0].risk == "high"
    assert filled.issues_to_watch[1].url.endswith("/issues/612")
    assert "coroutine" in filled.issues_to_watch[1].why_it_matters
    # Model-authored fields are preserved.
    assert filled.headline == b.headline
    assert filled.actions == b.actions
