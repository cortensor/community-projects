# src/telegram_bot.py
import hashlib
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ParseMode
from telegram.error import BadRequest

from . import config
from . import cortensor_api
from .cortensor_api import CortensorAPIError, CortensorNetworkError, CortensorResponseError

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

chat_histories = {}
MAX_HISTORY_TURNS = 5
chat_profiles = {}  # per-user lightweight memory (e.g., name)
last_user_prompt_by_chat = {}  # track latest user prompt per chat for filtering context
_client_reference_ids: dict = {}
_client_reference_lookup: dict = {}


def _resolve_reference_id(chat_id: int) -> str:
    """Return a deterministic, random-looking ID for the given chat."""
    if chat_id in _client_reference_ids:
        return _client_reference_ids[chat_id]
    salt = getattr(config, "CLIENT_REFERENCE_SALT", "") or ""
    digest = hashlib.sha256(f"{salt}:{chat_id}".encode("utf-8")).hexdigest()[:10]
    _client_reference_ids[chat_id] = digest
    return digest


def _register_client_reference(chat_id: int, reference: str) -> None:
    """Store a reverse lookup so async callbacks can resolve the chat."""
    _client_reference_lookup[reference] = chat_id


def resolve_chat_id_from_reference(reference: str) -> int | None:
    """Resolve a previously issued client_reference back to its chat_id."""
    return _client_reference_lookup.get(reference)


def _build_client_reference(chat_id: int) -> str:
    """Format the client_reference value using the configured template."""
    template = getattr(config, "CORTENSOR_CLIENT_REFERENCE_TEMPLATE", "") or ""
    resolved_id = _resolve_reference_id(chat_id)
    if "(ID)" in template:
        reference = template.replace("(ID)", resolved_id)
        _register_client_reference(chat_id, reference)
        return reference
    if "{id}" in template:
        try:
            reference = template.format(id=resolved_id)
            _register_client_reference(chat_id, reference)
            return reference
        except Exception:
            pass
    if getattr(config, "USE_CHAT_ID_AS_CLIENT_REFERENCE", True):
        if template:
            reference = f"{template}{resolved_id}"
            _register_client_reference(chat_id, reference)
            return reference
        reference = resolved_id
        _register_client_reference(chat_id, reference)
        return reference
    reference = template or resolved_id
    _register_client_reference(chat_id, reference)
    return reference

def start_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_histories[user_id] = []
    display_reference = _build_client_reference(chat_id)
    display_id = _resolve_reference_id(chat_id)
    update.message.reply_text(
        "Hello, my name is Eliza.\n"
        f"Your User ID is {display_id}, and I am ready to assist you."
    )

