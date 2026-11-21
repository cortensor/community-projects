from openminion.modules.session.storage.store import SQLiteSessionStore
from openminion.modules.tool.base import ToolExecutionContext
from openminion.modules.tool.contracts.provider_types import ProviderToolCall

from triage_agent.orchestrator import build_registry


def test_openminion_tool_registry_executes_decorated_tool() -> None:
    registry = build_registry()
    call = ProviderToolCall(
        name="triage.assess_issue",
        arguments={
            "issue_json": '{"number":1,"title":"Crash on startup","body":"No steps","labels":["bug"]}'
        },
        id="offline-call",
    )
    batch = registry.execute_calls(
        [call],
        context=ToolExecutionContext(channel="test", target="triage", session_id="s-1"),
    )
    assert len(batch.results) == 1
    assert batch.results[0].ok is True
    assert '"severity": "high"' in batch.results[0].content


def test_openminion_session_store_keeps_events_and_turns() -> None:
    store = SQLiteSessionStore(":memory:")
    session_id = store.create_session(title="test", initial_agent_id="triage-agent")
    store.append_event(
        session_id,
        event_type="triage.test",
        payload={"ok": True},
        actor_type="agent",
        actor_id="triage-agent",
    )
    store.append_turn(session_id, "assistant", "complete")
    events = store.list_events(session_id)
    turns = store.list_turns(session_id)
    assert any(item.get("type") == "triage.test" for item in events)
    assert turns[-1]["content"] == "complete"

