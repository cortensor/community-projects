import os
import sys
import tempfile
import importlib

# Ensure repo root is on sys.path for `import src`
THIS_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class FakeMessage:
    def __init__(self):
        self.last = None

    def reply_text(self, text: str):
        self.last = text


class FakeUser:
    def __init__(self, uid: int):
        self.id = uid


class FakeChat:
    def __init__(self, cid: int):
        self.id = cid


class FakeUpdate:
    def __init__(self, uid: int, cid: int):
        self.effective_user = FakeUser(uid)
        self.effective_chat = FakeChat(cid)
        self.message = FakeMessage()


class FakeContext:
    def __init__(self, args=None):
        self.args = args or []


def test_parent_persistence_roundtrip():
    from src import parent as parent
    importlib.reload(parent)

    tmpdir = tempfile.mkdtemp(prefix="parent-test-")
    parent._DATA_DIR = tmpdir  # type: ignore[attr-defined]
    parent._PINS_FILE = os.path.join(tmpdir, "parent_pins.json")  # type: ignore[attr-defined]

    # Clean state
    parent._CHAT_PIN.clear()  # type: ignore[attr-defined]

    # Save one pin and reload
    parent._CHAT_PIN[111] = "1234"  # type: ignore[index]
    parent.save_state()

    parent._CHAT_PIN.clear()  # type: ignore[attr-defined]
    parent.load_state()

    assert parent.has_pin(111) is True


def test_admin_reset_pin_flow():
    from src import parent as parent
    importlib.reload(parent)

    tmpdir = tempfile.mkdtemp(prefix="parent-test-")
    parent._DATA_DIR = tmpdir  # type: ignore[attr-defined]
    parent._PINS_FILE = os.path.join(tmpdir, "parent_pins.json")  # type: ignore[attr-defined]

    # Prepare state and admin user
    parent._CHAT_PIN.clear()  # type: ignore[attr-defined]
    admin_uid = next(iter(parent.ADMIN_USER_IDS))

    # Admin sets a pin for target chat
    upd = FakeUpdate(admin_uid, 999)
    ctx = FakeContext(args=["777", "8888"])  # target chat 777, new pin 8888
    parent.admin_reset_pin(upd, ctx)
    assert parent.has_pin(777) is True
    assert parent._CHAT_PIN[777] == "8888"  # type: ignore[index]

    # Admin clears the pin
    upd2 = FakeUpdate(admin_uid, 999)
    ctx2 = FakeContext(args=["777"])  # clear
    parent.admin_reset_pin(upd2, ctx2)
    assert parent.has_pin(777) is False
