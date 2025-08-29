import logging
import re
import html as html_lib
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from .agents import AgentStyles, build_prompt
from .config import MODEL_PROVIDER_DEFAULT, MODEL_NAME_DEFAULT, FORCE_ENGLISH
from .state import get_style, set_style, reset_style, get_model, get_history, remember_turn
from .safety import (
    is_input_unsafe, is_output_safe, sanitize_output, safe_fallback_response,
    add_bad_word, remove_bad_word, list_custom_words, default_filter_summary,
)
from .parent import (
    require_parent,
    is_waiting as parent_is_waiting,
    handle_pin_input,
    prompt_verify_pin,
    prompt_set_pin,
    has_pin,
    set_pin_command as parent_set_pin_command,
    lock_parent as parent_lock,
    admin_reset_pin,
)
from .cortensor_api import request_completion

logger = logging.getLogger(__name__)

def submit_cortensor_task(update: Update, context: CallbackContext):
    user_prompt = update.message.text or ""
    chat_id = update.effective_chat.id
    logger.info(f"Submitting task for chat_id={chat_id}")

    # If waiting for PIN set/verify, treat this message as PIN input
    if parent_is_waiting(chat_id):
        handle_pin_input(update, context, user_prompt)
        return

    if is_input_unsafe(chat_id, user_prompt):
        update.message.reply_text("That’s not a safe topic. Let’s choose something fun and friendly like animals or space!")
        return

    style_id = get_style(chat_id)
    provider, model = get_model(chat_id)
    history = get_history(chat_id)
    prompt = build_prompt(style_id, user_prompt, history)

    # Brief typing indicator, then show a loading placeholder that will be edited to the final answer
    context.bot.send_chat_action(chat_id=chat_id, action='typing')
    loading_msg = update.message.reply_text("⏳ Thinking…")

    try:
        response_data = request_completion(prompt, provider, model)
        logger.debug(f"Received response: {response_data}")

        answer = response_data.get('choices', [{}])[0].get('text', '')

        # If the model leaked hidden reasoning, keep only the content after the last </think>
        if isinstance(answer, str) and "</think>" in answer:
            answer = answer.rsplit("</think>", 1)[-1]
        # Clean any residual think tags if present
        if isinstance(answer, str):
            answer = answer.replace("<think>", "").replace("</think>", "")
        if isinstance(answer, str) and "```bash" in answer and "print(" in answer:
            answer = answer.replace("```bash", "```python")

        # Very light language enforcement: if output seems non-English and FORCE_ENGLISH, simplify to English
        def seems_english(s: str) -> bool:
            if not s:
                return True
            letters = sum(ch.isalpha() for ch in s)
            ascii_letters = sum(('a' <= ch.lower() <= 'z') for ch in s)
            return ascii_letters >= max(10, int(0.6 * max(1, letters)))

        if FORCE_ENGLISH and not seems_english(answer):
            # Keep structure by cleaning line-by-line to preserve bullets and headings
            lines = (answer or "").splitlines()
            cleaned_lines = []
            for ln in lines:
                ascii_ln = ''.join(ch if ord(ch) < 128 else ' ' for ch in ln)
                ascii_ln = re.sub(r"\s+", " ", ascii_ln).strip()
                # Keep line if it still looks English after cleaning or is a bullet/header marker
                if ascii_ln.startswith(('- ', '* ', '1.', '2.', '3.', '4.', '5.')) or len(ascii_ln) >= 3:
                    cleaned_lines.append(ascii_ln)
            rebuilt = "\n".join(cleaned_lines).strip()
            answer = rebuilt if rebuilt else "Here are some fun animal facts in simple English. If you want more, tell me which animal!"

        if not is_output_safe(chat_id, answer):
            answer = safe_fallback_response()
        answer = sanitize_output(answer or "")

        if answer.strip():
            # Converter: simple Markdown to HTML for Telegram rendering
            def to_html(text: str) -> str:
                s = text or ""
                s = html_lib.escape(s)
                s = re.sub(r"```[\s\S]*?```", lambda m: "<pre><code>" + html_lib.escape(m.group(0)[3:-3].strip()) + "</code></pre>", s)
                s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
                s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
                return s

            # Chunking to avoid Telegram 4096 char limit; split on paragraphs/newlines/spaces
            def chunk_text(s: str, limit: int = 3500) -> list[str]:
                s = s.strip()
                if len(s) <= limit:
                    return [s]
                parts = []
                while s:
                    if len(s) <= limit:
                        parts.append(s)
                        break
                    cut = s.rfind('\n\n', 0, limit)
                    if cut == -1:
                        cut = s.rfind('\n', 0, limit)
                    if cut == -1:
                        cut = s.rfind(' ', 0, limit)
                    if cut == -1:
                        cut = limit
                    parts.append(s[:cut])
                    s = s[cut:].lstrip()
                return parts

            chunks = chunk_text(answer.strip())
            first_html = to_html(chunks[0])
            try:
                loading_msg.edit_text(first_html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception:
                update.message.reply_text(first_html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            # Send remaining chunks as follow-ups
            if len(chunks) > 1:
                for ch in chunks[1:]:
                    html_ch = to_html(ch)
                    update.message.reply_text(html_ch, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            # Save to memory
            try:
                remember_turn(chat_id, user_prompt, answer.strip())
            except Exception:
                pass
        else:
            logger.warning("Received an empty 'text' field from Cortensor API.")
            try:
                loading_msg.edit_text("I’m sorry, I didn’t receive valid content. Please try a different question.", parse_mode=ParseMode.HTML)
            except Exception:
                update.message.reply_text("I’m sorry, I didn’t receive valid content. Please try a different question.", parse_mode=ParseMode.HTML)

    except Exception:
        logger.error("An unexpected error occurred", exc_info=True)
        try:
            loading_msg.edit_text("Sorry, an unexpected error occurred.", parse_mode=ParseMode.HTML)
        except Exception:
            update.message.reply_text("Sorry, an unexpected error occurred.", parse_mode=ParseMode.HTML)
    finally:
        # Nothing to cancel; we only did a single edit
        pass


def start_command(update: Update, context: CallbackContext):
    update.message.reply_text(
    "Hi! I’m Eureka. Ask me anything.\n"
    "Type /help for commands. Parents: use /parent to unlock and /setpin to set a PIN."
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Commands and usage:\n\n"
        "General\n"
        "- /start — Greet and basic info.\n"
        "- /help — Show this help message.\n"
        "- /style [id] — Without arguments, lists available styles. With an id, sets the reply style.\n"
    "- (Model is fixed to DeepSeek by default.)\n"
        "- /reset — Reset style and short chat memory for this chat.\n\n"
        "Parent mode (admin)\n"
        "- /parent — If no PIN is set, you’ll be asked to create one. If a PIN exists, you’ll be asked to enter it to unlock.\n"
        "- /setpin <new_pin> — Set or change the PIN (requires unlocked parent mode if changing).\n"
        "- /parentlock — Lock parent mode again for this chat.\n"
        "- /addbad <word> — Add a custom bad word to the filter.\n"
        "- /removebad <word> — Remove a custom bad word.\n"
    "- /listbad — List custom bad words.\n"
    "- /badcount — Show counts for built-in and custom filters.\n"
    "- /checkbad <term> — Check if a term would be blocked.\n"
    "- /adminresetpin <chat_id> [new_pin] — Admin only: reset or set another chat’s PIN.\n\n"
        "What to ask\n"
        "- Fun facts about animals or space\n"
        "- A short, safe story\n"
        "- Step-by-step help (math, science, writing)\n"
        "- Jokes or riddles\n\n"
        "Safety\n"
        "- I don’t store personal info and avoid unsafe or adult topics.\n"
        "- If something looks unsafe, I’ll gently refuse and suggest a safer alternative."
    )

def styles_list() -> str:
    return "\n".join([f"- {s['id']}: {s['name']}" for s in AgentStyles.values()])

def style_command(update: Update, context: CallbackContext):
    args = context.args or []
    chat_id = update.effective_chat.id
    if not args:
        update.message.reply_text("Available styles:\n" + styles_list())
        return
    candidate = args[0].strip()
    if candidate not in AgentStyles:
        update.message.reply_text("Unknown style. Available:\n" + styles_list())
        return
    set_style(chat_id, candidate)
    update.message.reply_text(f"Style set to: {AgentStyles[candidate]['name']}")

# model selection removed: always use defaults from config

def reset_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    reset_style(chat_id)
    update.message.reply_text("Style reset to default.")


"""Parent mode commands"""
def parent_command(update: Update, context: CallbackContext):
    # If a PIN exists, verify; otherwise set a new PIN
    chat_id = update.effective_chat.id
    if has_pin(chat_id):
        prompt_verify_pin(update, context)
    else:
        prompt_set_pin(update, context)


def addbad_command(update: Update, context: CallbackContext):
    if not require_parent(update):
        return
    args = context.args or []
    if not args:
        update.message.reply_text("Usage: /addbad <kata>")
        return
    word = args[0]
    ok = add_bad_word(update.effective_chat.id, word)
    update.message.reply_text("Ditambahkan." if ok else "Sudah ada / tidak valid.")


def removebad_command(update: Update, context: CallbackContext):
    if not require_parent(update):
        return
    args = context.args or []
    if not args:
        update.message.reply_text("Usage: /removebad <kata>")
        return
    word = args[0]
    ok = remove_bad_word(update.effective_chat.id, word)
    update.message.reply_text("Dihapus." if ok else "Tidak ditemukan / tidak valid.")


def listbad_command(update: Update, context: CallbackContext):
    if not require_parent(update):
        return
    items = list_custom_words(update.effective_chat.id)
    if items:
        update.message.reply_text("Custom filter words:\n- " + "\n- ".join(items))
    else:
        update.message.reply_text("No custom words yet.")


def setpin_command(update: Update, context: CallbackContext):
    parent_set_pin_command(update, context)


def parentlock_command(update: Update, context: CallbackContext):
    parent_lock(update, context)


def badcount_command(update: Update, context: CallbackContext):
    if not require_parent(update):
        return
    s = default_filter_summary(update.effective_chat.id)
    update.message.reply_text(
        "Filter summary (counts only):\n"
        f"- Profanity lexicon (active): {s.get('profanity_lexicon_total', 0)}\n"
        f"- Indonesian base words: {s.get('indo_profanity', 0)}\n"
        f"- Unsafe keywords: {s.get('unsafe_words', 0)}\n"
        f"- Unsafe phrases: {s.get('unsafe_phrases', 0)}\n"
        f"- Strict kids keywords: {s.get('strict_kids_words', 0)}\n"
        f"- Strict kids phrases: {s.get('strict_kids_phrases', 0)}\n"
        f"- Custom words: {s.get('custom_words', 0)}"
    )


def checkbad_command(update: Update, context: CallbackContext):
    if not require_parent(update):
        return
    args = context.args or []
    if not args:
        update.message.reply_text("Usage: /checkbad <term>")
        return
    term = " ".join(args).strip()
    # Use chat-aware input check with only custom words + profanity; reuse is_input_unsafe but it covers more.
    blocked = is_input_unsafe(update.effective_chat.id, term)
    update.message.reply_text("Blocked" if blocked else "Not blocked")


def resetpin_command(update: Update, context: CallbackContext):
    # Admin-only command handled in parent module
    admin_reset_pin(update, context)


def adminresetpin_command(update: Update, context: CallbackContext):
    # Alias for admin-only pin reset
    admin_reset_pin(update, context)
