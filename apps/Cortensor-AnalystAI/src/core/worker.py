# src/core/worker.py

"""
Background Worker for Processing Analysis Tasks
Handles queued analysis requests with retry logic, caching, and notification delivery.
"""

import logging
import re
import time
import threading
import asyncio
import os
import json
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
import pytz
from telegram import InputFile
from telegram.error import BadRequest

from src.config import RETRY_ATTEMPTS, RETRY_DELAY_SECONDS, DEFAULT_TIMEZONE
from src.utils.database import (
    get_pending_task, 
    update_task_status, 
    update_task_result, 
    increment_task_attempts
)
from src.utils.caching import get_cached_result, set_cached_result
from src.services.market_data_api import get_market_data
from src.services.news_api import fetch_relevant_news
from src.core.prompt_builder import build_analyst_prompt
from src.core.cortensor_client import get_ai_analysis
from src.bot.formatter import format_final_message, _clean_ai_output, escape_html

logger = logging.getLogger(__name__)


def is_response_valid(response_text: str) -> bool:
    """A simple validation layer to check the quality of the AI response."""
    if not response_text or len(response_text) < 20:
        logger.warning("Validation failed: AI response is too short or empty.")
        return False
    return True


async def send_chart_if_exists(bot, user_id, price_chart_path):
    """Send price chart image to user if it exists."""
    if price_chart_path and os.path.exists(price_chart_path):
        try:
            with open(price_chart_path, 'rb') as f:
                await bot.send_photo(chat_id=user_id, photo=InputFile(f))
            logger.info(f"Chart sent to user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to send chart image: {e}")


async def send_final_message(bot, user_id, message_text, ack_message_id=None):
    """Safely sends a message to the user and deletes acknowledgment message if provided."""
    try:
        # Send the final result message
        await bot.send_message(
            user_id, 
            message_text, 
            parse_mode='HTML', 
            disable_web_page_preview=True
        )
        
        # Delete the acknowledgment message if provided
        if ack_message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=ack_message_id)
                logger.info(f"Deleted acknowledgment message {ack_message_id} for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not delete acknowledgment message {ack_message_id}: {e}")
        
        return True
    except BadRequest as e:
        logger.error(f"Failed to send message: {e}")
        return False


