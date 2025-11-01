import os
import json
import time
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from telegram.error import BadRequest

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# config values
from config import TELEGRAM_BOT_TOKEN, INSIGHTS_QUEUE_FILE, SUBSCRIBERS_FILE

# --- Logging setup ---------------------------------------------------------
LOG_FILE = "telegram_bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cortensor_telegram")

# --- Utility helpers -------------------------------------------------------
def safe_load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        logger.error("❌ JSON decode error for %s", path)
        return default
    except Exception as e:
        logger.exception("❌ Error reading %s: %s", path, e)
        return default

def safe_write_json(path: str, data: Any):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        logger.exception("❌ Failed to write JSON to %s", path)

def truncate_text(text: str, limit: int = 4000) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    # try to cut at newline boundary
    candidate = text[:limit].rsplit("\n", 1)[0]
    if candidate:
        return candidate + "\n\n[Message truncated]"
    return text[:limit] + "\n\n[Message truncated]"

# --- Insight parsing / formatting -----------------------------------------
def normalize_key_insights(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        out = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                s = re.sub(r'\s+', ' ', item).strip()
                out.append(s)
            elif isinstance(item, dict):
                txt = item.get("text") or item.get("content") or ""
                if isinstance(txt, str) and txt.strip():
                    out.append(re.sub(r'\s+', ' ', txt).strip())
        return out[:5]
    if isinstance(raw, str):
        lines = [ln.strip() for ln in re.split(r'[\r\n]+', raw) if ln.strip()]
        lines = [re.sub(r'^\d+\.\s*', '', ln) for ln in lines]
        return lines[:5]
    return []

def heuristic_parse_plain_text_for_insight(text: str) -> Dict[str, Any]:
    """Heuristic extraction: TLDR (one-liner), summary (2-3 sentences), key_insights (bullets)."""
    out = {"tldr": None, "summary": None, "key_insights": []}
    if not text:
        return out

    t = text.strip()
    # strip code fences
    t = re.sub(r'^\s*```(?:json|text)?\n', '', t)
    t = re.sub(r'\n```$', '', t)
    # normalize newlines & whitespace
    t = re.sub(r'\r\n?', '\n', t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = t.strip()

    # try TL;DR label
    m = re.search(r'^(?:TL;DR|TLDR|T/L;DR)[:\-\s]*([^\n]+)', t, flags=re.IGNORECASE)
    if m:
        out["tldr"] = m.group(1).strip()
        t_after = t[m.end():].strip()
    else:
        # fallback to first sentence
        first_sentence = re.split(r'(?<=[.!?])\s+', t, maxsplit=1)[0].strip()
        out["tldr"] = first_sentence
        t_after = t[len(first_sentence):].strip()

    # summary: first 2-3 sentences from t_after (or from t if empty)
    source = t_after if t_after else t
    sentences = re.split(r'(?<=[.!?])\s+', source)
    summary = " ".join([s.strip() for s in sentences[:3] if s.strip()])
    out["summary"] = summary if summary else out["tldr"]

    # bullets: -, •, *, or numbered lists, or lines under "Key Insights"
    bullets = re.findall(r'^[\-\*•]\s*(.+)', t, flags=re.MULTILINE)
    if not bullets:
        bullets = re.findall(r'^\d+\.\s*(.+)', t, flags=re.MULTILINE)
    if not bullets:
        m2 = re.search(r'Key Insights[:\s]*\n(.*)', t, flags=re.IGNORECASE | re.DOTALL)
        if m2:
            block = m2.group(1).strip()
            lines = [ln.strip() for ln in re.split(r'[\r\n]+', block) if ln.strip()]
            for ln in lines:
                if len(ln) < 8:
                    continue
                bullets.append(ln)
                if len(bullets) >= 5:
                    break

    if not bullets:
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        candidate = []
        for ln in lines:
            if len(ln) < 12 or len(ln) > 400:
                continue
            if ln.lower().startswith(("note:", "info:", "summary")):
                continue
            candidate.append(ln)
            if len(candidate) >= 5:
                break
        bullets = candidate

    cleaned = []
    for b in bullets:
        s = re.sub(r'\s+', ' ', b).strip()
        s = re.sub(r'^[\-\*\u2022\s]+', '', s)
        if s:
            cleaned.append(s)
        if len(cleaned) >= 5:
            break

    out["key_insights"] = cleaned
    return out

def parse_structured_insight(insight: Any) -> Dict[str, Any]:
    """
    Given insight (from queue: could be dict with tldr/summary/key_insights/raw OR could be older formats),
    return normalized dict with keys: tldr (str), summary (str), key_insights (list[str]), raw (str).
    """
    result = {"tldr": None, "summary": None, "key_insights": [], "raw": None}
    if not insight:
        return result

    # If insight is dict and has tldr/summary/key_insights
    if isinstance(insight, dict):
        # If directly stored as normalized by processor
        if "tldr" in insight or "summary" in insight or "key_insights" in insight:
            result["tldr"] = insight.get("tldr") or None
            result["summary"] = insight.get("summary") or None
            result["key_insights"] = normalize_key_insights(insight.get("key_insights") or insight.get("insights") or [])
            result["raw"] = insight.get("raw") or None
            # If tldr or summary missing, try to heuristically parse raw
            if (not result["tldr"] or not result["summary"]) and result["raw"]:
                heur = heuristic_parse_plain_text_for_insight(result["raw"])
                result["tldr"] = result["tldr"] or heur.get("tldr")
                result["summary"] = result["summary"] or heur.get("summary")
                if not result["key_insights"]:
                    result["key_insights"] = heur.get("key_insights") or []
            return result

        # else, maybe insight contains 'summary' as string with the text we previously used
        if "summary" in insight and isinstance(insight["summary"], (str,)):
            raw_text = insight.get("summary")
            result["raw"] = raw_text
            heur = heuristic_parse_plain_text_for_insight(raw_text)
            result["tldr"] = heur.get("tldr")
            result["summary"] = heur.get("summary")
            result["key_insights"] = heur.get("key_insights")
            return result

        # If insight contains nested structures (choices/text/response)
        for k in ("text", "response", "content"):
            if k in insight and isinstance(insight[k], (str,)):
                raw_text = insight[k]
                result["raw"] = raw_text
                heur = heuristic_parse_plain_text_for_insight(raw_text)
                result["tldr"] = heur.get("tldr")
                result["summary"] = heur.get("summary")
                result["key_insights"] = heur.get("key_insights")
                return result

        # fallback: stringify
        try:
            raw_text = json.dumps(insight, ensure_ascii=False)
            heur = heuristic_parse_plain_text_for_insight(raw_text)
            result["raw"] = raw_text
            result["tldr"] = heur.get("tldr")
            result["summary"] = heur.get("summary")
            result["key_insights"] = heur.get("key_insights")
            return result
        except Exception:
            return result

    # If insight is a string
    if isinstance(insight, str):
        result["raw"] = insight
        heur = heuristic_parse_plain_text_for_insight(insight)
        result["tldr"] = heur.get("tldr")
        result["summary"] = heur.get("summary")
        result["key_insights"] = heur.get("key_insights")
        return result

    # unknown shape
    try:
        raw_text = str(insight)
        result["raw"] = raw_text
        heur = heuristic_parse_plain_text_for_insight(raw_text)
        result["tldr"] = heur.get("tldr")
        result["summary"] = heur.get("summary")
        result["key_insights"] = heur.get("key_insights")
        return result
    except Exception:
        return result

def build_telegram_message(original_content: str, parsed_insight: Dict[str, Any]) -> str:
    """
    Build final Telegram message (Markdown):
    - TL;DR: one-line
    - High-level summary: 2-3 sentences
    - Key Insights: bullets
    Also include an "Original Preview" short snippet at top.
    """
    preview = (original_content or "").strip()
    if len(preview) > 300:
        preview = preview[:300].rsplit(" ", 1)[0] + "..."

    tldr = (parsed_insight.get("tldr") or "").strip()
    if tldr and not tldr.endswith(('.', '!', '?')):
        # keep single-line as is; no enforced punctuation
        pass
    if not tldr:
        tldr = "(No TL;DR available.)"

    summary = (parsed_insight.get("summary") or "").strip()
    if not summary:
        summary = "(No high-level summary available.)"

    keys = parsed_insight.get("key_insights") or []
    if not keys:
        keys_text = "• (No key insights extracted.)"
    else:
        # Limit to 5 bullets, developer requested 3-5, prefer up to 5 but choose 3 if many short ones
        bullets = keys[:5]
        keys_text = "\n".join([f"• {b}" for b in bullets])

    # Compose message
    msg = (
        "🚀 *Cortensor Watcher — Development Insight*\n\n"
        "📝 *Original Preview:*\n"
        f"_{preview}_\n\n"
        f"🧠 *TL;DR:* {tldr}\n\n"
        f"🔎 *High-level summary:*\n{summary}\n\n"
        f"🔑 *Key Insights:*\n{keys_text}"
    )

    return truncate_text(msg, 3900)

# --- Telegram Bot class ----------------------------------------------------
class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.subscribers: List[int] = self.load_subscribers()
        self.setup_handlers()
        # send throttling
        self._per_msg_delay = 0.12  # seconds between messages
        self._last_send_ts = 0.0

    def load_subscribers(self) -> List[int]:
        data = safe_load_json(SUBSCRIBERS_FILE, {"subscribers": []})
        subs = data.get("subscribers", [])
        logger.info("📋 Loaded %d subscribers", len(subs))
        return subs if isinstance(subs, list) else []

    def save_subscribers(self):
        safe_write_json(SUBSCRIBERS_FILE, {"subscribers": self.subscribers})
        logger.info("💾 Saved %d subscribers", len(self.subscribers))

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    # --- user commands ----------------------------------------------------
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if chat_id not in self.subscribers:
            self.subscribers.append(chat_id)
            self.save_subscribers()
            logger.info("✅ New subscriber: %s (%s)", user.full_name if user else "unknown", chat_id)
        welcome = (
            "👋 *Welcome to Cortensor Watcher!*\n\n"
            "You will receive summarized developer updates (TL;DR + high-level summary + key insights).\n\n"
            "Commands:\n"
            "• /start — Subscribe\n"
            "• /stop — Unsubscribe\n"
            "• /status — Check subscription"
        )
        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        if chat_id in self.subscribers:
            try:
                self.subscribers.remove(chat_id)
                self.save_subscribers()
                logger.info("❌ Unsubscribed: %s (%s)", user.full_name if user else "unknown", chat_id)
            except ValueError:
                pass
            await update.message.reply_text("✅ You have been unsubscribed from updates.")
        else:
            await update.message.reply_text("ℹ️ You are not currently subscribed.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        total = len(self.subscribers)
        if chat_id in self.subscribers:
            await update.message.reply_text(f"✅ You are subscribed.\n\nTotal subscribers: {total}")
        else:
            await update.message.reply_text(f"❌ You are not subscribed.\n\nTotal subscribers: {total}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Auto-subscribe when user sends a message (friendly behaviour)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        if chat_id not in self.subscribers:
            self.subscribers.append(chat_id)
            self.save_subscribers()
            logger.info("✅ Auto-subscribed: %s (%s)", user.full_name if user else "unknown", chat_id)
        await update.message.reply_text(
            "🤖 I'm Cortensor Watcher — I will send summarized developer updates automatically.\n"
            "Use /start to ensure you're subscribed, or /stop to unsubscribe."
        )

    # --- send helpers -----------------------------------------------------
    async def _send_to_chat(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> Tuple[bool, Optional[str]]:
        """Send message with small inter-message delay and return (success, error).
        Try Markdown first; if Telegram fails to parse entities, retry as plain text.
        """
        try:
            now = time.time()
            elapsed = now - self._last_send_ts
            if elapsed < self._per_msg_delay:
                await asyncio.sleep(self._per_msg_delay - elapsed)

            # Try with requested parse_mode first
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True
                )
                self._last_send_ts = time.time()
                return True, None
            except BadRequest as br:
                # Telegram could not parse entities (likely malformed Markdown)
                err_text = str(br)
                logger.warning("⚠️ BadRequest while sending to %s: %s", chat_id, err_text)
                if "Can't parse entities" in err_text or "can't find end of the entity" in err_text:
                    # Retry as plain text (no parse mode) to ensure delivery
                    try:
                        await asyncio.sleep(0.05)  # tiny pause before retry
                        await self.application.bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            disable_web_page_preview=True
                        )
                        self._last_send_ts = time.time()
                        logger.info("🔁 Fallback plain-text send succeeded for %s", chat_id)
                        return True, None
                    except Exception as e2:
                        logger.warning("❌ Fallback plain-text send ALSO failed for %s: %s", chat_id, e2)
                        return False, str(e2)
                # Other BadRequest reasons -> return error
                return False, err_text
            except Exception as e:
                # other send-time exceptions (rate limit, network, etc.)
                logger.warning("❌ send_message exception for %s: %s", chat_id, e)
                return False, str(e)

        except Exception as e_outer:
            logger.exception("❌ Unexpected error in _send_to_chat: %s", e_outer)
            return False, str(e_outer)

    async def _broadcast_to_all(self, text: str) -> Tuple[int, int]:
        """
        Broadcast text to all subscribers (capped by list length).
        Returns (success_count, fail_count).
        Removes invalid subscribers automatically.
        """
        success = 0
        fail = 0
        # defensive copy
        subscribers_copy = list(self.subscribers)
        logger.info("📤 Broadcasting to %d subscribers...", len(subscribers_copy))
        for chat_id in subscribers_copy:
            sent, err = await self._send_to_chat(chat_id, text)
            if sent:
                success += 1
            else:
                fail += 1
                # remove if permanent error (blocked / chat not found / deactivated)
                err_lower = (err or "").lower()
                if "chat not found" in err_lower or "blocked" in err_lower or "user is deactivated" in err_lower:
                    try:
                        self.subscribers.remove(chat_id)
                        logger.info("🗑️ Removed invalid subscriber %s", chat_id)
                    except ValueError:
                        pass
        if fail > 0:
            self.save_subscribers()
        logger.info("📊 Broadcast finished — sent: %d, failed: %d", success, fail)
        return success, fail

    async def send_broadcast(self, text: str) -> Tuple[int, int]:
        """Public wrapper to broadcast a message to all subscribers (Markdown)."""
        trimmed = truncate_text(text, 3900)
        return await self._broadcast_to_all(trimmed)

    # --- queue processing -------------------------------------------------
    def format_insight_message(self, original_content: str, insight_data: Any) -> str:
        """Format insight data (structured or raw) to final Telegram message."""
        parsed = parse_structured_insight(insight_data)
        message = build_telegram_message(original_content, parsed)
        logger.info("📨 Built message len=%d", len(message))
        return message

    async def process_insights_queue(self):
        """Load INSIGHTS_QUEUE_FILE and send unsent items to all subscribers."""
        try:
            queue = safe_load_json(INSIGHTS_QUEUE_FILE, {"messages": []})
            messages = queue.get("messages", [])
        except Exception:
            logger.exception("❌ Error loading insights queue")
            return

        unsent = [m for m in messages if not m.get("sent", False)]
        if not unsent:
            logger.debug("⏭️ No unsent messages in queue")
            return

        logger.info("📁 Processing %d unsent messages for %d subscribers", len(unsent), len(self.subscribers))

        for item in unsent:
            mid = item.get("message_id", "unknown")
            original = item.get("original_content", "") or ""
            insight = item.get("insight", {}) or {}
            try:
                formatted = self.format_insight_message(original, insight)
                sent, failed = await self.send_broadcast(formatted)
                if sent > 0:
                    item["sent"] = True
                    item["sent_at"] = time.time()
                    item["sent_to"] = sent
                    item["failed_to"] = failed
                    # save queue state
                    safe_write_json(INSIGHTS_QUEUE_FILE, {"messages": messages})
                    logger.info("✅ Message %s sent to %d subscribers (failed=%d)", mid, sent, failed)
                else:
                    logger.error("❌ Message %s failed to send to any subscribers", mid)
            except Exception as e:
                logger.exception("❌ Error sending message %s: %s", mid, e)

    async def periodic_broadcast(self):
        """Background loop to check queue periodically."""
        logger.info("🔁 Starting periodic queue monitor (every 30s)")
        while True:
            try:
                await self.process_insights_queue()
            except Exception:
                logger.exception("⚠️ periodic broadcast encountered an error")
            await asyncio.sleep(30)

    # --- lifecycle --------------------------------------------------------
    def run(self):
        logger.info("🚀 Starting Telegram Bot...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def main():
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("✅ Bot is running and polling for commands")
            # start background task
            task = asyncio.create_task(self.periodic_broadcast())
            try:
                await task
            except asyncio.CancelledError:
                logger.info("🛑 periodic task cancelled")
            finally:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

        try:
            loop.run_until_complete(main())
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user (KeyboardInterrupt)")
        except Exception:
            logger.exception("❌ Unexpected error in bot run")
        finally:
            try:
                loop.close()
            except Exception:
                pass

# --- entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
