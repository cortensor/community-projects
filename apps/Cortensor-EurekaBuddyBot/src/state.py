from typing import Dict, Tuple, List
from .config import DEFAULT_AGENT_STYLE, MODEL_PROVIDER_DEFAULT, MODEL_NAME_DEFAULT, MEMORY_ENABLED, MEMORY_MAX_TURNS

CHAT_STYLE: Dict[int, str] = {}
CHAT_MODEL: Dict[int, Tuple[str, str]] = {}
CHAT_MEMORY: Dict[int, List[Tuple[str, str]]] = {}

def get_style(chat_id: int) -> str:
    return CHAT_STYLE.get(chat_id, DEFAULT_AGENT_STYLE)

def set_style(chat_id: int, style_id: str) -> None:
    CHAT_STYLE[chat_id] = style_id

def reset_style(chat_id: int) -> None:
    CHAT_STYLE.pop(chat_id, None)
    CHAT_MEMORY.pop(chat_id, None)

def set_model(chat_id: int, provider: str, model: str) -> None:
    CHAT_MODEL[chat_id] = (provider, model)

def get_model(chat_id: int) -> Tuple[str, str]:
    return CHAT_MODEL.get(chat_id, (MODEL_PROVIDER_DEFAULT, MODEL_NAME_DEFAULT))

def remember_turn(chat_id: int, user_text: str, bot_text: str) -> None:
    if not MEMORY_ENABLED:
        return
    history = CHAT_MEMORY.setdefault(chat_id, [])
    history.append((user_text, bot_text))
    # Trim to last N turns
    if len(history) > MEMORY_MAX_TURNS:
        del history[:-MEMORY_MAX_TURNS]

def get_history(chat_id: int) -> List[Tuple[str, str]]:
    if not MEMORY_ENABLED:
        return []
    return CHAT_MEMORY.get(chat_id, [])
