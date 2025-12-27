from __future__ import annotations

import asyncio
import datetime
import logging
import re
from html import escape as html_escape
from textwrap import dedent

import aiohttp
import pytz
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message

from src.config import Settings, load_settings
from src.cortensor_client import CortensorClient
from src.x_client import XClient
from src.x_scraper import XPost, XScraper

logger = logging.getLogger(__name__)


def build_dev_update_prompt(
    *,
    start_date_label: str,
    end_date_label: str,
    x_account_url: str,
    posts_block: str,
) -> str:
    """Strict prompt optimized for OSS 20B: short + explicit rules."""
    return dedent(
        f"""
        Generate a “Dev Update & Recap” covering all original dev or technical posts from the official Cortensor X account ({x_account_url}) between {start_date_label} and {end_date_label}.

        Rules:
        - Include posts, quote posts, retweets, and self-thread posts (replies to self).
        - Exclude replies to other accounts.
        - Include all DevLogs, technical updates, model/engine notes, documentation updates, /validate work, roadmap posts, and Testnet updates.
        - Keep summaries concise (one sentence each).
        - List posts in chronological order.
        - Use ONLY the posts provided below. Do not invent posts.

        Output format:
        - Begin with exactly:
          📌 Dev Update & Recap ({start_date_label}–{end_date_label})
        - Then for each entry:
          🔹 {{Title}}
          {{One-sentence summary}}
          {{Link}}

        Posts (chronological):
        {posts_block}
        """
    ).strip()


