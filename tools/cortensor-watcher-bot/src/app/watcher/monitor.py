import logging
import re
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, Optional, Tuple

import docker
from docker.models.containers import Container
from docker.errors import NotFound, DockerException

from app.bot.notifier import TelegramNotifier
from app.constants import (
    LOG_DIR,
    WATCHER_LOG_FILE,
    MSG_HELP,
    RE_LOG_STATE,
    RE_EVENT_STATS,
    RE_TASK_MODE
)

class NodeMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notifier = TelegramNotifier(
            token=config.get("telegram_bot_token"),
            chat_id=config.get("telegram_chat_id"),
        )
        try:
            self.docker_client = docker.from_env()
        except DockerException as e:
            logging.critical(f"Could not connect to Docker: {e}")
            exit(1)

        self.container_states = self._load_state()
        self.majority_state = None
        self.last_cycle_statuses = {}

    def _load_state(self) -> Dict[str, Any]:
        """Loads state from a JSON file for persistence."""
        state_file = Path("state_data/watcher_state.json")
        if not state_file.exists():
            return defaultdict(dict)
        
        logging.info(f"Loading state from {state_file}")
        with state_file.open("r", encoding="utf-8") as f:
            try:
                content = f.read()
                return defaultdict(dict, json.loads(content)) if content else defaultdict(dict)
            except json.JSONDecodeError:
                logging.error(f"Could not decode JSON from {state_file}. Starting fresh.")
                return defaultdict(dict)

    def _save_state(self) -> None:
        """Saves the current state to a JSON file."""
        state_file = Path("state_data/watcher_state.json")
        state_file.parent.mkdir(exist_ok=True)
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(self.container_states, f, indent=4, default=str)

    def _get_full_node_status(self, container: Container) -> Dict[str, Any]:
        """Reads all relevant statuses from a node's logs."""
        status = {
            "id_state": None,
            "last_event": "Unknown",
            "task_mode": "Unknown"
        }
        try:
            logs = container.logs(tail=250).decode("utf-8", errors="ignore")
            
            id_state_match = list(RE_LOG_STATE.finditer(logs))
            if id_state_match:
                status["id_state"] = (int(id_state_match[-1].group(1)), int(id_state_match[-1].group(2)))

            task_mode_match = list(RE_TASK_MODE.finditer(logs))
            if task_mode_match:
                raw_mode = task_mode_match[-1].group(1)
                clean_mode = re.sub(r'\[\d+m', '', raw_mode).replace('[0m', '').strip()
                status["task_mode"] = clean_mode

            event_stats_match = list(RE_EVENT_STATS.finditer(logs))
            if event_stats_match:
                stats_str = event_stats_match[-1].group(1).replace("'", '"')
                stats_dict = json.loads(stats_str)
                for event, count in reversed(list(stats_dict.items())):
                    if count > 0:
                        status["last_event"] = event
                        break
        except Exception as e:
            logging.error(f"Could not parse full status for {container.name}: {e}")
        return status

    def _manage_container(self, container_name: str, action: str) -> str:
        """Handles start, stop, and restart actions with pre-checks."""
        try:
            container = self.docker_client.containers.get(container_name)
            
            if action == "start":
                if container.status == "running":
                    return f"ℹ️ Container <code>{container_name}</code> is already running."
                container.start()
                return f"✅ Container <code>{container_name}</code> started successfully."
            
            elif action == "stop":
                if container.status != "running":
                    return f"ℹ️ Container <code>{container_name}</code> is already stopped (status: {container.status})."
                container.stop()
                return f"✅ Container <code>{container_name}</code> stopped successfully."

            elif action == "restart":
                container.restart()
                return f"✅ Container <code>{container_name}</code> restarted successfully."

        except NotFound:
            return f"❌ Container <code>{container_name}</code> not found."
        except Exception as e:
            logging.error(f"Failed to {action} {container_name}: {e}")
            return f"❌ Failed to {action} container <code>{container_name}</code>."

    def run(self):
        """Main monitoring loop with enhanced status logic."""
        self.notifier.send_watcher_start_message()
        self.notifier.start_update_listener(self._handle_command)

        while True:
            logging.info("Starting new monitoring cycle...")
            containers_to_monitor = self.config.get("containers", [])
            grace_period = self.config.get("grace_period_seconds", 300)

            self.last_cycle_statuses = {}
            for cid in containers_to_monitor:
                try:
                    container = self.docker_client.containers.get(cid)
                    # Get status even for non-running containers for the /status command
                    self.last_cycle_statuses[cid] = self._get_full_node_status(container)
                except Exception as e:
                    logging.error(f"Failed to get status for '{cid}': {e}")
            logging.info(f"Gathered statuses: {self.last_cycle_statuses}")

            valid_states = [s['id_state'] for s in self.last_cycle_statuses.values() if s.get('id_state') is not None]
            self.majority_state = Counter(valid_states).most_common(1)[0][0] if valid_states else None
            logging.info(f"Calculated majority state: {self.majority_state}")

            if self.majority_state:
                now = datetime.now(timezone.utc)
                for cid, status in self.last_cycle_statuses.items():
                    if cid not in self.container_states:
                        self.container_states[cid] = {}
                        
                    id_state = status.get('id_state')
                    if id_state is None:
                        if self.container_states[cid].get('deviation_start_time'):
                            self.container_states[cid]['deviation_start_time'] = None
                        continue
                    
                    if id_state != self.majority_state:
                        if not self.container_states[cid].get('deviation_start_time'):
                            self.container_states[cid]['deviation_start_time'] = now.isoformat()
                            logging.warning(f"Node '{cid}' state {id_state} deviates from majority. Starting timer.")
                        else:
                            start_time = datetime.fromisoformat(self.container_states[cid]['deviation_start_time'])
                            if (now - start_time).total_seconds() > grace_period:
                                logging.error(f"Node '{cid}' has deviated for too long. Taking action.")
                                self.container_states[cid]['deviation_start_time'] = None 
                    else:
                        if self.container_states[cid].get('deviation_start_time'):
                            logging.info(f"Node '{cid}' returned to majority state.")
                            self.container_states[cid]['deviation_start_time'] = None

            self._save_state()
            interval = self.config.get("check_interval_seconds", 60)
            logging.info(f"Cycle finished. Waiting for {interval} seconds.")
            time.sleep(interval)

    def _handle_command(self, message: Dict):
        """Handles incoming Telegram commands."""
        text = message.get("text", "")
        parts = text.split()
        command = parts[0].lower()
        args = parts[1:]
        logging.info(f"Received command: {command} with args: {args}")

        try:
            if command == "/status":
                self._handle_status_command()
            elif command == "/help":
                self.notifier.send_help_response()
            elif command in ["/start", "/stop", "/restart"]:
                # If /start is used without args, show help.
                if command == "/start" and not args:
                    self.notifier.send_help_response()
                    return
                # For other commands, show usage.
                if not args:
                    self.notifier.send_command_response(f"Usage: <code>{command} &lt;container_name&gt;</code>")
                    return
                
                action = command.strip('/')
                response = self._manage_container(args[0], action)
                self.notifier.send_command_response(response)
            elif command == "/logs":
                self._handle_logs_command(args)
            elif command == "/resources":
                self._handle_resources_command(args)
            else:
                self.notifier.send_unknown_command_response()
        except Exception as e:
            logging.error(f"Error handling command '{command}': {e}", exc_info=True)
            self.notifier.send_command_response("An internal error occurred.")

    def _get_container_logs(self, container_name: str, lines: int) -> str:
        """Retrieves the latest logs from a container."""
        try:
            container = self.docker_client.containers.get(container_name)
            logs = container.logs(tail=lines).decode("utf-8", errors="ignore").replace("<", "&lt;").replace(">", "&gt;")
            return f"<b>Logs for <code>{container_name}</code> ({lines} lines):</b>\n<pre>{logs}</pre>"
        except NotFound:
            return f"❌ Container <code>{container_name}</code> not found."
        except Exception as e:
            logging.error(f"Failed to get logs for {container_name}: {e}")
            return f"❌ Failed to retrieve logs for <code>{container_name}</code>."

    def _get_resource_usage(self, container_name: str) -> str:
        """Retrieves CPU and Memory usage from a container."""
        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            number_cpus = stats['cpu_stats'].get('online_cpus', 1)
            cpu_usage_percent = (cpu_delta / system_cpu_delta) * number_cpus * 100.0 if system_cpu_delta > 0 else 0
            mem_usage = stats['memory_stats'].get('usage', 0) / (1024 * 1024)
            mem_limit = stats['memory_stats'].get('limit', 0) / (1024 * 1024)
            return (f"📊 <b>Resource Usage for <code>{container_name}</code>:</b>\n"
                    f"  - <b>CPU:</b> {cpu_usage_percent:.2f}%\n"
                    f"  - <b>Memory:</b> {mem_usage:.2f} MB / {mem_limit:.2f} MB")
        except NotFound:
            return f"❌ Container <code>{container_name}</code> not found."
        except Exception as e:
            logging.error(f"Failed to get resource stats for {container_name}: {e}")
            return f"⚠️ Could not retrieve resource usage for <code>{container_name}</code>."

    def _handle_status_command(self):
        """Handles the /status command logic."""
        header = f"<b>📊 Node Status Report</b>\n\nMajority State: <code>{self.majority_state or 'Not Calculated'}</code>"
        self.notifier.send_command_response(header)
        time.sleep(0.2)
        
        if not self.last_cycle_statuses:
            self.notifier.send_command_response("Status data not available yet.")
            return

        for cid, status in sorted(self.last_cycle_statuses.items()):
            sync_status = "✅ Synced"
            id_state = status.get('id_state')

            if id_state is None:
                sync_status = "ℹ️ No State Data"
            elif self.majority_state and id_state != self.majority_state:
                sync_status = "❌ Deviating"
            
            node_report = (
                f"--- <b>{cid}</b> ---\n"
                f"  - Mode: <code>{status.get('task_mode')}</code>\n"
                f"  - Last Event: <code>{status.get('last_event')}</code>\n"
                f"  - ID/State: <code>{id_state or 'N/A'}</code>\n"
                f"  - Sync: {sync_status}"
            )
            self.notifier.send_command_response(node_report)
            time.sleep(0.1)

    def _handle_logs_command(self, args: list):
        """Handles the /logs command logic."""
        if not args:
            for cid in sorted(self.config.get("containers", [])):
                response = self._get_container_logs(cid, 25)
                self.notifier.send_command_response(response)
                time.sleep(0.1)
        else:
            lines = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
            response = self._get_container_logs(args[0], lines)
            self.notifier.send_command_response(response)

    def _handle_resources_command(self, args: list):
        """Handles the /resources command logic."""
        if not args:
            for cid in sorted(self.config.get("containers", [])):
                response = self._get_resource_usage(cid)
                self.notifier.send_command_response(response)
                time.sleep(0.1)
        else:
            response = self._get_resource_usage(args[0])
            self.notifier.send_command_response(response)
