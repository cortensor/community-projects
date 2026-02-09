import logging
import os
import re
import json
import requests
from urllib.parse import quote_plus
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction
from telegram.ext import CallbackContext

from .thread_gen import generate_thread, generate_tweet, generate_reply, format_thread_preview
from .db.storage import (
    load_user_defaults,
    save_user_defaults,
    save_history,
    get_recent_history,
    get_history_by_id,
    list_voices,
)
# from .cortensor_api import router_info, router_status, _build_endpoint  # removed with /diag
from .hashtags import suggest_hashtags
from .link_fetch import parse_x_status_id, fetch_x_tweet_json, build_reply_context_from_x, fetch_x_tweet_json_from_text, build_basic_context_from_url
from .rate_limiter import rate_limit_check, record_user_action

logger = logging.getLogger(__name__)

# Use tones from config (loaded from .env)
_TONES = []  # Will be populated from config in _get_tones()
_SESS: dict[str, dict] = {}

# Session cleanup settings (configurable via env)
def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default

_SESSION_TTL_HOURS = _get_int_env('SESSION_TTL_HOURS', 24)
_SESSION_CLEANUP_INTERVAL = _get_int_env('SESSION_CLEANUP_INTERVAL', 3600)
_LAST_CLEANUP_TIME = 0

def _cleanup_old_sessions():
    """Remove sessions older than TTL to prevent memory leak"""
    global _LAST_CLEANUP_TIME
    import time
    now = time.time()
    
    # Only run cleanup if enough time has passed
    if now - _LAST_CLEANUP_TIME < _SESSION_CLEANUP_INTERVAL:
        return
    
    _LAST_CLEANUP_TIME = now
    ttl_seconds = _SESSION_TTL_HOURS * 3600
    expired_uids = []
    
    for uid, sess in _SESS.items():
        created_at = sess.get("_created_at", 0)
        if created_at and (now - created_at) > ttl_seconds:
            expired_uids.append(uid)
    
    for uid in expired_uids:
        try:
            del _SESS[uid]
            logger.debug(f"Cleaned up expired session for user {uid}")
        except Exception:
            pass
    
    if expired_uids:
        logger.info(f"Session cleanup: removed {len(expired_uids)} expired sessions")

def _get_tones() -> list[str]:
    """Get available tones from config (supports runtime changes)"""
    return getattr(_cfg, 'AVAILABLE_TONES', ['concise', 'informative', 'persuasive', 'technical', 'conversational', 'authoritative'])

_IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
_HOST_FIELD_RE = re.compile(r"host='[^']+'", re.I)


def _friendly_error(err: Exception) -> str:
    if isinstance(err, requests.exceptions.Timeout):
        return "Request to the generation service timed out. Please try again."
    if isinstance(err, requests.exceptions.ConnectionError):
        return "Cannot reach the generation service right now. Please retry shortly."
    if isinstance(err, requests.exceptions.RequestException):
        return "Generation service returned an error. Please retry."
    msg = (str(err) or '').strip()
    if not msg:
        msg = err.__class__.__name__
    msg = _IP_RE.sub('<redacted-ip>', msg)
    msg = _HOST_FIELD_RE.sub("host='<hidden>'", msg)
    return msg

def _audit(uid: str, event: str, **fields):
    try:
        extras = " ".join(f"{k}={fields[k]}" for k in fields if fields.get(k) is not None)
        logger.info(f"audit event={event} uid={uid} {extras}")
    except Exception:
        pass


def _check_rate_limit(uid: str, update: Update, is_generation: bool = False) -> bool:
    """
    Check rate limit and send error message if exceeded.
    Returns True if allowed, False if rate limited.
    """
    allowed, msg = rate_limit_check(uid, is_generation=is_generation)
    if not allowed:
        try:
            update.message.reply_text(f"⏳ {msg}")
        except Exception:
            pass
        _audit(uid, "rate_limited", is_generation=is_generation)
        return False
    return True


def _check_rate_limit_callback(uid: str, query, is_generation: bool = False) -> bool:
    """
    Check rate limit for callback queries.
    Returns True if allowed, False if rate limited.
    """
    allowed, msg = rate_limit_check(uid, is_generation=is_generation)
    if not allowed:
        try:
            query.answer(f"⏳ {msg}", show_alert=True)
        except Exception:
            pass
        _audit(uid, "rate_limited", is_generation=is_generation)
        return False
    return True


def _sess(uid: str) -> dict:
    # Run periodic cleanup to prevent memory leaks
    _cleanup_old_sessions()
    
    if uid in _SESS:
        return _SESS[uid]
    # Load defaults from DB if available
    db_defaults = load_user_defaults(uid) or {}
    env_defaults = {
        "tone": getattr(_cfg, 'DEFAULT_TONE', 'concise'),
        "length": getattr(_cfg, 'DEFAULT_LENGTH', 'medium'),
        "n": getattr(_cfg, 'DEFAULT_THREAD_N', 6),
        "hashtags": getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip(),
    }
    dfl = {**env_defaults, **db_defaults}
    _SESS[uid] = {
        "topic": "",
        "n": int(dfl.get("n", 6)),
        "tone": dfl.get("tone", env_defaults["tone"]),
        "hashtags": dfl.get("hashtags", env_defaults["hashtags"]),
        "posts": [],
        "mode": "thread",
        "length": dfl.get("length", env_defaults["length"]),
        "instructions": "",
        "reply_ctx": "",
    "style_cta": False,
    "style_noemoji": False,
    "style_bullets": False,
    "style_stats": False,
    "voice": None,
    "_uid": uid,
    "char_limit": getattr(_cfg, 'TWEET_CHAR_LIMIT', 280),  # Per-user char limit (avoids race condition)
    "_created_at": None,  # For session cleanup
        "defaults": dfl,
    }
    import time
    _SESS[uid]["_created_at"] = time.time()
    return _SESS[uid]


from . import config as _cfg


def _build_preview(sess: dict, max_len: int | None = None) -> str:
    if max_len is None:
        max_len = getattr(_cfg, 'PREVIEW_CHAR_LIMIT', 3900)
    mode = sess.get("mode", "thread")
    tone = sess.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
    if mode == "tweet":
        header = (
            f"Tweet Preview\n"
            f"Topic: {sess.get('topic','')}\n"
            f"Tone: {tone}\n"
            f"Length: {sess.get('length','medium')}\n\n"
        )
    elif mode == "reply":
        # Show context (original post details) before the generated reply
        ctx = (sess.get("reply_ctx") or "").strip()
        ctx_block = (f"Context:\n{ctx}\n\n" if ctx else "")
        header = (
            f"Reply Preview\n"
            f"Tone: {tone}\n\n"
            f"{ctx_block}"
            f"Reply:\n\n"
        )
    else:
        header = (
            f"Thread Preview\n"
            f"Topic: {sess.get('topic','')}\n"
            f"Tone: {tone}\n"
            f"Posts: {sess.get('n',6)}\n"
            f"Tags: {sess.get('hashtags') or '-'}\n\n"
        )
    if mode == 'thread':
        enumerated = format_thread_preview(sess.get('posts', []))
        body = "\n\n".join(enumerated)
    else:
        body = "\n\n".join(p for p in sess.get("posts", []))
    txt = header + body
    return txt if len(txt) <= max_len else txt[: max_len - 20] + "\n\n…(truncated)"