def handle_message(update: Update, context: CallbackContext):
    user_prompt = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in chat_histories:
        chat_histories[user_id] = []
    
    history = chat_histories.get(user_id, [])
    # Remember latest user prompt per chat for downstream filter
    try:
        last_user_prompt_by_chat[chat_id] = user_prompt or ""
    except Exception:
        pass
    
    # Simple inline name capture and recall before invoking the model
    text_l = (user_prompt or "").strip().lower()
    # capture: "namaku X" or "nama saya X"
    import re
    m = re.search(r"\b(namaku|nama\s+saya)\s+([a-zA-Z0-9_\- ]{2,40})$", text_l)
    if m:
        name = m.group(2).strip().title()
        chat_profiles[user_id] = chat_profiles.get(user_id, {})
        chat_profiles[user_id]["name"] = name
        try:
            return context.bot.send_message(chat_id=chat_id, text=f"Hai, {name}.")
        except Exception:
            return context.bot.send_message(chat_id=chat_id, text="Halo.")
    # recall: "apa kau tahu namaku" etc.
    if re.search(r"\btahu\s+namaku\b|do\s+you\s+know\s+my\s+name\b", text_l):
        prof = chat_profiles.get(user_id, {})
        if prof.get("name"):
            try:
                return context.bot.send_message(chat_id=chat_id, text=f"Namamu {prof['name']}.")
            except Exception:
                return context.bot.send_message(chat_id=chat_id, text=prof['name'])
        else:
            return context.bot.send_message(chat_id=chat_id, text="Kamu belum memberitahu namamu.")

    processing_message = context.bot.send_message(chat_id=chat_id, text="⏳ Eliza is thinking...")
    message_id_to_edit = processing_message.message_id

    # Log internal state (tidak dikirim ke user)
    try:
        logger.info(
            "[HANDLE] user=%s chat=%s turns=%d session=%s prompt_chars=%d", 
            user_id, chat_id, len(history)//2, config.CORTENSOR_SESSION_ID, len(user_prompt)
        )
        def progress_cb(event: dict):
            # event keys: event, kind, attempt, next_attempt, total_attempts, reason, sleep
            if event.get('event') == 'retry':
                attempt = event.get('attempt')
                total = event.get('total_attempts')
                reason = event.get('reason')
                sleep_for = event.get('sleep')
                try:
                    context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id_to_edit,
                        text=(
                            f"⏳ Still processing (retry {attempt}/{total}) due to {reason}. "
                            f"Next attempt in {sleep_for:.1f}s..."
                        )
                    )
                except Exception:
                    logger.debug("Failed to edit message for retry", exc_info=True)

        # Use default session from config (no per-user override) and always pass chat_id as client_reference
        answer = cortensor_api.get_completion(
            history=history,
            new_prompt=user_prompt,
            progress_cb=progress_cb,
            session_id=None,
            client_reference=_build_client_reference(chat_id),
        )
        
        if not answer:
            context.bot.edit_message_text(text="I'm sorry, I received an empty response.", chat_id=chat_id, message_id=message_id_to_edit)
            return

        chat_histories[user_id].extend([user_prompt, answer])
        if len(chat_histories[user_id]) > MAX_HISTORY_TURNS * 2:
            chat_histories[user_id] = chat_histories[user_id][-(MAX_HISTORY_TURNS * 2):]
            
    # --- Robust rendering logic ---
        try:
            # Try MarkdownV2 first
            context.bot.edit_message_text(
                text=answer,
                chat_id=chat_id,
                message_id=message_id_to_edit,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except BadRequest:
            try:
                # Fallback to HTML if MarkdownV2 fails
                logger.warning("MarkdownV2 parsing failed. Retrying with HTML parse mode.")
                context.bot.edit_message_text(
                    text=answer,
                    chat_id=chat_id,
                    message_id=message_id_to_edit,
                    parse_mode=ParseMode.HTML
                )
            except BadRequest:
                # Final fallback: plain text
                logger.warning("HTML parsing failed. Sending as plain text.")
                context.bot.edit_message_text(
                    text=answer,
                    chat_id=chat_id,
                    message_id=message_id_to_edit
                )
        
    except CortensorNetworkError as e:
        logger.error(f"Network error for user {user_id}: {e}")
        context.bot.edit_message_text(
            text="🚧 The AI service is currently unreachable. Please try again shortly.",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )
    except CortensorResponseError as e:
        logger.error(f"API response error for user {user_id}: {e}")
        context.bot.edit_message_text(
            text="⚠️ The service returned an unexpected response. Please rephrase or simplify your request.",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )
    except CortensorAPIError as e:
        logger.error(f"Generic API error for user {user_id}: {e}")
        context.bot.edit_message_text(
            text="❌ An internal AI processing error occurred. Please try again soon.",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        context.bot.edit_message_text(
            text="❌ An unexpected system error occurred. Please try again.",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )

# Ensure edit_message_text also passes through our filter (not just send_message)
try:
    import telegram
    from .response_filters import post_process_response
    from .config import BRIEF_BY_DEFAULT
    if hasattr(telegram.Bot, "edit_message_text"):
        _orig_edit_message_text = telegram.Bot.edit_message_text
        def _patched_edit_message_text(self, *args, **kwargs):
            try:
                text = kwargs.get("text")
                chat_id = kwargs.get("chat_id")
                if text is not None:
                    user_text = ""
                    try:
                        if chat_id is None and len(args) >= 1:
                            # Signature can be edit_message_text(chat_id=..., message_id=..., ...)
                            # but if passed positionally, first arg might be chat_id
                            chat_id = args[0]
                    except Exception:
                        pass
                    if chat_id is not None:
                        user_text = last_user_prompt_by_chat.get(chat_id, "")
                    filtered = post_process_response(user_text, str(text), brief_default=BRIEF_BY_DEFAULT)
                    kwargs["text"] = filtered
            except Exception:
                pass
            return _orig_edit_message_text(self, *args, **kwargs)
        telegram.Bot.edit_message_text = _patched_edit_message_text
except Exception:
    pass

# Inject concise, factual post-processing into outgoing Telegram replies
try:
    from .response_filters import post_process_response
    from .config import BRIEF_BY_DEFAULT
    # python-telegram-bot API
    try:
        import telegram
        # Patch Message.reply_text
        if hasattr(telegram, "Message") and hasattr(telegram.Message, "reply_text"):
            _orig_reply_text = telegram.Message.reply_text
            def _patched_reply_text(self, text, *args, **kwargs):
                try:
                    user_text = getattr(self, 'text', '') or ''
                    filtered = post_process_response(user_text, str(text), brief_default=BRIEF_BY_DEFAULT)
                    return _orig_reply_text(self, filtered, *args, **kwargs)
                except Exception:
                    return _orig_reply_text(self, text, *args, **kwargs)
            telegram.Message.reply_text = _patched_reply_text
        # Patch Bot.send_message
        if hasattr(telegram, "Bot") and hasattr(telegram.Bot, "send_message"):
            _orig_send_message = telegram.Bot.send_message
            def _patched_send_message(self, chat_id, text, *args, **kwargs):
                try:
                    # Use last user prompt for this chat to preserve requested list counts
                    user_text = last_user_prompt_by_chat.get(chat_id, "")
                    filtered = post_process_response(user_text, str(text), brief_default=BRIEF_BY_DEFAULT)
                    return _orig_send_message(self, chat_id, filtered, *args, **kwargs)
                except Exception:
                    return _orig_send_message(self, chat_id, text, *args, **kwargs)
            telegram.Bot.send_message = _patched_send_message
    except Exception:
        # If telegram is not available or different framework is used, no-op
        pass
except Exception:
    # If local filter/config import fails, no-op to avoid breaking runtime
    pass

def main():
    logger.info("Starting Eliza bot with the final, robust configuration...")
    # Log ringkas konfigurasi penting (tanpa API key untuk keamanan)
    logger.info(
        "Config summary: cortensor_url=%s session_id=%s", 
        config.CORTENSOR_API_URL, config.CORTENSOR_SESSION_ID
    )
    updater = Updater(token=config.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main()