def generate_price_chart(topic: str, request_id: str, price_history: list) -> str | None:
    """
    Generate price chart from historical data.
    
    Args:
        topic: Asset name for chart title
        request_id: Unique request ID for file naming
        price_history: List of dicts with 'date' and 'price' keys
        
    Returns:
        str: Path to generated chart image, or None if generation fails
    """
    if not price_history or not isinstance(price_history, list) or len(price_history) < 2:
        return None
        
    try:
        dates = [x['date'] for x in price_history]
        prices = [x['price'] for x in price_history]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates, prices, marker='o', linewidth=2, markersize=4)
        ax.set_title(f"Price Chart for {topic}", fontsize=14, fontweight='bold')
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Price (USD)", fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Improve date formatting
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save chart
        chart_dir = os.path.join("output", "charts")
        os.makedirs(chart_dir, exist_ok=True)
        price_chart_path = os.path.join(chart_dir, f"{request_id}_price_chart.png")
        plt.savefig(price_chart_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Price chart generated: {price_chart_path}")
        return price_chart_path
        
    except Exception as e:
        logger.warning(f"Failed to generate price chart: {e}")
        return None


def clean_opinion_text(text: str) -> str:
    """Clean opinion text by removing sentiment prefixes."""
    return re.sub(
        r'^(Bullish|Bearish|Neutral|Positive|Negative|\*+|:|\s)+[:\*\s-]*', 
        '', 
        text, 
        flags=re.IGNORECASE
    ).strip()


def clean_key_takeaway(text: str) -> str:
    """Clean key takeaway text by removing formatting prefixes."""
    return re.sub(r'^[\*:\s]+', '', text).strip()


def parse_competitors_from_ai_response(ai_result_text: str) -> list:
    """Extract competitors list from AI response if present."""
    try:
        ai_json = None
        if ai_result_text.strip().startswith('{'):
            ai_json = json.loads(ai_result_text)
        elif '\n{"competitors":' in ai_result_text:
            ai_json = json.loads(ai_result_text.split('\n', 1)[1])
        
        if ai_json and 'competitors' in ai_json:
            return ai_json['competitors']
    except Exception:
        pass
    return []


async def process_single_task(bot):
    """Process a single task from the queue."""
    task = get_pending_task()
    if not task:
        return

    request_id = task['request_id']
    topic = task['topic']
    user_id = task['user_id']
    ack_message_id = task.get('ack_message_id')
    analysis_type = task.get('analysis_type', 'manual')
    
    logger.info(f"Worker picked up task {request_id} for topic '{topic}' (type: {analysis_type}).")
    update_task_status(request_id, 'PROCESSING')

    # Check cache first
    cached_result = get_cached_result(topic)
    if cached_result:
        logger.info(f"Found cached result for '{topic}'. Using cache.")
        if await send_final_message(bot, user_id, cached_result, ack_message_id):
            update_task_status(request_id, 'COMPLETED')
        else:
            update_task_status(request_id, 'FAILED')
        return

    # Process with retry logic
    for attempt in range(RETRY_ATTEMPTS):
        current_attempt = increment_task_attempts(request_id)
        logger.info(f"Processing attempt {current_attempt}/{RETRY_ATTEMPTS} for {request_id}.")
        
        try:
            # Fetch market data
            market_data = get_market_data(topic)
            if not market_data:
                error_message = (
                    f"❌ Analysis for '{topic}' failed: Could not fetch market data. "
                    "Please check the ticker symbol."
                )
                await send_final_message(bot, user_id, error_message, ack_message_id)
                update_task_status(request_id, 'FAILED')
                return

            asset_type = market_data.get('type', 'Unknown')
            asset_symbol = market_data.get('symbol', topic)
            
            # Fetch news
            news_data = fetch_relevant_news(topic, asset_type, asset_symbol)
            
            # Build prompt and get AI analysis
            prompt = build_analyst_prompt(market_data, news_data)
            ai_result_text = get_ai_analysis(request_id, prompt)

            # Generate price chart
            price_chart_path = generate_price_chart(
                topic, 
                request_id, 
                market_data.get('price_history')
            )

            if ai_result_text and is_response_valid(ai_result_text):
                # Parse AI response
                competitors = parse_competitors_from_ai_response(ai_result_text)
                parsed = _clean_ai_output(
                    ai_result_text,
                    [n.get('title', '') for n in news_data] if news_data else []
                )
                opinions = parsed.get('opinions', [])
                key_takeaway = parsed.get('key_takeaway', '')

                # Get current time in configured timezone
                default_tz = pytz.timezone(DEFAULT_TIMEZONE)
                current_time = datetime.now(default_tz)
                date_str = current_time.strftime('%A, %d %B %Y')
                time_str = current_time.strftime('%H:%M WIB')

                # Build report sections
                header_lines = [
                    '💎 Analyst Report 💎',
                    '',
                    f"📈 Company: {escape_html(market_data.get('company_name', topic))} ({market_data.get('symbol', topic)})",
                    f"📅 {date_str}",
                    f"🕐 {time_str}",
                    '',
                    '━━━━━━━━━━━━━━━━━━',
                    ''
                ]
                
                opinion_lines = ['Expert Opinions:']
                for idx, (sentiment, text) in enumerate(opinions):
                    emoji = {'Bullish': '🟢', 'Bearish': '🔴', 'Neutral': '🟡'}.get(sentiment, '🟡')
                    cleaned = clean_opinion_text(text)
                    opinion_lines.append(f"• [Expert {idx+1}] {emoji} {sentiment}: {escape_html(cleaned)}")
                if not opinions:
                    opinion_lines.append('• <i>No expert opinions available.</i>')
                opinion_lines.append('')
                
                key_lines = [
                    '🔑 <b>Key Takeaway:</b>',
                    escape_html(clean_key_takeaway(key_takeaway)) if key_takeaway else '<i>No summary was generated.</i>',
                    ''
                ]
                
                news_lines = ['News Summary:']
                if news_data:
                    for idx, n in enumerate(news_data, 1):
                        title = escape_html(n.get('title', ''))
                        url = n.get('url', '')
                        summary = escape_html(n.get('summary', ''))
                        if summary:
                            news_lines.append(f"• News {idx}: {title}  ({url})\n  {summary}")
                        else:
                            news_lines.append(f"• News {idx}: {title}  ({url})")
                else:
                    news_lines.append('• <i>No news found.</i>')
                news_lines.append('')
                
                disclaimer = [
                    'Disclaimer: This report is for informational purposes only and does not '
                    'constitute financial advice. Please do your own research before making '
                    'investment decisions.'
                ]
                
                # Format final message
                final_message = format_final_message(
                    topic,
                    ai_result_text,
                    market_data,
                    news_data,
                    price_chart_path=price_chart_path,
                    competitors=competitors,
                    analysis_type=analysis_type
                )
                
                if await send_final_message(bot, user_id, final_message, ack_message_id):
                    await send_chart_if_exists(bot, user_id, price_chart_path)
                    update_task_result(request_id, 'COMPLETED', final_message)
                    set_cached_result(topic, final_message)
                    logger.info(f"Task {request_id} completed successfully.")
                    return
                else:
                    raise ValueError("Failed to send final message.")
            else:
                raise ValueError("AI Response failed validation or was empty.")

        except Exception as e:
            logger.error(f"Error on attempt {current_attempt} for {request_id}: {e}")

        # Wait before retry (except on last attempt)
        if current_attempt < RETRY_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS)
        else:
            error_message = (
                f"❌ Analysis for '{topic}' failed after multiple attempts. "
                "There might be an issue with external APIs or AI response generation."
            )
            await send_final_message(bot, user_id, error_message, ack_message_id)
            update_task_status(request_id, 'FAILED')


async def worker_loop(bot):
    """The main loop for the worker thread."""
    logger.info("Background worker thread started.")
    while True:
        try:
            await process_single_task(bot)
        except Exception as e:
            logger.critical(f"Critical error in worker loop: {e}", exc_info=True)
        await asyncio.sleep(5)


def start_background_worker(bot_instance):
    """Starts the worker in a separate daemon thread."""
    worker_thread = threading.Thread(
        target=lambda: asyncio.run(worker_loop(bot_instance)), 
        daemon=True
    )
    worker_thread.start()
    logger.info("Background worker thread initialized.")
    return worker_thread