def _send_thread_preview(context: CallbackContext, chat_id: int, sess: dict):
    """Send thread preview as multiple messages if THREAD_SPLIT_SEND is enabled.

    Header is sent first (without posts), then each formatted line, then a controls message with inline keyboard.
    """
    try:
        header = _build_preview({**sess, 'posts': []})
        context.bot.send_message(chat_id=chat_id, text=header)
    except Exception:
        pass
    try:
        lines = format_thread_preview(sess.get('posts', []))
    except Exception:
        lines = sess.get('posts', []) or []
    for ln in lines:
        if not ln:
            continue
        try:
            context.bot.send_message(chat_id=chat_id, text=ln)
        except Exception:
            break
    try:
        context.bot.send_message(chat_id=chat_id, text='Controls:', reply_markup=_kb(sess))
    except Exception:
        pass


def _next_char_limit(current: int) -> int:
    try:
        arr = getattr(_cfg, 'CHAR_LIMIT_PRESETS', [280, 400, 600, 800, 1000])
        if current not in arr:
            # find closest
            arr_sorted = sorted(arr)
            for v in arr_sorted:
                if current < v:
                    return v
            return arr_sorted[0]
        idx = arr.index(current)
        return arr[(idx + 1) % len(arr)]
    except Exception:
        return current


def _kb(sess: dict) -> InlineKeyboardMarkup:
    mode = sess.get("mode", "thread")
    n = int(sess.get("n", getattr(_cfg, 'DEFAULT_THREAD_N', 6)))
    tone = sess.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
    tags_on = bool(sess.get("hashtags"))
    posts = sess.get("posts", []) or []
    # Build the X compose URL. For replies, prefer in_reply_to=<id> if we can extract one.
    first_url = getattr(_cfg, 'X_COMPOSE_URL', 'https://x.com/intent/tweet')
    reply_sid = None
    if mode == "reply":
        # Try to extract status id from stored context text
        ctx = (sess.get("reply_ctx") or "")
        m = re.search(r"/status/(\d+)", ctx)
        reply_sid = m.group(1) if m else None
    if posts:
        limit = getattr(_cfg, 'TWEET_CHAR_LIMIT', 280)
        txt_q = quote_plus((posts[0] or "")[:limit])
        if mode == "reply" and reply_sid:
            first_url = f"{first_url}?in_reply_to={reply_sid}&text={txt_q}"
        else:
            first_url = f"{first_url}?text={txt_q}"
    elif mode == "reply" and reply_sid:
        first_url = f"{first_url}?in_reply_to={reply_sid}"
    rows: list[list[InlineKeyboardButton]] = []
    rows.append([InlineKeyboardButton("🔁 Regenerate", callback_data="thr|regen"),
                InlineKeyboardButton("✖ Close", callback_data="thr|close")])
    if mode == "thread":
        rows.append([
            InlineKeyboardButton("➖ N", callback_data="thr|n|dec"),
            InlineKeyboardButton(f"N={n}", callback_data="thr|noop"),
            InlineKeyboardButton("➕ N", callback_data="thr|n|inc"),
        ])
        rows.append([
            InlineKeyboardButton(f"Tone: {tone}", callback_data="thr|tone|next"),
            InlineKeyboardButton(f"Tags: {'ON' if tags_on else 'OFF'}", callback_data="thr|tags|toggle"),
        ])
        rows.append([
            InlineKeyboardButton(f"Length: {sess.get('length','medium')}", callback_data="thr|length|next"),
            InlineKeyboardButton(f"Max: {sess.get('char_limit', getattr(_cfg,'TWEET_CHAR_LIMIT',280))}", callback_data="thr|climit|next"),
        ])
        rows.append([
            InlineKeyboardButton(f"CTA: {'ON' if sess.get('style_cta') else 'OFF'}", callback_data="thr|style|cta"),
            InlineKeyboardButton(f"No emoji: {'ON' if sess.get('style_noemoji') else 'OFF'}", callback_data="thr|style|noemoji"),
        ])
        rows.append([
            InlineKeyboardButton(f"Bullets: {'ON' if sess.get('style_bullets') else 'OFF'}", callback_data="thr|style|bullets"),
            InlineKeyboardButton(f"Stats: {'ON' if sess.get('style_stats') else 'OFF'}", callback_data="thr|style|stats"),
        ])
        try:
            voices = list_voices(sess.get('_uid')) if sess.get('_uid') else []
        except Exception:
            voices = []
        if voices:
            vname = sess.get('voice') or 'none'
            rows.append([InlineKeyboardButton(f"Voice: {vname}", callback_data="thr|voice|next")])
        rows.append([
            InlineKeyboardButton("✏️ Edit", callback_data="thr|edit|start"),
            InlineKeyboardButton("↻ Line", callback_data="thr|rline|start"),
            InlineKeyboardButton("🏷 Suggest tags", callback_data="thr|tags|suggest"),
            InlineKeyboardButton("➕ Continue", callback_data="thr|cont|next"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(f"Tone: {tone}", callback_data="thr|tone|next"),
            InlineKeyboardButton(f"Length: {sess.get('length','medium')}", callback_data="thr|length|next"),
            InlineKeyboardButton(f"Max: {sess.get('char_limit', getattr(_cfg,'TWEET_CHAR_LIMIT',280))}", callback_data="thr|climit|next"),
        ])
        rows.append([
            InlineKeyboardButton(f"CTA: {'ON' if sess.get('style_cta') else 'OFF'}", callback_data="thr|style|cta"),
            InlineKeyboardButton(f"No emoji: {'ON' if sess.get('style_noemoji') else 'OFF'}", callback_data="thr|style|noemoji"),
        ])
        rows.append([
            InlineKeyboardButton(f"Bullets: {'ON' if sess.get('style_bullets') else 'OFF'}", callback_data="thr|style|bullets"),
            InlineKeyboardButton(f"Stats: {'ON' if sess.get('style_stats') else 'OFF'}", callback_data="thr|style|stats"),
        ])
        try:
            voices = list_voices(sess.get('_uid')) if sess.get('_uid') else []
        except Exception:
            voices = []
        if voices:
            vname = sess.get('voice') or 'none'
            rows.append([InlineKeyboardButton(f"Voice: {vname}", callback_data="thr|voice|next")])
        rows.append([InlineKeyboardButton("✏️ Edit", callback_data="thr|edit|start")])
    if posts:
        rows.append([InlineKeyboardButton("Post to X", url=first_url)])
        rows.append([InlineKeyboardButton("📋 Copy text", callback_data="thr|copy"),
                    InlineKeyboardButton(" Save JSON", callback_data="thr|save")])
    return InlineKeyboardMarkup(rows)


def _reply_kb(sess: dict | None = None) -> ReplyKeyboardMarkup:
    step = (sess or {}).get("wizard_step")
    rows: list[list[str]]
    mode = (sess or {}).get("mode", "thread")
    tones = _get_tones()
    if step == "topic":
        switch_label = "Switch: Tweet" if mode == "thread" else "Switch: Thread"
        rows = [["/start"], [switch_label, "Switch: Reply"], ["Length: short", "Length: medium", "Length: long", "Length: auto"]]
    elif step == "context":
        rows = [["Skip", "/start"]]
    elif step == "n":
        rows = [["5", "6", "8", "10"], ["Skip", "/start"]]
    elif step == "tone":
        mid = (len(tones) + 1) // 2
        rows = [tones[:mid], tones[mid:], ["Skip", "/start"]]
    elif step == "tags":
        rows = [["Use default", "No tags"], ["Skip", "/start"], ["Generate now", "Back"]]
    elif step == "reply_ctx":
        rows = [["/start"], ["Length: short", "Length: medium", "Length: long", "Length: auto"]]
    elif step == "length_pick":
        rows = [["Length: short", "Length: medium", "Length: long", "Length: auto"], ["Generate now", "Back"], ["/start"]]
    else:
        rows = [["🧵 New Thread", "📝 New Tweet"], ["🗨️ Reply"], ["❓ Help"], ["⬇️ Hide keyboard"]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def thread_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    
    # Rate limit check for generation
    if not _check_rate_limit(uid, update, is_generation=True):
        return
    
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    brief = parts[1].strip() if len(parts) > 1 else ""
    if not brief:
        update.message.reply_text("Please provide a topic after /thread or use the interactive keyboard.")
        return

    toks = brief.split()
    args = {k.split("=", 1)[0]: k.split("=", 1)[1] for k in toks if "=" in k}
    n = int(args.get("n", "6")) if args.get("n", "6").isdigit() else 6
    tone = args.get("tone")
    hashtags = args.get("tags", "")
    topic = " ".join(t for t in toks if "=" not in t).strip()

    loading_msg = None
    try:
        try:
            context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        except Exception:
            pass
        loading_msg = update.message.reply_text("Generating thread… ⏳")
        posts = generate_thread(topic=topic, n_posts=n, tone=tone, hashtags=hashtags, instructions="", length="medium")
        # Record successful generation for rate limiting
        record_user_action(uid, is_generation=True)
    except Exception as e:
        try:
            if loading_msg:
                context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
        except Exception:
            pass
        update.message.reply_text(f"Failed to generate: {_friendly_error(e)}")
        return
    finally:
        try:
            if loading_msg:
                context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
        except Exception:
            pass

    sess = _sess(uid)
    sess.update({
        "mode": "thread",
        "topic": topic,
        "n": n,
        "tone": tone or sess.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise')),
        "hashtags": hashtags,
        "posts": posts,
    })
    if getattr(_cfg, 'THREAD_SPLIT_SEND', False):
        _send_thread_preview(context, update.effective_chat.id, sess)
    else:
        update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))


