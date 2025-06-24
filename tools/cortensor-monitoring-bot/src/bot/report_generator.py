import logging
import aiohttp
import asyncio
from typing import Dict, Optional
from datetime import datetime, timezone
from aiogram.utils import markdown as md

# Assuming these modules exist and are correctly imported from your project structure
from . import api_client, utils, data_logger, health_checker

logger = logging.getLogger(__name__)

def get_change_str(current_rate: Optional[float], old_rate: Optional[float], 
                   current_points: int, old_points: Optional[int]) -> str:
    """
    Formats a string describing the change in points and success rate, including a trend emoji.
    """
    if any(v is None for v in [current_rate, old_rate, current_points, old_points]):
        return "N/A"
    
    rate_diff = current_rate - old_rate
    point_diff = current_points - old_points

    point_str = f"+{point_diff}" if point_diff >= 0 else str(point_diff)
    
    if rate_diff > 0.1:
        rate_str = f"+{rate_diff:.2f}% 📈"
    elif rate_diff < -0.1:
        rate_str = f"{rate_diff:.2f}% 📉"
    else:
        rate_str = f"~0.00% ➖"
        
    return f"{point_str} pts ({rate_str})"


def format_health_report(addr_data: Dict, health_data: Dict) -> str:
    """
    Formats the health check data into a cleaner, concise report.
    """
    name = addr_data.get('name', 'N/A')
    addr = addr_data.get('address', 'N/A')
    safe_name = md.escape_md(name)

    if not health_data:
        return f"❌ Could not perform health check for **{safe_name}**."

    title = f"📋 Health Card: **{safe_name}**"
    
    table_lines = [
        f"{'Address':<18}: {addr}",
        f"{'Reason':<18}: {health_data.get('reason', 'N/A')}",
        f"{'Last Transaction':<18}: {health_data.get('last_transaction_time', 'N/A')}",
        f"{'Status':<18}: {health_data.get('status', 'N/A')}",
        f"{'Balance':<18}: {health_data.get('balance', 'N/A')}",
        f"{'Health':<18}: {health_data.get('health_bar', 'N/A')}",
    ]
    table_string = "\n".join(table_lines)
    
    detailed_reason = health_data.get("detailed_reason")
    error_block = f"\n\n🔍 *Error Details:* `{md.escape_md(detailed_reason)}`" if detailed_reason else ""
    
    return f"{title}\n\n```{table_string}```\n{error_block}".strip()


