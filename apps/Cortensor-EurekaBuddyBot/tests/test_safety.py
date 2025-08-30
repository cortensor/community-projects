import os
import sys
import tempfile
import importlib

# Ensure repo root is on sys.path for `import src`
THIS_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def test_safety_custom_words_and_checks():
    from src import safety as safety
    importlib.reload(safety)

    # Isolate persistence to a temp dir
    tmpdir = tempfile.mkdtemp(prefix="safety-test-")
    safety._DATA_DIR = tmpdir  # type: ignore[attr-defined]
    safety._CUSTOM_FILE = os.path.join(tmpdir, "custom_words.json")  # type: ignore[attr-defined]

    # Start clean
    safety._CUSTOM_BAD_WORDS.clear()  # type: ignore[attr-defined]
    safety._CUSTOM_BAD_WORDS_RE.clear()  # type: ignore[attr-defined]

    chat_id = 12345

    # Basic PII and profanity checks
    assert safety.is_input_unsafe(chat_id, "email me at kid@example.com") is True
    assert safety.is_output_safe(chat_id, "this is shit") is False  # profanity

    # Custom words add/remove
    assert safety.add_bad_word(chat_id, "xqzvword") is True
    assert safety.add_bad_word(chat_id, "xqzvword") is False  # duplicate
    assert safety.custom_count(chat_id) == 1
    assert safety.is_input_unsafe(chat_id, "hello xqzvword world") is True
    assert safety.remove_bad_word(chat_id, "xqzvword") is True
    assert safety.custom_count(chat_id) == 0
    assert safety.is_input_unsafe(chat_id, "hello xqzvword world") is False

    # Sanitize output masks PII
    sanitized = safety.sanitize_output("Call +1-202-555-0198 or mail me@site.com")
    assert "[hidden-phone]" in sanitized
    assert "[hidden-email]" in sanitized


def test_safety_persistence_roundtrip():
    from src import safety as safety
    importlib.reload(safety)

    tmpdir = tempfile.mkdtemp(prefix="safety-test-")
    safety._DATA_DIR = tmpdir  # type: ignore[attr-defined]
    safety._CUSTOM_FILE = os.path.join(tmpdir, "custom_words.json")  # type: ignore[attr-defined]

    chat_id = 67890

    # Clean and add word
    safety._CUSTOM_BAD_WORDS.clear()  # type: ignore[attr-defined]
    safety._CUSTOM_BAD_WORDS_RE.clear()  # type: ignore[attr-defined]
    assert safety.add_bad_word(chat_id, "baz") is True
    safety.save_state()

    # Drop in-memory and reload
    safety._CUSTOM_BAD_WORDS.clear()  # type: ignore[attr-defined]
    safety._CUSTOM_BAD_WORDS_RE.clear()  # type: ignore[attr-defined]
    safety.load_state()

    assert safety.custom_count(chat_id) == 1
    assert safety.is_input_unsafe(chat_id, "say baz please") is True