def create_dispatcher(
    settings: Settings,
    cortensor: CortensorClient,
    x_client: XClient | None,
    x_scraper: XScraper | None,
) -> Dispatcher:
    dp = Dispatcher()
    interval_days = settings.recap_interval_days

    def is_user_allowlisted(message: Message) -> bool:
        if not settings.admin_only:
            return message.from_user is not None

        # Strict mode: only users in ADMIN_USER_IDS are allowed.
        # If the allowlist is empty, deny all (explicit allowlist required).
        if message.from_user is None:
            return False
        if not settings.admin_user_ids:
            return False
        return message.from_user.id in settings.admin_user_ids

    def scheduler_allowed_target() -> bool:
        # Optional: restrict where the scheduler is allowed to post.
        if not settings.allowed_chat_ids:
            return True
        if settings.target_chat_id is None:
            return False
        return settings.target_chat_id in settings.allowed_chat_ids

    @dp.message(Command("start"))
    async def handle_start(message: Message) -> None:
        if not is_user_allowlisted(message):
            return
        await message.answer(
            "Bot active. Commands:\n"
            "/help\n"
            "/recap (last interval)\n"
            "/recapdays N\n"
            "/recaprange YYYY-MM-DD YYYY-MM-DD\n"
            "/setinterval N"
        )

    @dp.message(Command("help"))
    async def handle_help(message: Message) -> None:
        if not is_user_allowlisted(message):
            return

        # Note: Bot default parse_mode is HTML.
        text = (
            "<b>Recap Bot</b>\n"
            f"Generates a short recap from <b>@{html_escape(settings.x_username)}</b> posts for a chosen date range and posts it to the target chat.\n\n"
            "<b>Commands</b>\n"
            "- /recap [N] — recap using the default interval (or N days)\n"
            "- /recapdays N — recap the last N days (1–31)\n"
            "- /recaprange START END — recap a custom date range (max 31 days)\n"
            "- /setinterval N — set the default interval (days)\n\n"
            "<b>Usage examples</b>\n"
            "- <code>/recap</code>\n"
            "- <code>/recap 2</code>\n"
            "- <code>/recapdays 3</code>\n"
            "- <code>/recaprange 2025-12-01 2025-12-23</code>\n"
            "- <code>/setinterval 3</code>\n\n"
            "<b>Notes</b>\n"
            "- Date format: <code>YYYY-MM-DD</code>\n"
            "- X API rate limits may apply.\n"
            "- Username lookup (resolve @username): 3 requests / 15 mins\n"
            "- Post fetch (timeline): 1 request / 15 mins\n"
            "- If you see <code>429 Too Many Requests</code>, wait 15 minutes and try again.\n"
            "- If the bot doesn't reply, access may be restricted.\n"
        )
        await message.answer(text)

    @dp.message(Command("chatid"))
    async def handle_chatid(message: Message) -> None:
        if not is_user_allowlisted(message):
            return
        await message.answer(f"chat id: {message.chat.id}\nchat title: {message.chat.title}")

    @dp.message(Command("health"))
    async def handle_health(message: Message) -> None:
        if not is_user_allowlisted(message):
            return
        await message.answer("Checking router health…")
        try:
            info = await cortensor.healthcheck()
            await message.answer(f"Router info: {info}")
        except Exception as exc:
            await message.answer(f"Router check failed: {exc}")

    async def post_recap_to_target(bot: Bot, recap: str) -> None:
        if settings.target_chat_id is None:
            raise RuntimeError("TARGET_CHAT_ID not set")
        await bot.send_message(settings.target_chat_id, recap, parse_mode="HTML")

    async def handle_range(message: Message, *, start_date: datetime.date, end_date: datetime.date) -> None:
        if not is_user_allowlisted(message):
            return
        if settings.target_chat_id is None:
            await message.answer("Set TARGET_CHAT_ID in .env then restart bot.")
            return

        await message.answer(f"Fetching @{settings.x_username} posts from {start_date} to {end_date}…")
        recap = await generate_dev_update_recap(
            x_client=x_client,
            x_scraper=x_scraper,
            cortensor=cortensor,
            settings=settings,
            start_date=start_date,
            end_date=end_date,
        )
        recap = wrap_tables_with_pre(telegram_html_sanitize(normalize_links(recap)))
        await post_recap_to_target(message.bot, recap)
        if message.chat.id != settings.target_chat_id:
            await message.answer("Recap posted to target chat.")

    @dp.message(Command("recap"))
    async def handle_recap(message: Message) -> None:
        if not is_user_allowlisted(message):
            return
        args = _command_args(message)
        days: int
        if len(args) == 1 and args[0].isdigit():
            days = int(args[0])
            if days < 1 or days > 31:
                await message.answer("N must be 1..31")
                return
        elif len(args) == 0:
            days = interval_days
        else:
            await message.answer("Usage: /recap or /recap N (e.g. /recap 3)")
            return

        end_date = datetime.datetime.now(pytz.UTC).date()
        start_date = end_date - datetime.timedelta(days=days - 1)
        try:
            await handle_range(message, start_date=start_date, end_date=end_date)
        except Exception as exc:
            logger.exception("/recap failed")
            await message.answer(f"Failed: {exc}")

    @dp.message(Command("recapdays"))
    async def handle_recapdays(message: Message) -> None:
        if not is_user_allowlisted(message):
            return
        args = _command_args(message)
        if len(args) != 1 or not args[0].isdigit():
            await message.answer("Usage: /recapdays N (e.g. /recapdays 3)")
            return
        days = int(args[0])
        if days < 1 or days > 31:
            await message.answer("N must be 1..31")
            return
        end_date = datetime.datetime.now(pytz.UTC).date()
        start_date = end_date - datetime.timedelta(days=days - 1)
        try:
            await handle_range(message, start_date=start_date, end_date=end_date)
        except Exception as exc:
            logger.exception("/recapdays failed")
            await message.answer(f"Failed: {exc}")

    @dp.message(Command("recaprange"))
    async def handle_recaprange(message: Message) -> None:
        if not is_user_allowlisted(message):
            return
        args = _command_args(message)
        if len(args) != 2:
            await message.answer("Usage: /recaprange YYYY-MM-DD YYYY-MM-DD")
            return
        try:
            start_date = _parse_ymd(args[0])
            end_date = _parse_ymd(args[1])
        except ValueError:
            await message.answer("Invalid date. Use YYYY-MM-DD.")
            return
        if end_date < start_date:
            await message.answer("END date must be >= START date")
            return
        if (end_date - start_date).days > 30:
            await message.answer("Max range is 31 days")
            return
        try:
            await handle_range(message, start_date=start_date, end_date=end_date)
        except Exception as exc:
            logger.exception("/recaprange failed")
            await message.answer(f"Failed: {exc}")

    @dp.message(Command("setinterval"))
    async def handle_setinterval(message: Message) -> None:
        nonlocal interval_days
        if not is_user_allowlisted(message):
            return
        args = _command_args(message)
        if len(args) != 1 or not args[0].isdigit():
            await message.answer("Usage: /setinterval N (days)")
            return
        value = int(args[0])
        if value < 1 or value > 31:
            await message.answer("N must be 1..31")
            return
        interval_days = value
        await message.answer(f"Interval set to {interval_days} days.")

    async def interval_task(bot: Bot) -> None:
        if not settings.auto_recap_enabled:
            logger.info("AUTO_RECAP_ENABLED=0; scheduler disabled")
            return
        if settings.target_chat_id is None:
            logger.warning("TARGET_CHAT_ID not set; scheduler disabled")
            return
        if not scheduler_allowed_target():
            logger.warning("TARGET_CHAT_ID not allowed by ALLOWED_CHAT_IDS; scheduler disabled")
            return

        next_run_at = _compute_next_run(datetime.datetime.now(pytz.UTC), settings.recap_post_hour_utc)
        while True:
            now = datetime.datetime.now(pytz.UTC)
            if now >= next_run_at:
                end_date = now.date()
                start_date = end_date - datetime.timedelta(days=interval_days - 1)
                try:
                    recap = await generate_dev_update_recap(
                        x_client=x_client,
                        x_scraper=x_scraper,
                        cortensor=cortensor,
                        settings=settings,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    recap = wrap_tables_with_pre(telegram_html_sanitize(normalize_links(recap)))
                    await post_recap_to_target(bot, recap)
                except Exception as exc:
                    logger.exception("Scheduled recap failed: %s", exc)
                next_run_at = next_run_at + datetime.timedelta(days=interval_days)
            await asyncio.sleep(60)

    async def on_startup(bot: Bot) -> None:
        asyncio.create_task(interval_task(bot))

    dp.startup.register(on_startup)
    return dp


def telegram_html_sanitize(text: str) -> str:
    # Only allow Telegram HTML tags: b, strong, i, em, u, ins, s, strike, del, span, a, code, pre, tg-spoiler
    allowed_tags = {
        'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'span', 'a', 'code', 'pre', 'tg-spoiler'
    }

    def repl(m):
        tag = m.group(1).lower()
        if tag in allowed_tags:
            return m.group(0)
        return html_escape(m.group(0))

    text = re.sub(r'<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'(<)(?!/?[a-zA-Z])', '&lt;', text)
    text = re.sub(r'<\/?([a-zA-Z0-9\-]+)[^>]*>', repl, text)
    return text


def normalize_links(text: str) -> str:
    # Convert HTML anchors and markdown links to plain URLs to fit "{Link}" line expectation.
    text = re.sub(
        r'<a\s+href=["\']([^"\']+)["\']\s*>(.*?)</a>',
        r'\1',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\2', text)
    return text


def wrap_tables_with_pre(text: str) -> str:
    # Find blocks of lines with pipes and wrap them in <pre>...</pre>
    lines = text.splitlines()
    result = []
    in_table = False
    table_block = []
    for line in lines:
        if '|' in line:
            table_block.append(line)
            in_table = True
        else:
            if in_table and table_block:
                # End of table block
                result.append('<pre>' + '\n'.join(table_block) + '</pre>')
                table_block = []
                in_table = False
            result.append(line)
    if in_table and table_block:
        result.append('<pre>' + '\n'.join(table_block) + '</pre>')
    return '\n'.join(result)


def remove_hyperlinks(text: str) -> str:
    # Replace <a href="url">text</a> with 'text: url'
    import re
    text = re.sub(r'<a\s+href=["\']([^"\']+)["\']>(.*?)<\/a>', r'\2: \1', text, flags=re.IGNORECASE)
    # Replace markdown [text](url) with 'text: url'
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1: \2', text)
    return text


def _command_args(message: Message) -> list[str]:
    text = (message.text or "").strip()
    parts = text.split()
    return parts[1:]


def _parse_ymd(value: str) -> datetime.date:
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def _format_label(d: datetime.date) -> str:
    return d.strftime("%b %d %Y")


def _compute_next_run(now_utc: datetime.datetime, hour_utc: int) -> datetime.datetime:
    candidate = now_utc.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if candidate <= now_utc:
        candidate = candidate + datetime.timedelta(days=1)
    return candidate


def _posts_block(posts: list[XPost]) -> str:
    lines: list[str] = []
    for p in posts:
        text = p.text.replace("\n", " ").strip()
        if len(text) > 500:
            text = text[:497] + "…"
        created = p.created_at.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%MZ")
        lines.append(f"- {created}: {text}\n  {p.url}")
    return "\n".join(lines)


async def generate_dev_update_recap(
    *,
    x_client: XClient | None,
    x_scraper: XScraper | None,
    cortensor: CortensorClient,
    settings: Settings,
    start_date: datetime.date,
    end_date: datetime.date,
) -> str:
    start_dt = datetime.datetime.combine(start_date, datetime.time(0, 0, 0), tzinfo=pytz.UTC)
    end_exclusive = datetime.datetime.combine(
        end_date + datetime.timedelta(days=1),
        datetime.time(0, 0, 0),
        tzinfo=pytz.UTC,
    )

    if settings.x_fetch_mode == "scrape":
        if x_scraper is None:
            raise RuntimeError("X scraper not initialized")
        posts = await asyncio.to_thread(
            x_scraper.fetch_posts,
            username=settings.x_username,
            start_time=start_dt,
            end_time=end_exclusive,
        )
    else:
        if x_client is None:
            raise RuntimeError("X API client not initialized")
        user_id = settings.x_user_id or await x_client.get_user_id(settings.x_username)
        posts = await x_client.fetch_original_posts(
            user_id=user_id,
            username=settings.x_username,
            start_time=start_dt,
            end_time=end_exclusive,
        )

    if not posts:
        return (
            f"📌 Dev Update & Recap ({_format_label(start_date)}–{_format_label(end_date)})\n\n"
            "No original dev/technical posts found in this range."
        )

    prompt = build_dev_update_prompt(
        start_date_label=_format_label(start_date),
        end_date_label=_format_label(end_date),
        x_account_url=f"https://x.com/{settings.x_username}",
        posts_block=_posts_block(posts),
    )

    return await cortensor.summarize(
        prompt,
        prompt_type=settings.router_prompt_type,
        prompt_template=settings.router_prompt_template,
        precommit_timeout=settings.router_precommit_timeout,
        client_reference=settings.router_client_reference,
        max_tokens=settings.router_max_tokens,
        temperature=settings.router_temperature,
        top_p=settings.router_top_p,
        top_k=settings.router_top_k,
        presence_penalty=settings.router_presence_penalty,
        frequency_penalty=settings.router_frequency_penalty,
    )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))

    logger.info(
        "Bot starting with target_chat_id=%s side_chat_id=%s allow_main_chat=%s",
        settings.target_chat_id,
        settings.side_chat_id,
        settings.allow_main_chat,
    )

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.request_timeout)) as session:
        x_client: XClient | None = None
        x_scraper: XScraper | None = None
        if settings.x_fetch_mode == "scrape":
            x_scraper = XScraper(base_urls=settings.x_scrape_rss_base_urls, timeout_s=settings.request_timeout)
        else:
            x_client = XClient(settings.x_bearer_token, session=session)

        async with CortensorClient(
            base_url=settings.router_base_url,
            api_key=settings.router_api_key,
            timeout=settings.request_timeout,
            session_id=settings.router_session_id,
        ) as cortensor:
            dp = create_dispatcher(settings, cortensor, x_client, x_scraper)
            await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
