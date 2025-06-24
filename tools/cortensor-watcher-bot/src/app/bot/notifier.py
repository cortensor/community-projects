import logging
import threading
import time
from typing import Callable, Dict, Optional, Tuple

import requests

from app.constants import (MSG_CMD_ERROR, MSG_CMD_HELP, MSG_CMD_RESPONSE,
                           MSG_CMD_UNKNOWN, MSG_RESTART, MSG_RESTART_FAILED,
                           MSG_STAGNATION_ALERT, MSG_WATCHER_ERROR,
                           MSG_WATCHER_STARTED, MSG_WATCHER_STOPPED)

class TelegramNotifier:
    def __init__(self, token: Optional[str], chat_id: Optional[str]):
        if not token or not chat_id:
            logging.warning("Telegram token or chat_id is not configured. Notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{token}"
            self.chat_id = chat_id
            self.update_offset = 0
            self.stop_event = threading.Event()

    def _send_request(self, message: str) -> None:
        if not self.enabled: return
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10).raise_for_status()
            logging.info("Successfully sent Telegram notification.")
        except requests.RequestException as e:
            logging.error(f"Could not send Telegram notification: {e}")

    def _poll_for_updates(self, command_callback: Callable[[Dict], None]) -> None:
        logging.info("Telegram command listener started.")
        while not self.stop_event.is_set():
            try:
                url = f"{self.base_url}/getUpdates"
                params = {"offset": self.update_offset, "timeout": 30}
                response = requests.get(url, params=params, timeout=35)
                response.raise_for_status()
                updates = response.json().get("result", [])
                for update in updates:
                    self.update_offset = update["update_id"] + 1
                    if "message" in update and "text" in update["message"]:
                        command_callback(update["message"])
            except requests.RequestException:
                time.sleep(15)
            except Exception as e:
                logging.error(f"An unexpected error in the polling thread: {e}", exc_info=True)
                time.sleep(30)

    def start_update_listener(self, command_callback: Callable[[Dict], None]) -> None:
        if not self.enabled: return
        listener_thread = threading.Thread(target=self._poll_for_updates, args=(command_callback,), daemon=True)
        listener_thread.start()

    def stop_listener(self) -> None:
        if self.enabled:
            logging.info("Stopping Telegram command listener...")
            self.stop_event.set()

    def send_restart_alert(self, cid: str, reason: str, details: str, timestamp: str) -> None:
        self._send_request(MSG_RESTART.format(cid=cid, reason=reason, details=details, timestamp=timestamp))

    def send_stagnation_alert(self, pair: Tuple[int, int], duration: int) -> None:
        self._send_request(MSG_STAGNATION_ALERT.format(pair=pair, duration=duration))

    def send_command_response(self, response_text: str) -> None:
        self._send_request(MSG_CMD_RESPONSE.format(response=response_text))

    def send_unknown_command_response(self) -> None:
        self._send_request(MSG_CMD_UNKNOWN)

    def send_help_response(self) -> None:
        self._send_request(MSG_CMD_HELP)

    def send_watcher_start_message(self) -> None:
        self._send_request(MSG_WATCHER_STARTED)

    def send_watcher_stop_message(self) -> None:
        self._send_request(MSG_WATCHER_STOPPED)

    def send_watcher_error_message(self, error: Exception) -> None:
        self._send_request(MSG_CMD_ERROR.format(error=str(error)))