def _thread_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    if not q or not q.data:
        return
    uid = str(q.from_user.id)
    sess = _sess(uid)
    data = q.data.split("|")
    if data[0] != "thr":
        return
    # Acknowledge early to avoid 'query is too old' errors on long operations
    try:
        q.answer()
    except Exception:
        pass
    act = data[1]
    if act == "noop":
        q.answer(); return
    if act == "close":
        try:
            q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        q.answer("Closed"); return
    if act == "n":
        max_posts = getattr(_cfg, 'MAX_THREAD_POSTS', 25)
        min_posts = getattr(_cfg, 'MIN_THREAD_POSTS', 2)
        default_n = getattr(_cfg, 'DEFAULT_THREAD_N', 6)
        if len(data) > 2 and data[2] == "inc":
            sess["n"] = min(max_posts, int(sess.get("n", default_n)) + 1)
        elif len(data) > 2 and data[2] == "dec":
            sess["n"] = max(min_posts, int(sess.get("n", default_n)) - 1)
    elif act == "tone":
        tones = _get_tones()
        cur = sess.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        try:
            idx = (tones.index(cur) + 1) % len(tones)
        except ValueError:
            idx = 0
        sess["tone"] = tones[idx]
    elif act == "length":
        order = ["short", "medium", "long", "auto"]
        cur = (sess.get("length", "medium") or "medium").lower()
        try:
            idx = (order.index(cur) + 1) % len(order)
        except ValueError:
            idx = 1
        sess["length"] = order[idx]
        # Do not auto-regenerate; user must confirm via 🔁 Regenerate
        try:
            q.answer(f"Length set to {order[idx]}")
        except Exception:
            pass
    elif act == "tags":
        sub = data[2] if len(data) > 2 else "toggle"
        if sub == "toggle":
            sess["hashtags"] = "" if sess.get("hashtags") else getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip()
        elif sub == "suggest":
            topic = sess.get("topic", "")
            posts = sess.get("posts", []) or []
            try:
                suggestions = suggest_hashtags(topic, posts, limit=5)
            except Exception:
                suggestions = []
            if suggestions:
                sess["hashtags"] = " ".join(suggestions)
                q.answer("Tags suggested")
            else:
                q.answer("No suggestions", show_alert=True)
                try:
                    q.edit_message_text(_build_preview(sess), reply_markup=_kb(sess))
                except Exception:
                    context.bot.send_message(chat_id=q.message.chat_id, text=_build_preview(sess), reply_markup=_kb(sess))
                return
    elif act == "climit":
        # Cycle character limit per-session (avoids race condition with global config)
        cur = sess.get("char_limit", getattr(_cfg, 'TWEET_CHAR_LIMIT', 280))
        new_val = _next_char_limit(cur)
        sess["char_limit"] = new_val
        try:
            q.answer(f"Max chars set: {new_val}")
        except Exception:
            pass
    elif act == "style":
        which = data[2] if len(data) > 2 else ""
        key_map = {
            "cta": "style_cta",
            "noemoji": "style_noemoji",
            "bullets": "style_bullets",
            "stats": "style_stats",
        }
        key = key_map.get(which)
        if key:
            sess[key] = not bool(sess.get(key))
            try:
                q.answer(f"{which} {'ON' if sess[key] else 'OFF'}")
            except Exception:
                pass
    elif act == "voice":
        # Cycle through saved voices (and 'none')
        try:
            voices = [v.get("name") for v in (list_voices(uid) or [])]
        except Exception:
            voices = []
        order = [None] + voices
        cur = sess.get("voice")
        try:
            idx = (order.index(cur) + 1) % len(order)
        except ValueError:
            idx = 0
        sess["voice"] = order[idx]
        try:
            q.answer(f"Voice set to {sess['voice'] or 'none'}")
        except Exception:
            pass
    elif act == "save":
        import io, json
        payload = {
            "topic": sess.get("topic"),
            "n_posts": int(sess.get("n", 6)),
            "tone": sess.get("tone"),
            "hashtags": sess.get("hashtags", ""),
            "mode": sess.get("mode", "thread"),
            "length": sess.get("length", "medium"),
            "instructions": sess.get("instructions", ""),
            "posts": sess.get("posts", []),
        }
        buf = io.BytesIO(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        buf.name = "thread.json"
        try:
            context.bot.send_document(chat_id=q.message.chat.id, document=buf, filename="thread.json")
        except Exception:
            context.bot.send_document(chat_id=q.message.chat_id, document=buf, filename="thread.json")
        q.answer("Saved"); return
    elif act == "copy":
        import io
        posts = sess.get("posts", []) or []
        if not posts:
            q.answer("No content to copy", show_alert=True)
            return
        raw = "\n".join(posts)
        if len(raw) <= 4000:
            try:
                context.bot.send_message(chat_id=q.message.chat.id, text=raw)
            except Exception:
                context.bot.send_message(chat_id=q.message.chat_id, text=raw)
        else:
            buf = io.BytesIO(raw.encode("utf-8"))
            buf.name = "thread.txt"
            try:
                context.bot.send_document(chat_id=q.message.chat.id, document=buf, filename="thread.txt")
            except Exception:
                context.bot.send_document(chat_id=q.message.chat_id, document=buf, filename="thread.txt")
        q.answer("Ready to copy"); return
    elif act == "edit":
        sess["edit_mode"] = True
        msg = (
            "Edit mode: send 'N: new text' to update a line (e.g., 3: Shorten this).\n"
            "Send 'done' to finish or 'cancel' to exit."
        )
        try:
            context.bot.send_message(chat_id=q.message.chat.id, text=msg)
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text=msg)
        q.answer("Edit mode on"); return
    elif act == "regen":
        # Rate limit check for regeneration
        if not _check_rate_limit_callback(uid, q, is_generation=True):
            return
        
        loading_msg = None
        try:
            try:
                context.bot.send_chat_action(chat_id=q.message.chat.id, action=ChatAction.TYPING)
            except Exception:
                pass
            loading_msg = context.bot.send_message(chat_id=q.message.chat.id, text="Regenerating… ⏳")
            mode = sess.get("mode", "thread")
            _audit(uid, "regen_submit", mode=mode)
            instr = (sess.get("instructions", "") or "").strip()
            hints = []
            if sess.get("style_cta"): hints.append("Include a clear call-to-action.")
            if sess.get("style_noemoji"): hints.append("Avoid emojis.")
            if sess.get("style_bullets"): hints.append("Use concise bullet points when possible.")
            if sess.get("style_stats"): hints.append("Include a specific stat or number if relevant.")
            vprompt = None
            try:
                if sess.get("voice"):
                    for v in (list_voices(uid) or []):
                        if v.get("name") == sess["voice"]:
                            vprompt = v.get("prompt")
                            break
            except Exception:
                vprompt = None
            extra = "\n".join(hints + ([f"Voice profile: {vprompt}"] if vprompt else []))
            final_instructions = (instr + ("\n" + extra if extra else "")).strip()
            if mode == "tweet":
                out = generate_tweet(
                    topic=(sess.get("topic", "") + (f"\nGuidance: {final_instructions}" if final_instructions else "")),
                    tone=sess.get("tone"),
                    length=sess.get("length", "medium"),
                    hashtags="",
                )
                sess["posts"] = [out] if out else []
            elif mode == "reply":
                out = generate_reply(
                    context_text=(sess.get("reply_ctx", "") or ""),
                    tone=sess.get("tone"),
                    length=sess.get("length", "medium"),
                    instructions=final_instructions,
                )
                sess["posts"] = [out] if out else []
            else:
                sess["posts"] = generate_thread(
                    topic=sess.get("topic", ""),
                    n_posts=int(sess.get("n", 6)),
                    tone=sess.get("tone"),
                    hashtags=sess.get("hashtags", ""),
                    instructions=final_instructions,
                    length=sess.get("length", "medium"),
                    offset=0,
                )
            # Record successful generation for rate limiting
            record_user_action(uid, is_generation=True)
            _audit(uid, "regen_done", ok=bool(sess.get("posts")), count=len(sess.get("posts", [])))
            # If split send is enabled for threads, push a fresh preview instead of editing original message
            if mode == 'thread' and getattr(_cfg, 'THREAD_SPLIT_SEND', False):
                _send_thread_preview(context, q.message.chat.id, sess)
                return
        except Exception as e:
            try:
                if loading_msg:
                    context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
            except Exception:
                pass
            q.answer(f"Failed: {_friendly_error(e)}", show_alert=True)
            return
        finally:
            try:
                if loading_msg:
                    context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
            except Exception:
                pass
    elif act == "cont":
        # Rate limit check for continue generation
        if not _check_rate_limit_callback(uid, q, is_generation=True):
            return
        
        # Continue thread: generate next batch using offset = current length
        try:
            existing = sess.get("posts", []) or []
            batch = int(getattr(_cfg, 'THREAD_CONTINUE_BATCH', 3))
            instr = (sess.get("instructions", "") or "").strip()
            new_posts = generate_thread(
                topic=sess.get("topic", ""),
                n_posts=batch,
                tone=sess.get("tone"),
                hashtags="",  # hashtags only at the end of final manual regen
                instructions=instr,
                length=sess.get("length", "medium"),
                offset=len(existing),
            )
            sess["posts"] = existing + new_posts
            # Record successful generation for rate limiting
            record_user_action(uid, is_generation=True)
            q.answer(f"Added {len(new_posts)} posts")
            if getattr(_cfg, 'THREAD_SPLIT_SEND', False):
                _send_thread_preview(context, q.message.chat.id, sess)
                return
        except Exception as e:
            q.answer(f"Fail: {_friendly_error(e)}", show_alert=True)
            return
    elif act == "rline":
        posts = sess.get("posts", []) or []
        if not posts:
            q.answer("No posts yet", show_alert=True)
            return
        sess["regen_line_mode"] = True
        msg = f"Send a line number 1-{len(posts)} to regenerate that line (or 'cancel')."
        try:
            context.bot.send_message(chat_id=q.message.chat.id, text=msg)
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text=msg)
        q.answer("Choose a line")
        return

    # Save to history if we have posts
    try:
        posts = sess.get("posts", []) or []
        if posts:
            payload = {
                "mode": sess.get("mode"),
                "topic": sess.get("topic", ""),
                "reply_ctx": sess.get("reply_ctx", ""),
                "posts": posts,
            }
            save_history(uid, sess.get("mode","thread"), sess.get("tone"), sess.get("length","medium"), sess.get("hashtags",""), json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass

    try:
        if getattr(_cfg, 'THREAD_SPLIT_SEND', False) and sess.get('mode') == 'thread':
            # Already sent via split preview paths
            pass
        else:
            q.edit_message_text(_build_preview(sess), reply_markup=_kb(sess))
    except Exception:
        if not (getattr(_cfg, 'THREAD_SPLIT_SEND', False) and sess.get('mode') == 'thread'):
            context.bot.send_message(chat_id=q.message.chat_id, text=_build_preview(sess), reply_markup=_kb(sess))
    # Answer again (safe-guarded); ignore if already answered or expired
    try:
        q.answer()
    except Exception:
        pass
    return


def start_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    sess = _sess(uid)
    sess['_uid'] = uid
    _audit(uid, "cmd_start")
    # Send a clean welcome + getting started message with the reply keyboard; no inline buttons
    try:
        update.message.reply_text(_build_start_text(), reply_markup=_reply_kb(sess))
    except Exception:
        update.message.reply_text("Welcome. Use the keyboard below to begin.", reply_markup=_reply_kb(sess))

def help_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    sess = _sess(uid)
    sess['_uid'] = uid
    update.message.reply_text(_build_help_text(), reply_markup=_reply_kb(sess))
    _audit(uid, "cmd_help")

def history_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    items = get_recent_history(uid, limit=3)
    if not items:
        update.message.reply_text("No recent drafts.")
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"Open #{it['id']} • {it['mode']} • {it['tone']}/{it['length']}", callback_data=f"cmd|openhist|{it['id']}")] for it in items])
    update.message.reply_text("Recent drafts:", reply_markup=kb)
    return

