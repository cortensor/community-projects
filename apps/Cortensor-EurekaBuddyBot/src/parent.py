import logging
import json
import os
from typing import Set, Dict, Literal, Optional

logger = logging.getLogger(__name__)

# Per-chat parent mode state
_AUTHORIZED_CHATS: Set[int] = set()
PendingType = Literal["verify", "set"]
# Tracks per-chat pending PIN interaction and try counts
_PENDING: Dict[int, Dict[str, int | str]] = {}
_CHAT_PIN: Dict[int, str] = {}

# Persistence
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_PINS_FILE = os.path.join(_DATA_DIR, "parent_pins.json")

# Admins (Telegram user IDs) allowed to manage other chats' PINs
ADMIN_USER_IDS: Set[int] = {6034232050}
MAX_PIN_ATTEMPTS = 3


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def is_authorized(chat_id: int) -> bool:
    return chat_id in _AUTHORIZED_CHATS


def has_pin(chat_id: int) -> bool:
    return chat_id in _CHAT_PIN and bool(_CHAT_PIN[chat_id])


def is_waiting(chat_id: int) -> bool:
    p = _PENDING.get(chat_id)
    if not p:
        return False
    tries = int(p.get("tries", 0))
    return tries < MAX_PIN_ATTEMPTS


def prompt_verify_pin(update, context) -> None:
    chat_id = update.effective_chat.id
    _PENDING[chat_id] = {"type": "verify", "tries": 0}
    update.message.reply_text("Parent mode: Please enter your PIN (3 attempts).")


def prompt_set_pin(update, context) -> None:
    chat_id = update.effective_chat.id
    _PENDING[chat_id] = {"type": "set", "tries": 0}
    update.message.reply_text("No PIN is set for this chat yet. Please send a new PIN now (3 attempts).")


def handle_pin_input(update, context, provided: str) -> None:
    chat_id = update.effective_chat.id
    pin = (provided or "").strip()
    p = _PENDING.get(chat_id)
    if not p:
        # No pending interaction; ignore
        return
    ptype: Optional[str] = p.get("type")  # 'verify' or 'set'
    tries = int(p.get("tries", 0))

    def bump_and_maybe_stop(msg: str) -> None:
        nonlocal tries
        tries += 1
        p["tries"] = tries
        if tries >= MAX_PIN_ATTEMPTS:
            _PENDING.pop(chat_id, None)
            update.message.reply_text(msg + " You have reached the maximum attempts. Please run the command again to retry.")
        else:
            update.message.reply_text(msg + f" Attempts left: {MAX_PIN_ATTEMPTS - tries}.")

    if ptype == "set":
        if not pin:
            bump_and_maybe_stop("PIN cannot be empty.")
            return
        _CHAT_PIN[chat_id] = pin
        _AUTHORIZED_CHATS.add(chat_id)
        _PENDING.pop(chat_id, None)
        try:
            save_state()
        except Exception:
            pass
        update.message.reply_text("PIN set. Parent mode is now unlocked for this chat.")
        return

    if ptype == "verify":
        current = _CHAT_PIN.get(chat_id)
        if pin and current and pin == current:
            _AUTHORIZED_CHATS.add(chat_id)
            _PENDING.pop(chat_id, None)
            update.message.reply_text("PIN correct. Parent mode is now unlocked for this chat.")
        else:
            bump_and_maybe_stop("Incorrect PIN.")


def require_parent(update) -> bool:
    """Return True if authorized; otherwise prompt to verify or set PIN and return False."""
    chat_id = update.effective_chat.id
    if is_authorized(chat_id):
        return True
    if has_pin(chat_id):
        prompt_verify_pin(update, None)
    else:
        prompt_set_pin(update, None)
    return False


def set_pin_command(update, context) -> None:
    chat_id = update.effective_chat.id
    args = getattr(context, "args", None) or []
    if not args:
        update.message.reply_text("Usage: /setpin <new_pin>")
        return
    new_pin = (args[0] or "").strip()
    if not new_pin:
        update.message.reply_text("PIN cannot be empty.")
        return
    # If a PIN exists, require unlocked parent mode to change it
    if has_pin(chat_id) and not is_authorized(chat_id):
        update.message.reply_text("Please unlock parent mode first with /parent.")
        return
    _CHAT_PIN[chat_id] = new_pin
    _AUTHORIZED_CHATS.add(chat_id)
    _PENDING.pop(chat_id, None)
    try:
        save_state()
    except Exception:
        pass
    update.message.reply_text("PIN updated. Parent mode is unlocked.")


def lock_parent(update, context) -> None:
    chat_id = update.effective_chat.id
    _AUTHORIZED_CHATS.discard(chat_id)
    update.message.reply_text("Parent mode locked for this chat.")


def admin_reset_pin(update, context) -> None:
    """Admin-only: reset or set a PIN for another chat.

    Usage: /resetpin <chat_id> [new_pin]
    - If new_pin is provided, sets it for the target chat and locks parent mode.
    - If omitted, clears any existing PIN and locks parent mode.
    """
    user = getattr(update, "effective_user", None)
    uid = getattr(user, "id", None)
    if not uid or not is_admin(uid):
        update.message.reply_text("Unauthorized.")
        return

    args = getattr(context, "args", None) or []
    if not args:
        update.message.reply_text("Usage: /resetpin <chat_id> [new_pin]")
        return
    try:
        target_chat_id = int(args[0])
    except Exception:
        update.message.reply_text("Invalid chat_id.")
        return
    new_pin = None
    if len(args) > 1:
        new_pin = (args[1] or "").strip()
        if not new_pin:
            new_pin = None

    existed = target_chat_id in _CHAT_PIN
    if new_pin is not None:
        _CHAT_PIN[target_chat_id] = new_pin
    else:
        _CHAT_PIN.pop(target_chat_id, None)

    # Always lock and clear pending states for the target chat
    _AUTHORIZED_CHATS.discard(target_chat_id)
    _PENDING.pop(target_chat_id, None)

    try:
        save_state()
    except Exception:
        pass

    if new_pin is not None:
        update.message.reply_text(f"PIN for chat {target_chat_id} has been set and parent mode locked.")
    else:
        update.message.reply_text(
            f"PIN for chat {target_chat_id} {'cleared' if existed else 'was not set'}. Parent mode locked."
        )


def _ensure_data_dir() -> None:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
    except Exception:
        pass


def load_state() -> None:
    """Load per-chat PINs from disk."""
    global _CHAT_PIN
    _ensure_data_dir()
    try:
        if os.path.exists(_PINS_FILE):
            with open(_PINS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # keys stored as strings; convert to int
                _CHAT_PIN = {int(k): str(v) for k, v in (data or {}).items()}
    except Exception as e:
        logger.warning(f"Failed to load parent pins: {e}")


def save_state() -> None:
    """Persist per-chat PINs to disk."""
    _ensure_data_dir()
    try:
        with open(_PINS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in _CHAT_PIN.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save parent pins: {e}")
