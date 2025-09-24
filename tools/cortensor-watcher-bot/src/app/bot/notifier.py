import logging
import threading
import time
from typing import Callable, Dict, Optional

import requests

from app.constants import (
    MSG_CMD_ERROR,
    MSG_HELP,  # <-- Corrected from MSG_CMD_HELP
    MSG_CMD_RESPONSE,
    MSG_CMD_UNKNOWN,
    MSG_RESTART,
    MSG_STAGNATION_ALERT,
    MSG_DEVIATION_ALERT,
    MSG_WATCHER_ERROR,
    MSG_WATCHER_STARTED,
    MSG_WATCHER_STOPPED,
    MSG_STALE_NODE_ALERT
)

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
            self._max_len = 4096  # Telegram sendMessage text limit

    def _post_message(self, message: str) -> None:
        """Send a single message to Telegram (no splitting)."""
        if not self.enabled:
            return
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logging.debug("Successfully sent Telegram notification.")
        except requests.RequestException as e:
            logging.error(f"Could not send Telegram notification: {e}")

    def _send_request(self, message: str) -> None:
        """Send message; split into chunks if it exceeds Telegram size limits."""
        if not self.enabled:
            return

        # Fast path if within limits
        if len(message) <= self._max_len:
            self._post_message(message)
            return

        # Attempt to split around <pre> blocks (logs or models) to preserve formatting
        try:
            pre_start = message.find("<pre>")
            pre_end = message.rfind("</pre>")
            if pre_start != -1 and pre_end != -1 and pre_end > pre_start:
                header = message[:pre_start]
                content = message[pre_start + len("<pre>"):pre_end]
                footer = message[pre_end + len("</pre>"):]

                # Send header if present
                if header.strip():
                    if len(header) > self._max_len:
                        self._post_message(header[: self._max_len - 10] + "…")
                    else:
                        self._post_message(header)

                # Split content by newline into safe chunks wrapped with <pre>
                safe_limit = self._max_len - 20  # leave room for <pre></pre>
                buf = []
                current_len = 0
                for line in content.splitlines(True):  # keepends=True
                    if current_len + len(line) > safe_limit and buf:
                        self._post_message("<pre>" + "".join(buf) + "</pre>")
                        buf = []
                        current_len = 0
                    # If a single line exceeds safe_limit, hard-split it
                    while len(line) > safe_limit:
                        self._post_message("<pre>" + line[:safe_limit] + "</pre>")
                        line = line[safe_limit:]
                    buf.append(line)
                    current_len += len(line)
                if buf:
                    self._post_message("<pre>" + "".join(buf) + "</pre>")

                # Send footer if present
                if footer.strip():
                    if len(footer) > self._max_len:
                        self._post_message(footer[: self._max_len - 10] + "…")
                    else:
                        self._post_message(footer)
                return
        except Exception as e:
            logging.warning(f"Falling back to generic split due to error while splitting <pre> block: {e}")

        # Generic split by length at newline boundaries
        safe_limit = self._max_len - 10
        text = message
        while text:
            if len(text) <= safe_limit:
                self._post_message(text)
                break
            # find last newline within limit
            cut = text.rfind("\n", 0, safe_limit)
            if cut == -1:
                cut = safe_limit
            chunk = text[:cut]
            self._post_message(chunk)
            text = text[cut:]

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
                logging.error(f"An unexpected error occurred in the Telegram polling thread: {e}", exc_info=True)
                time.sleep(30)

    def start_update_listener(self, command_callback: Callable[[Dict], None]) -> None:
        if not self.enabled:
            return
        listener_thread = threading.Thread(target=self._poll_for_updates, args=(command_callback,), daemon=True)
        listener_thread.start()

    def stop_listener(self) -> None:
        if self.enabled and self.stop_event:
            logging.info("Stopping Telegram command listener...")
            self.stop_event.set()

    def send_restart_alert(self, cid: str, reason: str, details: str, timestamp: str, logs: str) -> None:
        message = MSG_RESTART.format(cid=cid, reason=reason, details=details, timestamp=timestamp, logs=logs)
        self._send_request(message)

    def send_stagnation_alert(self, pair: tuple, duration: int) -> None:
        message = MSG_STAGNATION_ALERT.format(pair=pair, duration=duration)
        self._send_request(message)

    def send_stale_node_alert(self, cid: str, duration: int) -> None:
        message = MSG_STALE_NODE_ALERT.format(cid=cid, duration=duration)
        self._send_request(message)

    def send_deviation_alert(self, cid: str, node_state: str, majority_state: str, minutes: int) -> None:
        message = MSG_DEVIATION_ALERT.format(cid=cid, node_state=node_state, majority_state=majority_state, minutes=minutes)
        self._send_request(message)

    def send_command_response(self, response_text: str) -> None:
        message = MSG_CMD_RESPONSE.format(response=response_text)
        self._send_request(message)

    def send_unknown_command_response(self) -> None:
        self._send_request(MSG_CMD_UNKNOWN)

    def send_help_response(self) -> None:
        self._send_request(MSG_HELP)  # <-- Corrected from MSG_CMD_HELP

    def send_watcher_start_message(self) -> None:
        self._send_request(MSG_WATCHER_STARTED)

    def send_watcher_stop_message(self) -> None:
        self._send_request(MSG_WATCHER_STOPPED)

    def send_watcher_error_message(self, error: Exception) -> None:
        error_str = str(error).replace("<", "&lt;").replace(">", "&gt;")
        message = MSG_WATCHER_ERROR.format(error=error_str)
        self._send_request(message)