# /diag command removed for a cleaner UX


def _settings_kb(sess: dict | None = None) -> ReplyKeyboardMarkup:
    tones = _get_tones()
    rows = [
        ["Done", "Cancel"],
        tones[: (len(tones)+1)//2],
        tones[(len(tones)+1)//2 :],
        ["Length: short", "Length: medium", "Length: long", "Length: auto"],
        ["2", "3", "5", "6", "8", "10"],
        ["Use default tags", "No tags"],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def settings_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    sess = _sess(uid)
    sess["settings_mode"] = True
    d = sess.get("defaults", {})
    _audit(uid, "settings_open")
    msg = (
        "Settings (defaults):\n"
        f"- Tone: {d.get('tone', getattr(_cfg, 'DEFAULT_TONE', 'concise'))}\n"
        f"- Length: {d.get('length', getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))}\n"
        f"- N (thread): {d.get('n', getattr(_cfg, 'DEFAULT_THREAD_N', 6))}\n"
        f"- Tags: {d.get('hashtags','') or '(none)'}\n\n"
        "Pick a tone, set Length: <value>, send a number for N (2–25), or type tags.\n"
        "Tap Done to save."
    )
    update.message.reply_text(msg, reply_markup=_settings_kb(sess))
    return


def _build_help_text() -> str:
    default_tone = getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
    default_tags = getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip() or "(none)"

    return (
        "Help\n"
        "Quick start:\n"
        "• 🧵 New Thread → enter topic → (optional) guidance → choose N (2–25) → pick tone → set hashtags → preview.\n"
        "• 📝 New Tweet → enter topic → (optional) guidance → pick tone → preview.\n"
        "• 🗨️ Reply → paste the tweet text or an X link → (optional) guidance → choose Length → pick Tone → Generate now.\n\n"
        "After generation, use inline controls:\n"
        "• 🔁 Regenerate • ➖/➕ N • Tone • Length • Tags • ✏️ Edit • ↻ Line • 🏷 Suggest • 💾 Save.\n\n"
        f"Defaults: /settings (tone={default_tone}, tags={default_tags}).\n"
    )


def _build_start_text() -> str:
    default_tone = getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
    return (
    "Welcome to the Tweet/Thread Generator\n\n"
    "Getting started:\n"
    "- 🧵 New Thread: draft a thread.\n"
    "- 📝 New Tweet: draft a single tweet.\n"
    "- 🗨️ Reply: reply to an X link or pasted tweet text.\n\n"
    f"Tip: set your defaults in /settings (tone={default_tone})."
    )


def _cmd_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    if not q or not q.data:
        return
    data = q.data.split("|")
    if data[0] != "cmd":
        return
    act = data[1]
    uid = str(q.from_user.id)
    sess = _sess(uid)
    if act == "help":
        try:
            q.edit_message_text(_build_help_text(), reply_markup=None)
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text=_build_help_text())
        q.answer(); return
    if act == "history":
        items = get_recent_history(uid, limit=3)
        if not items:
            txt = "No recent drafts."
            try:
                q.edit_message_text(txt, reply_markup=None)
            except Exception:
                context.bot.send_message(chat_id=q.message.chat_id, text=txt)
            q.answer(); return
        buttons = []
        for it in items:
            title = f"#{it['id']} • {it['mode']} • {it['tone']}/{it['length']}"
            buttons.append([InlineKeyboardButton(title, callback_data=f"cmd|openhist|{it['id']}")])
        try:
            q.edit_message_text("Recent drafts:", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text="Recent drafts:", reply_markup=InlineKeyboardMarkup(buttons))
        q.answer(); return
    if act == "openhist" and len(data) > 2:
        try:
            hid = int(data[2])
        except Exception:
            q.answer("Bad id", show_alert=True); return
        row = get_history_by_id(uid, hid)
        if not row:
            q.answer("Not found", show_alert=True); return
        try:
            payload = json.loads(row.get("payload") or "{}")
        except Exception:
            payload = {}
        sess = _sess(uid)
        sess.update({
            "mode": payload.get("mode", row.get("mode")),
            "topic": payload.get("topic", ""),
            "reply_ctx": payload.get("reply_ctx", ""),
            "tone": row.get("tone") or sess.get("tone"),
            "length": row.get("length") or sess.get("length"),
            "hashtags": row.get("hashtags") or sess.get("hashtags"),
            "posts": payload.get("posts", []),
        })
        sess['_uid'] = uid
        try:
            q.edit_message_text(_build_preview(sess), reply_markup=_kb(sess))
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text=_build_preview(sess), reply_markup=_kb(sess))
        q.answer(); return
    if act == "newtweet":
        sess.clear(); sess['_uid'] = uid
        sess["wizard_step"] = "topic"; sess["mode"] = "tweet"
        d = _sess(uid).get("defaults", {})
        sess["tone"] = d.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        sess["length"] = d.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
        try:
            q.edit_message_text("Send a topic for your tweet.")
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text="Send a topic for your tweet.")
        try:
            context.bot.send_message(chat_id=q.message.chat.id, text="Topic:", reply_markup=ForceReply(selective=True))
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text="Topic:", reply_markup=ForceReply(selective=True))
        q.answer(); return
    if act == "reply":
        sess.clear(); sess['_uid'] = uid
        sess["wizard_step"] = "reply_ctx"; sess["mode"] = "reply"
        d = _sess(uid).get("defaults", {})
        sess["tone"] = d.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        sess["length"] = d.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
        try:
            q.edit_message_text("Send the X post text (or paste link and provide the text).")
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text="Send the X post text (or paste link and provide the text).")
        # Open a ForceReply prompt so the next message is captured correctly (avoids lingering 'Topic:' prompts)
        try:
            context.bot.send_message(chat_id=q.message.chat.id, text="Post text:", reply_markup=ForceReply(selective=True))
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text="Post text:", reply_markup=ForceReply(selective=True))
        q.answer(); return
    if act == "newthread":
        sess.clear()
        sess["wizard_step"] = "topic"
        prompt = "Send a topic for your thread (just text)."
        try:
            q.edit_message_text(prompt)
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text=prompt)
        try:
            context.bot.send_message(chat_id=q.message.chat.id, text="Topic:", reply_markup=ForceReply(selective=True))
        except Exception:
            context.bot.send_message(chat_id=q.message.chat_id, text="Topic:", reply_markup=ForceReply(selective=True))
        q.answer(); return


