# File: api_checker.py
"""
api_checker.py

Periodically scrapes the Cortensor dashboard to extract the "Failures" and "Timestamp" columns for each node.
Runs at a configurable interval per-container, staggered by initial offset.
If a new timestamped failure entry is detected (i.e., newer timestamp than last seen), signals to restart.
Initial scrape seeds the baseline without triggering a restart.
Uses system-installed chromium & chromedriver for Selenium.
"""
import os
import time
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Path to the chromedriver binary installed via system package
DRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/lib/chromium/chromedriver")


def fetch_failures_with_timestamps(node_address: str, metric: str = "Precommit", headless: bool = True) -> list[tuple[datetime, int]]:
    """
    Loads Cortensor dashboard for a node+metric, extracts pairs of (timestamp, failures) from the table.
    Returns a list of tuples.
    """
    url = f"https://dashboard-devnet5.cortensor.network/stats/node/{node_address}?metric={metric}"
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    service = Service()  # expect chromedriver in PATH
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url)
        # wait for JS-rendered table
        time.sleep(5)
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        if not rows:
            return []
        # Determine column indices
        headers = [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")]
        try:
            ts_idx = next(i for i,h in enumerate(headers) if 'time' in h.lower())
        except StopIteration:
            return []
        try:
            fail_idx = headers.index("Failures")
        except ValueError:
            return []
        data = []
        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) <= max(ts_idx, fail_idx):
                continue
            ts_text = cells[ts_idx].text.strip()
            # parse timestamp; assume ISO-like or common formats
            try:
                ts = datetime.fromisoformat(ts_text)
            except Exception:
                try:
                    ts = datetime.strptime(ts_text, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
            fail_txt = cells[fail_idx].text.strip().replace(',', '')
            try:
                failures = int(float(fail_txt))
            except ValueError:
                failures = 0
            data.append((ts, failures))
        return data
    finally:
        driver.quit()


class ApiChecker:
    def __init__(self, metric: str = "Precommit", headless: bool = True, interval_s: int = 120):
        self.metric = metric
        self.headless = headless
        self.interval = timedelta(seconds=interval_s)
        self.node_address: dict[str, str] = {}
        self.last_seen: dict[str, datetime|None] = {}
        self.next_check: dict[str, datetime] = {}

    def init_container(self, container_name: str, node_address: str, offset_s: int):
        """Initialize tracking for a container, staggered by offset_s seconds."""
        now = datetime.now(timezone.utc)
        self.node_address[container_name] = node_address
        # seed baseline timestamp as None so first scrape does not restart
        self.last_seen[container_name] = None
        # schedule first check after offset
        self.next_check[container_name] = now + timedelta(seconds=offset_s)

    def check(self, container_name: str) -> bool:
        """
        If it's time, scrape failures with timestamps and compare to last. Return True if new timestamp > last_seen.
        """
        now = datetime.now(timezone.utc)
        # not time yet
        if now < self.next_check.get(container_name, now):
            return False
        # schedule next check
        self.next_check[container_name] = now + self.interval
        addr = self.node_address.get(container_name)
        if not addr:
            return False
        entries = fetch_failures_with_timestamps(addr, metric=self.metric, headless=self.headless)
        if not entries:
            return False
        # find the latest by timestamp
        entries.sort(key=lambda x: x[0])
        latest_ts, latest_fail = entries[-1]
        prev_ts = self.last_seen.get(container_name)
        # seed baseline on first run
        if prev_ts is None:
            self.last_seen[container_name] = latest_ts
            return False
        # restart on any new timestamped entry
        if latest_ts > prev_ts:
            self.last_seen[container_name] = latest_ts
            return True
        return False
