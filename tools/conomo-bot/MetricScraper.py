import asyncio
import schedule
# from pyppeteer import launch
# from bs4 import BeautifulSoup
from Metric import Metric #, KNOWN_METRIC_NAMES
import logging
import sqlite3
# from itertools import batched
from BotConfig import BotConfig
import requests


BOT_CONFIG = BotConfig()
logger = logging.getLogger("MetricScraper")


class MetricScraper:
    def __init__(self, callback):
        """Initialize the scraper with callback"""
        self.callback = callback

    
    def scrape_metrics(self, addresses = []) -> dict[str, list[Metric]]:
        """Scrape a single page and extract data."""
        logger.info("Sraping metrics")
            
        result = dict()
        leaderboard = []
        try:
            response = requests.get(BOT_CONFIG.COR_LEADERBOARD_URL)
            if response.status_code == 200:
                leaderboard = response.json()
        except Exception as e:
            logger.exception("Failed to fetch leaderboard")
            return result
        
        metric_names = ["create", "prepare", "precommit", "commit"]
        
        for miner in leaderboard:
            address = miner["miner"].lower()
            if addresses and address not in addresses:
                continue

            metrics = []
            data = miner["nodes"][0]

            metrics.append(Metric("Last Active", counter=data["last_active"], visible=False))
            metrics.append(Metric("Ping", counter=data["ping_counter"]))
            metrics.append(Metric("Global Ping", points=data["globalPingPoint"]))

            for name in metric_names:
                metric = Metric(name.capitalize(), data[name + "Point"], data[name + "Counter"])
                metrics.append(metric)

            result[address] = metrics
            
        return result
    

    async def get_addresses(self, chat_id) -> list[str]:
        with sqlite3.connect(BOT_CONFIG.BOT_DB_FILE) as con:
            try:
                cur = con.cursor()
                cur.row_factory = lambda _, row: row[0]
                sql = "SELECT DISTINCT chat_node.node_address FROM chat_node LEFT JOIN chat ON chat_node.chat_id = chat.chat_id AND (chat.active = 1 OR chat.active IS NULL) "
                
                params = ()
                if chat_id:
                    sql += "AND chat.chat_id = ?"
                    params = (chat_id,)
                
                return cur.execute(sql, params).fetchall()
            except Exception:
                logger.exception("Failed to fetch node addresses from db.")
                return []
            finally:
                cur.close()


    async def scrape_all(self):
        """Scrape all URLs concurrently."""
        logger.info("Scraping metrics...")
        addresses = await self.get_addresses(None)
        await self.scrape_addresses(addresses)


    # async def scrape_chat_id(self, chat_id):
    #     """Scrape all URLs concurrently."""
    #     logger.info(f"Scraping metrics for chat_id {chat_id}...")
    #     addresses = await self.get_addresses(chat_id)
    #     await self.scrape_addresses(addresses)


    def scrape_address(self, address) -> list[Metric]:
        logger.info(f"Scraping metrics for address: {address}")

        return self.scrape_metrics([address]).get(address, [])


    async def scrape_addresses(self, addresses):
        """Scrape all URLs concurrently."""
        logger.info(f"Scraping metrics for addresses: {addresses}")

        result_dict = self.scrape_metrics(addresses)

        logger.info("Calling scraper callback")
        await self.callback(result_dict)

    # async def scrape_addresses(self, addresses):
    #     """Scrape all URLs concurrently."""
    #     logger.info(f"Scraping metrics for addresses: {addresses}")
    #     results = []
    #     for batch in batched(addresses, 3):
    #         tasks = [self.scrape_metrics_for_address(address[0]) for address in batch]
    #         batch_results = await asyncio.gather(*tasks)
    #         results.extend(batch_results)

    #     result_dict = dict()
    #     for metrics, address in results:
    #         result_dict[address] = metrics

    #     logger.info("Calling scraper callback")
    #     await self.callback(result_dict)


    def schedule_scraping(self):
        """Schedule scraping exactly 4 times per day."""
        
        # schedule.every().day.at(time_str="21:49").do(lambda: asyncio.create_task(self.scrape_all())) # , tz="UTC"
        # schedule.every().day.at(time_str="21:19", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))


        # schedule.every().minute.do(lambda: asyncio.create_task(self.scrape_all()))

        # schedule.every().day.at("00:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("06:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("12:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("18:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        
        # schedule.every().day.at("00:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("04:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("08:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("12:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("16:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("20:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))

        # TODO: loop oneliner
        # schedule.every().day.at("00:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("03:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("06:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("09:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("12:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("15:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("18:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))
        # schedule.every().day.at("21:00", tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))


        for i in range(0, 24, 3):
            time_str = f"{i:02d}:00"
            schedule.every().day.at(time_str, tz="UTC").do(lambda: asyncio.create_task(self.scrape_all()))

        print("Scraper scheduled to run at 00:00, 06:00, 12:00, 18:00.")

    async def run_scheduler(self):
        """Run the scheduled tasks asynchronously."""
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # Non-blocking wait


    async def run(self):
        """Start the scraper and keep it running."""
        # await self.start_browser()  # Ensure browser is started
        self.schedule_scraping()  # Schedule tasks
        # first time scrape
        asyncio.create_task(self.scrape_all())

        try:
            await self.run_scheduler()  # Run scheduler
        except KeyboardInterrupt:
            await self.close_browser()  # Ensure browser closes on exit
