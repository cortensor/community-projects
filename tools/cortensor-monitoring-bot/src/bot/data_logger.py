# bot/data_logger.py
import logging
import sqlite3
import time
from typing import Dict, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.bot.bot import Bot
from . import api_client

logger = logging.getLogger(__name__)
HISTORY_DB_FILE = "history.db"

def setup_history_db() -> None:
    """
    Creates the history database and the leaderboard_history table if they don't exist.
    This function also creates an index for faster queries.
    """
    try:
        with sqlite3.connect(HISTORY_DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard_history (
                    timestamp INTEGER NOT NULL,
                    miner_address TEXT NOT NULL,
                    precommit_points INTEGER,
                    precommit_counters INTEGER,
                    commit_points INTEGER,
                    commit_counters INTEGER,
                    prepare_points INTEGER,
                    prepare_counters INTEGER,
                    PRIMARY KEY(timestamp, miner_address)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_miner_history ON leaderboard_history (miner_address, timestamp);")
            logger.info("History database and table have been verified.")
    except sqlite3.Error as e:
        logger.error(f"History database setup failed: {e}", exc_info=True)
        raise

async def log_leaderboard_snapshot(bot: Bot) -> None:
    """
    Fetches the entire leaderboard, aggregates node data per miner,
    and logs the snapshot to the history database.
    
    :param bot: The aiogram Bot instance, used to get the shared aiohttp session.
    """
    logger.info("Running periodic leaderboard snapshot job...")
    session = bot.get("session")
    try:
        leaderboard_data = await api_client.fetch_full_leaderboard(session)
        if not leaderboard_data:
            logger.warning("Skipping snapshot job: Leaderboard data is empty or could not be fetched.")
            return

        timestamp = int(time.time())
        aggregated_records: Dict[str, Dict[str, int]] = {}
        
        # Aggregate data for miners who may have multiple nodes
        for node_data in leaderboard_data:
            miner_addr = node_data.get('miner')
            if not miner_addr:
                continue
            miner_addr = miner_addr.lower()

            if miner_addr not in aggregated_records:
                aggregated_records[miner_addr] = {
                    'precommit_points': 0, 'precommit_counters': 0,
                    'commit_points': 0, 'commit_counters': 0,
                    'prepare_points': 0, 'prepare_counters': 0,
                }
            
            # Sum points and counters from each node
            aggregated_records[miner_addr]['precommit_points'] += node_data.get('precommitPoint', 0)
            aggregated_records[miner_addr]['precommit_counters'] += node_data.get('precommitCounter', 0)
            aggregated_records[miner_addr]['commit_points'] += node_data.get('commitPoint', 0)
            aggregated_records[miner_addr]['commit_counters'] += node_data.get('commitCounter', 0)
            aggregated_records[miner_addr]['prepare_points'] += node_data.get('preparePoint', 0)
            aggregated_records[miner_addr]['prepare_counters'] += node_data.get('prepareCounter', 0)
        
        # Prepare records for bulk insertion
        final_records_to_insert = [
            (timestamp, miner, data['precommit_points'], data['precommit_counters'],
             data['commit_points'], data['commit_counters'], data['prepare_points'], data['prepare_counters'])
            for miner, data in aggregated_records.items()
        ]

        # Insert all records into the history database
        if final_records_to_insert:
            with sqlite3.connect(HISTORY_DB_FILE) as conn:
                conn.executemany("""
                    INSERT OR IGNORE INTO leaderboard_history (
                        timestamp, miner_address, precommit_points, precommit_counters, 
                        commit_points, commit_counters, prepare_points, prepare_counters
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, final_records_to_insert)
                logger.info(f"Successfully logged {len(final_records_to_insert)} miner snapshots to history.db.")
        else:
            logger.info("No records to log in this snapshot.")

    except Exception as e:
        logger.error(f"An error occurred in the leaderboard snapshot job: {e}", exc_info=True)

def get_historical_data(addr: str, time_ago_seconds: int) -> Optional[Dict]:
    """
    Retrieves the closest historical data point from the database for a given address
    at a specific time in the past.

    :param addr: The miner address to query.
    :param time_ago_seconds: The number of seconds in the past to search from (e.g., 3600 for 1 hour).
    :return: A dictionary representing the database row, or None if no data is found.
    """
    target_timestamp = int(time.time()) - time_ago_seconds
    try:
        with sqlite3.connect(HISTORY_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Find the most recent record that is on or before the target timestamp
            cursor.execute("""
                SELECT * FROM leaderboard_history 
                WHERE miner_address = ? AND timestamp <= ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (addr.lower(), target_timestamp))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Failed to get historical data for {addr}: {e}", exc_info=True)
        return None

def schedule_logging_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """
    Adds the background data logging job to the APScheduler instance.

    :param scheduler: The AsyncIOScheduler instance.
    :param bot: The aiogram Bot instance to pass to the job.
    """
    scheduler.add_job(
        log_leaderboard_snapshot,
        'interval',
        minutes=15,
        kwargs={'bot': bot},
        id='leaderboard_snapshot_job' # Assign a unique ID
    )
    logger.info("Leaderboard snapshot job has been scheduled to run every 15 minutes.")