async def generate_stats_report(session: aiohttp.ClientSession, addr_to_find: str, name: str) -> str:
    """
    Generates a comprehensive statistics report with trend analysis for 15m, 1h, and 24h.
    """
    safe_name = md.escape_md(name)
    try:
        full_leaderboard, health_data = await asyncio.gather(
            api_client.fetch_full_leaderboard(session),
            health_checker.get_health_data(session, addr_to_find)
        )
        
        nodes_for_miner = [node for node in full_leaderboard if node.get('miner','').lower() == addr_to_find.lower()]
        if not nodes_for_miner:
            return f"ℹ️ Miner **{safe_name}** (`{addr_to_find}`) was not found on the leaderboard."

        # Aggregate & Calculate Current Data
        total_ping = sum(n.get('ping_counter', 0) for n in nodes_for_miner)
        last_active = max(n.get('last_active', 0) for n in nodes_for_miner) if nodes_for_miner else 0
        score_points = sum(node.get(key, 0) for node in nodes_for_miner for key in ['requestPoint', 'createPoint', 'preparePoint', 'startPoint', 'precommitPoint', 'commitPoint', 'endPoint', 'correctnessPoint', 'globalPingPoint'])
        
        pre_p, pre_c = sum(n.get('precommitPoint', 0) for n in nodes_for_miner), sum(n.get('precommitCounter', 0) for n in nodes_for_miner)
        com_p, com_c = sum(n.get('commitPoint', 0) for n in nodes_for_miner), sum(n.get('commitCounter', 0) for n in nodes_for_miner)
        prep_p, prep_c = sum(n.get('preparePoint', 0) for n in nodes_for_miner), sum(n.get('prepareCounter', 0) for n in nodes_for_miner)

        current_precommit_rate = utils.calculate_success_rate(pre_p, pre_c)
        current_commit_rate = utils.calculate_success_rate(com_p, com_c)
        current_prepare_rate = utils.calculate_success_rate(prep_p, prep_c)

        # Extract Health Data
        balance = health_data.get('balance', 'N/A') if health_data else 'N/A'
        health_reason = health_data.get('detailed_reason') or health_data.get('reason', 'N/A') if health_data else 'N/A'
        health_bar = health_data.get('health_bar', 'N/A') if health_data else 'N/A'

        # Fetch Historical Data for all timeframes
        historical_data_15m = data_logger.get_historical_data(addr_to_find, 15 * 60) # 15 minutes
        historical_data_1h = data_logger.get_historical_data(addr_to_find, 3600)      # 1 hour
        historical_data_24h = data_logger.get_historical_data(addr_to_find, 24 * 3600) # 24 hours
        
        # --- Initialize all historical variables ---
        old_pre_15m, old_com_15m, old_prep_15m, old_pre_rate_15m, old_com_rate_15m, old_prep_rate_15m = [None] * 6
        old_pre_1h, old_com_1h, old_prep_1h, old_pre_rate_1h, old_com_rate_1h, old_prep_rate_1h = [None] * 6
        old_pre_24h, old_com_24h, old_prep_24h, old_pre_rate_24h, old_com_rate_24h, old_prep_rate_24h = [None] * 6

        if historical_data_15m:
            old_pre_15m, old_com_15m, old_prep_15m = historical_data_15m.get('precommit_points'), historical_data_15m.get('commit_points'), historical_data_15m.get('prepare_points')
            old_pre_rate_15m = utils.calculate_success_rate(old_pre_15m, historical_data_15m.get('precommit_counters'))
            old_com_rate_15m = utils.calculate_success_rate(old_com_15m, historical_data_15m.get('commit_counters'))
            old_prep_rate_15m = utils.calculate_success_rate(old_prep_15m, historical_data_15m.get('prepare_counters'))
            
        if historical_data_1h:
            old_pre_1h, old_com_1h, old_prep_1h = historical_data_1h.get('precommit_points'), historical_data_1h.get('commit_points'), historical_data_1h.get('prepare_points')
            old_pre_rate_1h = utils.calculate_success_rate(old_pre_1h, historical_data_1h.get('precommit_counters'))
            old_com_rate_1h = utils.calculate_success_rate(old_com_1h, historical_data_1h.get('commit_counters'))
            old_prep_rate_1h = utils.calculate_success_rate(old_prep_1h, historical_data_1h.get('prepare_counters'))

        if historical_data_24h:
            old_pre_24h, old_com_24h, old_prep_24h = historical_data_24h.get('precommit_points'), historical_data_24h.get('commit_points'), historical_data_24h.get('prepare_points')
            old_pre_rate_24h = utils.calculate_success_rate(old_pre_24h, historical_data_24h.get('precommit_counters'))
            old_com_rate_24h = utils.calculate_success_rate(old_com_24h, historical_data_24h.get('commit_counters'))
            old_prep_rate_24h = utils.calculate_success_rate(old_prep_24h, historical_data_24h.get('prepare_counters'))
        
        # Assemble the report
        table_lines = [
            f"{'Miner':<20}: {addr_to_find}",
            f"{'Total Points':<20}: {score_points}",
            f"{'Total Pings':<20}: {total_ping}",
            f"{'Balance':<20}: {balance}",
            f"{'Last Active':<20}: {utils.time_ago(last_active)}",
            f"{'Reason':<20}: {health_reason}",
            f"{'Health':<20}: {health_bar}",
            "",
            "--- Success Rates ---",
            f"{'Precommit Success':<20}: {utils.calculate_success_rate(pre_p, pre_c):.2f}% ({pre_p} pts)",
            f"{'Commit Success':<20}: {utils.calculate_success_rate(com_p, com_c):.2f}% ({com_p} pts)",
            f"{'Prepare Success':<20}: {utils.calculate_success_rate(prep_p, prep_c):.2f}% ({prep_p} pts)",
            f"{'Commit/Precommit %':<20}: {utils.calculate_success_rate(com_c, pre_c):.2f}%",
            "",
            # --- NEW: 15-Minute Change Section ---
            "--- Changes (last 15m) ---",
            f"{'Precommit Change':<20}: {get_change_str(current_precommit_rate, old_pre_rate_15m, pre_p, old_pre_15m)}",
            f"{'Commit Change':<20}: {get_change_str(current_commit_rate, old_com_rate_15m, com_p, old_com_15m)}",
            f"{'Prepare Change':<20}: {get_change_str(current_prepare_rate, old_prep_rate_15m, prep_p, old_prep_15m)}",
            "",
            "--- Changes (last 1h) ---",
            f"{'Precommit Change':<20}: {get_change_str(current_precommit_rate, old_pre_rate_1h, pre_p, old_pre_1h)}",
            f"{'Commit Change':<20}: {get_change_str(current_commit_rate, old_com_rate_1h, com_p, old_com_1h)}",
            f"{'Prepare Change':<20}: {get_change_str(current_prepare_rate, old_prep_rate_1h, prep_p, old_prep_1h)}",
            "",
            "--- Changes (last 24h) ---",
            f"{'Precommit Change':<20}: {get_change_str(current_precommit_rate, old_pre_rate_24h, pre_p, old_pre_24h)}",
            f"{'Commit Change':<20}: {get_change_str(current_commit_rate, old_com_rate_24h, com_p, old_com_24h)}",
            f"{'Prepare Change':<20}: {get_change_str(current_prepare_rate, old_prep_rate_24h, prep_p, old_prep_24h)}",
        ]
        
        # --- FOOTER FORMATTING FIXED ---
        health_bar_note = "\n\n*Health bar represents all transactions in the last 30 minutes.*"
        
        trend_note = ""
        if not historical_data_15m: # Show note if the most recent data isn't available yet
            trend_note = "\n*Note: Trend data will be available after the next data snapshot (approx. 15 mins).*"
            
        update_time = f"\n_Last updated: {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M:%S %Z')}_"
        
        title = f"📊 **{safe_name}** Comprehensive Report"
        table_string = "```\n" + "\n".join(table_lines) + "\n```"

        return f"{title}\n\n{table_string}{health_bar_note}{trend_note}{update_time}"

    except Exception as e:
        logger.error(f"Failed to generate stats report for {addr_to_find}: {e}", exc_info=True)
        return f"❌ An error occurred while generating the report for **{safe_name}**."