def handle_text_input(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    sess = _sess(uid)
    text = (update.message.text or "").strip()

    if text == "/settings" or text.lower() == "settings":
        return settings_command(update, context)

    if sess.get("settings_mode"):
        d = sess.setdefault("defaults", {
            "tone": getattr(_cfg, 'DEFAULT_TONE', 'concise'),
            "length": getattr(_cfg, 'DEFAULT_LENGTH', 'medium'),
            "n": getattr(_cfg, 'DEFAULT_THREAD_N', 6),
            "hashtags": getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip(),
        })
        low = text.lower()
        tones = _get_tones()
        if low in ("done", "exit", "cancel", "back"):
            sess.pop("settings_mode", None)
            # Persist user defaults
            try:
                save_user_defaults(uid, d)
            except Exception:
                pass
            update.message.reply_text("Settings saved.", reply_markup=_reply_kb(sess))
            _audit(uid, "settings_saved", tone=d.get("tone"), length=d.get("length"), n=d.get("n"), tags=bool(d.get("hashtags")))
            return
        if text in tones:
            d["tone"] = text
            try:
                save_user_defaults(uid, d)
            except Exception:
                pass
            update.message.reply_text(f"Default tone set to {text}.", reply_markup=_settings_kb(sess))
            _audit(uid, "settings_tone", value=text)
            return
        if low.startswith("length:"):
            val = text.split(":",1)[1].strip().lower()
            if val in ("short", "medium", "long", "auto"):
                d["length"] = val
                try:
                    save_user_defaults(uid, d)
                except Exception:
                    pass
                update.message.reply_text(f"Default length set to {val}.", reply_markup=_settings_kb(sess))
                _audit(uid, "settings_length", value=val)
                return
        if text.isdigit():
            v = int(text)
            min_n = getattr(_cfg, 'MIN_THREAD_POSTS', 2)
            max_n = getattr(_cfg, 'MAX_THREAD_POSTS', 25)
            if min_n <= v <= max_n:
                d["n"] = v
                try:
                    save_user_defaults(uid, d)
                except Exception:
                    pass
                update.message.reply_text(f"Default N set to {v}.", reply_markup=_settings_kb(sess))
                _audit(uid, "settings_n", value=v)
                return
        if low in ("use default tags", "use default"):
            d["hashtags"] = getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip()
            try:
                save_user_defaults(uid, d)
            except Exception:
                pass
            update.message.reply_text("Default tags set to env default.", reply_markup=_settings_kb(sess))
            _audit(uid, "settings_tags_default")
            return
        if low in ("no tags", "clear tags"):
            d["hashtags"] = ""
            try:
                save_user_defaults(uid, d)
            except Exception:
                pass
            update.message.reply_text("Default tags cleared.", reply_markup=_settings_kb(sess))
            _audit(uid, "settings_tags_cleared")
            return
        if "#" in text:
            d["hashtags"] = text.strip()
            try:
                save_user_defaults(uid, d)
            except Exception:
                pass
            update.message.reply_text("Default tags updated.", reply_markup=_settings_kb(sess))
            _audit(uid, "settings_tags_set", value=text.strip())
            return
        min_n = getattr(_cfg, 'MIN_THREAD_POSTS', 2)
        max_n = getattr(_cfg, 'MAX_THREAD_POSTS', 25)
        update.message.reply_text(f"Pick a tone, Length: <value>, a number for N ({min_n}-{max_n}), or type tags with #.", reply_markup=_settings_kb(sess))
        return

    if sess.get("regen_line_mode"):
        if text.lower() in ("cancel", "done", "exit"):
            sess.pop("regen_line_mode", None)
            update.message.reply_text("Canceled line regenerate.", reply_markup=_reply_kb(sess))
            return
        if text.isdigit():
            idx = int(text)
            posts = sess.get("posts", []) or []
            if not posts:
                sess.pop("regen_line_mode", None)
                update.message.reply_text("No posts to regenerate.", reply_markup=_reply_kb(sess))
                return
            if not (1 <= idx <= len(posts)):
                update.message.reply_text(f"Pick a number between 1 and {len(posts)} or 'cancel'.", reply_markup=_reply_kb(sess))
                return
            try:
                try:
                    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                except Exception:
                    pass
                topic = sess.get("topic", "")
                tone = sess.get("tone")
                length = sess.get("length", "medium")
                instructions = sess.get("instructions", "")
                guide = ("Guidance: Single line for a thread; no numbering; continue same topic.\n" + instructions).strip()
                new_line = generate_tweet(topic=f"{topic}\n{guide}", tone=tone, length=length, hashtags="")
            except Exception as e:
                sess.pop("regen_line_mode", None)
                update.message.reply_text(f"Failed to regenerate: {_friendly_error(e)}", reply_markup=_reply_kb(sess))
                return
            if new_line:
                posts[idx-1] = new_line
                sess["posts"] = posts
                sess.pop("regen_line_mode", None)
                update.message.reply_text(f"Regenerated line {idx}.", reply_markup=_reply_kb(sess))
                update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
                return
            else:
                update.message.reply_text("No content returned. Try again or 'cancel'.", reply_markup=_reply_kb(sess))
                return

    # Global cancel (highest priority when wizard active)
    if (text.lower() == "cancel" or text == "/start") and sess.get("wizard_step"):
        sess.clear()
        update.message.reply_text("Session reset.", reply_markup=_reply_kb(sess))
        return

    if text in ("❓ Help", "Help"):
        update.message.reply_text(_build_help_text(), reply_markup=_reply_kb(sess))
        return
    if text in ("🧵 New Thread", "New Thread"):
        sess.clear()
        sess["wizard_step"] = "topic"
        sess["mode"] = "thread"
        d = _sess(uid).get("defaults", {})
        sess["tone"] = d.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        sess["length"] = d.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
        sess["n"] = int(d.get("n", getattr(_cfg, 'DEFAULT_THREAD_N', 6)))
        sess["hashtags"] = d.get("hashtags", getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip())
        update.message.reply_text("Send a topic for your thread (just text).", reply_markup=_reply_kb(sess))
        update.message.reply_text("Topic:", reply_markup=ForceReply(selective=True))
        _audit(uid, "wizard_thread_start")
        return
    if text in ("📝 New Tweet", "New Tweet"):
        sess.clear()
        sess["wizard_step"] = "topic"
        sess["mode"] = "tweet"
        d = _sess(uid).get("defaults", {})
        sess["tone"] = d.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        sess["length"] = d.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
        update.message.reply_text("Send a topic for your tweet (just text).", reply_markup=_reply_kb(sess))
        update.message.reply_text("Topic:", reply_markup=ForceReply(selective=True))
        _audit(uid, "wizard_tweet_start")
        return
    if text in ("🗨️ Reply", "Reply"):
        sess.clear()
        sess["wizard_step"] = "reply_ctx"
        sess["mode"] = "reply"
        d = _sess(uid).get("defaults", {})
        sess["tone"] = d.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        sess["length"] = d.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
        update.message.reply_text("Send the X post text (or paste a link).", reply_markup=_reply_kb(sess))
        update.message.reply_text("Paste here:", reply_markup=ForceReply(selective=True))
        _audit(uid, "wizard_reply_start")
        return
    if text.startswith("Length:"):
        sess["length"] = text.split(":",1)[1].strip()
        # In reply pre-generation step, advance to tone selection
        if sess.get("wizard_step") == "length_pick":
            sess["wizard_step"] = "tone"
            update.message.reply_text(
                f"Pick a tone (default {getattr(_cfg, 'DEFAULT_TONE', 'concise')}).",
                reply_markup=_reply_kb(sess)
            )
        else:
            update.message.reply_text(f"Length set to {sess['length']}.", reply_markup=_reply_kb(sess))
        return
    if text == "Switch: Tweet" and sess.get("wizard_step") == "topic":
        sess["mode"] = "tweet"
        update.message.reply_text("Switched to Tweet mode.", reply_markup=_reply_kb(sess))
        return
    if text == "Switch: Thread" and sess.get("wizard_step") == "topic":
        sess["mode"] = "thread"
        update.message.reply_text("Switched to Thread mode.", reply_markup=_reply_kb(sess))
        return
    if text == "Switch: Reply" and sess.get("wizard_step") == "topic":
        sess.clear()
        sess["wizard_step"] = "reply_ctx"
        sess["mode"] = "reply"
        sess["length"] = sess.get("length", "medium")
        update.message.reply_text("Send the X post text (or paste a link).", reply_markup=_reply_kb(sess))
        update.message.reply_text("Paste here:", reply_markup=ForceReply(selective=True))
        return
    if text in ("⬇️ Hide keyboard", "Hide keyboard"):
        update.message.reply_text("Keyboard hidden. Use /start to show it again.", reply_markup=ReplyKeyboardRemove(selective=False))
        return

    # Smart intercept: if user pastes an X/Twitter status link at any time, switch to Reply flow
    try:
        x_link = re.search(r"https?://(www\.)?(x\.com|twitter\.com)/[^/]+/status/\d+", text, flags=re.I)
    except Exception:
        x_link = None
    if x_link:
        try:
            try:
                context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            except Exception:
                pass
            data = fetch_x_tweet_json_from_text(text)
        except Exception:
            data = None
        ctx_txt = None
        if data:
            try:
                ctx_txt = build_reply_context_from_x(data, source_url=text)
            except Exception:
                ctx_txt = None
        if ctx_txt is None:
            # Fallback: minimal formatted context from URL
            try:
                ctx_txt = build_basic_context_from_url(text)
            except Exception:
                ctx_txt = text
        # Reset and enter reply wizard at length pick
        sess.clear()
        sess["mode"] = "reply"
        d = _sess(uid).get("defaults", {})
        sess["tone"] = d.get("tone", getattr(_cfg, 'DEFAULT_TONE', 'concise'))
        sess["length"] = d.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
        sess["reply_ctx"] = ctx_txt
        sess["wizard_step"] = "length_pick"
        _audit(uid, "reply_context_parsed", has=bool(data))
        update.message.reply_text(
            "Choose Length, then pick a Tone. Tap 'Generate now' to preview.",
            reply_markup=_reply_kb(sess)
        )
        return

    # (Legacy cancel block removed; handled at top)

    if sess.get("edit_mode"):
        lower = text.lower()
        if lower in ("done", "finish", "exit", "cancel"):
            sess.pop("edit_mode", None)
            update.message.reply_text("Edit mode ended.", reply_markup=_reply_kb(sess))
            if sess.get("posts"):
                update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
            return
        m = re.match(r"^(\d{1,2})\s*:\s*(.+)$", text, flags=re.S)
        posts = sess.get("posts", []) or []
        if not m:
            update.message.reply_text("Send 'N: new text' (e.g., 2: New content) or 'done' to finish.")
            return
        idx = int(m.group(1))
        new_text = m.group(2).strip()
        if not posts:
            update.message.reply_text("No posts to edit.")
            return
        if idx < 1 or idx > len(posts):
            update.message.reply_text(f"Pick a number between 1 and {len(posts)}.")
            return
        # Sanitize manual edits: strip any hidden think blocks and enforce 280
        from .thread_gen import _strip_think  # local import to avoid cycles at module load
        cleaned = _strip_think(new_text)
        limit = getattr(_cfg, 'TWEET_CHAR_LIMIT', 280)
        trimmed = cleaned[:limit]
        note = f" (trimmed to {limit} chars)" if len(cleaned) > limit else ""
        posts[idx - 1] = trimmed
        sess["posts"] = posts
        update.message.reply_text(f"Updated line {idx}{note}.", reply_markup=_reply_kb(sess))
        update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
        return

    step = sess.get("wizard_step")
    if not step:
        return

    if step == "topic":
        topic = text
        if not topic:
            update.message.reply_text("Please provide a topic text.", reply_markup=_reply_kb(sess))
            return
        sess["topic"] = topic
        sess["wizard_step"] = "context"
        update.message.reply_text(
            "Add any guidance or key points (optional). E.g., audience, angle, must-include points. Or tap Skip.",
            reply_markup=_reply_kb(sess)
        )
        _audit(uid, "wizard_topic_ok", mode=sess.get("mode"))
        return
    if step == "context":
        if text.lower() == "skip":
            sess["instructions"] = ""
        else:
            sess["instructions"] = text
        if sess.get("mode") == "tweet":
            sess["wizard_step"] = "tone"
            update.message.reply_text(
                f"Pick a tone (default {getattr(_cfg, 'DEFAULT_TONE', 'concise')}).",
                reply_markup=_reply_kb(sess)
            )
        elif sess.get("mode") == "thread":
            sess["wizard_step"] = "n"
            update.message.reply_text(
                "How many posts should the thread include? Select 2–25 (default is 6).",
                reply_markup=_reply_kb(sess)
            )
        elif sess.get("mode") == "reply":
            sess["wizard_step"] = "length_pick"
            update.message.reply_text(
                "Choose Length, then pick a Tone. Tap 'Generate now' to preview.",
                reply_markup=_reply_kb(sess)
            )
        _audit(uid, "wizard_context_ok", mode=sess.get("mode"))
        return

    if step == "n":
        if text.lower() == "skip":
            sess["n"] = 6
        else:
            if text.isdigit():
                val = int(text)
                if 2 <= val <= 25:
                    sess["n"] = val
                else:
                    update.message.reply_text(
                        "Please choose a number between 2 and 25, or tap Skip.",
                        reply_markup=_reply_kb(sess)
                    )
                    return
            else:
                update.message.reply_text(
                    "Please enter a number between 2 and 25, or tap Skip.",
                    reply_markup=_reply_kb(sess)
                )
                return
        sess["wizard_step"] = "tone"
        default_tone = getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
        update.message.reply_text(
            f"Pick a tone (default {default_tone}) or type your own.", reply_markup=_reply_kb(sess)
        )
        return

    if step == "tone":
        if text.lower() == "skip":
            sess["tone"] = getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
        else:
            sess["tone"] = text
        if sess.get("mode") == "tweet":
            topic = sess.get("topic", "")
            tone = sess.get("tone") or getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
            length = sess.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
            # Build guidance from style/voice
            instr = (sess.get("instructions", "") or "").strip()
            hints = []
            if sess.get("style_cta"): hints.append("Include a clear call-to-action.")
            if sess.get("style_noemoji"): hints.append("Avoid emojis.")
            if sess.get("style_bullets"): hints.append("Use concise bullet points when possible.")
            if sess.get("style_stats"): hints.append("Include a specific stat or number if relevant.")
            vprompt = None
            try:
                if sess.get("voice"):
                    for v in (list_voices(uid) or []):
                        if v.get("name") == sess["voice"]:
                            vprompt = v.get("prompt")
                            break
            except Exception:
                vprompt = None
            extra = "\n".join(hints + ([f"Voice profile: {vprompt}"] if vprompt else []))
            instructions = (instr + ("\n" + extra if extra else "")).strip()
            loading_msg = None
            try:
                try:
                    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                except Exception:
                    pass
                loading_msg = update.message.reply_text("Generating tweet… ⏳")
                _audit(uid, "generate_tweet_submit", tone=tone, length=length)
                text_out = generate_tweet(topic=topic, tone=tone, length=length, hashtags="", )
                if instructions and not text_out:
                    text_out = generate_tweet(topic=f"{topic}\nGuidance: {instructions}", tone=tone, length=length, hashtags="")
            except Exception as e:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
                update.message.reply_text(f"Failed to generate: {_friendly_error(e)}")
                return
            finally:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
            sess["posts"] = [text_out] if text_out else []
            _audit(uid, "generate_tweet_done", ok=bool(text_out), chars=len(text_out or ""))
            try:
                if text_out:
                    payload = {"mode":"tweet","topic":topic,"posts":[text_out]}
                    save_history(uid, "tweet", tone, length, "", json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass
            sess.pop("wizard_step", None)
            update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
            return
        elif sess.get("mode") == "reply":
            # On first tone selection in reply flow, generate immediately
            tone = sess.get("tone") or getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
            length = sess.get("length", getattr(_cfg, 'DEFAULT_LENGTH', 'medium'))
            instr = (sess.get("instructions", "") or "").strip()
            hints = []
            if sess.get("style_cta"): hints.append("Include a clear call-to-action.")
            if sess.get("style_noemoji"): hints.append("Avoid emojis.")
            if sess.get("style_bullets"): hints.append("Use concise bullet points when possible.")
            if sess.get("style_stats"): hints.append("Include a specific stat or number if relevant.")
            vprompt = None
            try:
                if sess.get("voice"):
                    for v in (list_voices(uid) or []):
                        if v.get("name") == sess["voice"]:
                            vprompt = v.get("prompt")
                            break
            except Exception:
                vprompt = None
            extra = "\n".join(hints + ([f"Voice profile: {vprompt}"] if vprompt else []))
            instructions = (instr + ("\n" + extra if extra else "")).strip()
            ctx_text = (sess.get("reply_ctx", "") or "")
            loading_msg = None
            try:
                try:
                    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                except Exception:
                    pass
                loading_msg = update.message.reply_text("Generating reply… ⏳")
                _audit(uid, "generate_reply_submit", tone=tone, length=length)
                out = generate_reply(
                    context_text=ctx_text,
                    tone=tone,
                    length=length,
                    instructions=instructions,
                )
            except Exception as e:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
                update.message.reply_text(f"Failed to generate: {_friendly_error(e)}")
                return
            finally:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
            sess["posts"] = [out] if out else []
            _audit(uid, "generate_reply_done", ok=bool(out), chars=len(out or ""))
            try:
                if out:
                    payload = {"mode":"reply","reply_ctx":sess.get("reply_ctx",""),"posts":[out]}
                    save_history(uid, "reply", tone, length, sess.get("hashtags",""), json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass
            sess.pop("wizard_step", None)
            update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
            return
        # Thread flow continues to tags
        sess["wizard_step"] = "tags"
        default_tags = getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip() or "(none)"
        update.message.reply_text(
            f"Hashtags? Choose an option or type custom (e.g., #ai #dev). Default: {default_tags}",
            reply_markup=_reply_kb(sess)
        )
        return

    if step == "tags":
        choice = text.lower()
        if choice == "back":
            sess["wizard_step"] = "tone"
            update.message.reply_text(
                f"Pick a tone (default {getattr(_cfg, 'DEFAULT_TONE', 'concise')}).",
                reply_markup=_reply_kb(sess)
            )
            return
        if choice == "generate now":
            topic = sess.get("topic", "")
            n = int(sess.get("n", getattr(_cfg, 'DEFAULT_THREAD_N', 6)))
            tone = sess.get("tone") or getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
            hashtags = sess.get("hashtags", "")
            loading_msg = None
            try:
                try:
                    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                except Exception:
                    pass
                loading_msg = update.message.reply_text("Generating thread… ⏳")
                _audit(uid, "generate_thread_submit", n=n, tone=tone, length=sess.get("length","medium"), tags=bool(hashtags))
                posts = generate_thread(topic=topic, n_posts=n, tone=tone, hashtags=hashtags, instructions=sess.get("instructions",""), length=sess.get("length","medium"))
            except Exception as e:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
                update.message.reply_text(f"Failed to generate: {_friendly_error(e)}")
                return
            finally:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
            sess["posts"] = posts
            _audit(uid, "generate_thread_done", ok=bool(posts), count=len(posts))
            try:
                if posts:
                    payload = {"mode":"thread","topic":topic,"posts":posts}
                    save_history(uid, "thread", tone, sess.get("length","medium"), hashtags, json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass
            sess.pop("wizard_step", None)
            update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
            return
        if choice == "use default":
            sess["hashtags"] = getattr(_cfg, 'DEFAULT_HASHTAGS', '').strip()
        elif choice in ("no tags", "skip"):
            sess["hashtags"] = ""
        else:
            sess["hashtags"] = text

        topic = sess.get("topic", "")
        n = int(sess.get("n", getattr(_cfg, 'DEFAULT_THREAD_N', 6)))
        tone = sess.get("tone") or getattr(_cfg, 'DEFAULT_TONE', 'concise').strip()
        hashtags = sess.get("hashtags", "")
        loading_msg = None
        try:
            try:
                context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            except Exception:
                pass
            loading_msg = update.message.reply_text("Generating thread… ⏳")
            _audit(uid, "generate_thread_submit", n=n, tone=tone, length=sess.get("length","medium"), tags=bool(hashtags))
            posts = generate_thread(
                topic=topic,
                n_posts=n,
                tone=tone,
                hashtags=hashtags,
                instructions=sess.get("instructions",""),
                length=sess.get("length","medium"),
            )
        except Exception as e:
            try:
                if loading_msg:
                    context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
            except Exception:
                pass
            update.message.reply_text(f"Failed to generate: {_friendly_error(e)}")
            return
        finally:
            try:
                if loading_msg:
                    context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
            except Exception:
                pass
        sess["posts"] = posts
        _audit(uid, "generate_thread_done", ok=bool(posts), count=len(posts))
        try:
            if posts:
                payload = {"mode":"thread","topic":topic,"posts":posts}
                save_history(uid, "thread", tone, sess.get("length","medium"), hashtags, json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass
        sess.pop("wizard_step", None)
        update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
        return

    if step == "reply_ctx":
        ctx = text
        if not ctx:
            update.message.reply_text("Please provide the post text.", reply_markup=_reply_kb(sess))
            return
        # Always try to resolve tweet details from the provided text/URL
        try:
            try:
                context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            except Exception:
                pass
            data = fetch_x_tweet_json_from_text(ctx)
        except Exception:
            data = None
        if data:
            try:
                ctx = build_reply_context_from_x(data, source_url=text)
            except Exception:
                ctx = build_basic_context_from_url(text)
        elif re.search(r"https?://(www\.)?(x\.com|twitter\.com)/[^/]+/status/\d+", ctx, flags=re.I):
            # If it's a URL but fetch failed, still provide a basic context
            try:
                ctx = build_basic_context_from_url(ctx)
            except Exception:
                pass
        _audit(uid, "reply_context_parsed", has=bool(data))
        sess["mode"] = "reply"
        sess["reply_ctx"] = ctx
        sess["wizard_step"] = "length_pick"
        update.message.reply_text(
            "Choose Length, then pick a Tone. Tap 'Generate now' to preview.",
            reply_markup=_reply_kb(sess)
        )
        return

    if step == "length_pick":
        choice = text.lower()
        if choice == "back":
            # Go back to entering the reply context
            sess["wizard_step"] = "reply_ctx"
            update.message.reply_text("Send the X post text (or paste link and provide the text).", reply_markup=_reply_kb(sess))
            update.message.reply_text("Post text:", reply_markup=ForceReply(selective=True))
            return
        if choice == "generate now":
            # Generate reply immediately with current tone/length
            loading_msg = None
            try:
                try:
                    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                except Exception:
                    pass
                loading_msg = update.message.reply_text("Generating reply… ⏳")
                _audit(uid, "generate_reply_submit", tone=sess.get("tone"), length=sess.get("length"))
                out = generate_reply(
                    context_text=(sess.get("reply_ctx", "") or ""),
                    tone=sess.get("tone"),
                    length=sess.get("length", "medium"),
                    instructions=sess.get("instructions", ""),
                )
            except Exception as e:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
                update.message.reply_text(f"Failed to generate: {_friendly_error(e)}")
                return
            finally:
                try:
                    if loading_msg:
                        context.bot.delete_message(chat_id=loading_msg.chat_id, message_id=loading_msg.message_id)
                except Exception:
                    pass
            sess["posts"] = [out] if out else []
            _audit(uid, "generate_reply_done", ok=bool(out), chars=len(out or ""))
            sess.pop("wizard_step", None)
            update.message.reply_text(_build_preview(sess), reply_markup=_kb(sess))
            return
