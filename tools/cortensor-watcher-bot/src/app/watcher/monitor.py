import json
import logging
import os
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import docker
import requests
from docker.models.containers import Container

from app.bot.notifier import TelegramNotifier
from app.constants import (LOG_DIR, MSG_CMD_ERROR, MSG_CMD_HELP,
                           MSG_CMD_UNKNOWN, PATTERN_PING_FAIL,
                           PATTERN_TRACEBACK, RE_LOG_STATE, WARMUP_SECONDS,
                           WATCHER_LOG_FILE)

STATE_FILE_PATH = Path("./state_data/watcher_state.json")

class NodeMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = self._connect_to_docker()
        self.start_time = datetime.now(timezone.utc)
        self.notifier = TelegramNotifier(
            token=self.config.get("telegram_bot_token"),
            chat_id=self.config.get("telegram_chat_id")
        )
        self.notifier.start_update_listener(self._handle_telegram_command)

        STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        self.container_states: Dict[str, Dict[str, Any]] = {}
        self._load_state() 

        for cid in self.config.get("containers", []):
            if cid not in self.container_states:
                self.container_states[cid] = {
                    "state_deviation_start_time": None,
                    "id_lag_start_time": None,
                    "warmed_up": False,
                    "ignored_failures_at": {}
                }
        
        self.last_seen_majority_pair: Optional[Tuple[int, int]] = None
        self.majority_stagnation_start_time: Optional[datetime] = None
        self.alert_sent_for_stagnant_pair: Optional[Tuple[int, int]] = None
        
        LOG_DIR.mkdir(exist_ok=True)
        if not WATCHER_LOG_FILE.exists():
            WATCHER_LOG_FILE.touch()

    def _load_state(self):
        try:
            if STATE_FILE_PATH.exists():
                logging.info(f"Loading previous state from {STATE_FILE_PATH}...")
                with STATE_FILE_PATH.open("r") as f:
                    self.container_states = json.load(f)
                for state_data in self.container_states.values():
                    for key in ["state_deviation_start_time", "id_lag_start_time"]:
                        if state_data.get(key):
                            state_data[key] = datetime.fromisoformat(state_data[key])
        except Exception as e:
            logging.error(f"Could not load state file, starting fresh. Error: {e}")
            self.container_states = {}

    def _save_state(self):
        try:
            serializable_state = json.loads(json.dumps(self.container_states, default=str))
            with STATE_FILE_PATH.open("w") as f:
                json.dump(serializable_state, f, indent=2)
            logging.info(f"Successfully saved state to {STATE_FILE_PATH}")
        except Exception as e:
            logging.error(f"Could not save state file. Error: {e}")

    def _connect_to_docker(self) -> docker.DockerClient:
        try:
            client = docker.from_env()
            client.ping()
            logging.info("Successfully connected to Docker daemon.")
            return client
        except Exception as e:
            logging.critical(f"Cannot connect to Docker daemon: {e}")
            sys.exit(1)

    def _restart_container(self, container: Container, reason: str, details: str = "", failed_tasks_info: Optional[Dict] = None) -> None:
        cid = container.name
        now_utc = datetime.now(timezone.utc)
        logging.warning(f"Restarting container '{cid}'. Reason: {reason}. {details}")
        timestamp_str = now_utc.strftime("%Y%m%dT%H%M%S")
        log_filename = f"{cid}_{reason.lower().replace(' ', '_')}_{timestamp_str}.log"
        log_path = LOG_DIR / log_filename
        try:
            log_content = container.logs(tail=500).decode("utf-8", errors="ignore")
            log_path.write_text(log_content, encoding="utf-8")
        except Exception as e:
            logging.error(f"Failed to write restart log for '{cid}': {e}")
        event_log_entry = (f"{now_utc.isoformat()} | RESTART | {cid} | {reason} | {details}\n")
        with WATCHER_LOG_FILE.open("a", encoding="utf-8") as f: f.write(event_log_entry)
        self.notifier.send_restart_alert(cid=cid, reason=reason, details=details, timestamp=now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'))
        
        if cid in self.container_states:
            state_info = self.container_states[cid]
            state_info["state_deviation_start_time"], state_info["id_lag_start_time"] = None, None
            if reason == "Reputation Failure" and failed_tasks_info:
                state_info["ignored_failures_at"] = failed_tasks_info
                logging.info(f"Ignoring {len(failed_tasks_info.get('precommit', []))} precommit and {len(failed_tasks_info.get('commit', []))} commit failures for '{cid}'.")
            self._save_state()
        try:
            container.restart(timeout=30)
            logging.info(f"Restart command sent successfully to '{cid}'.")
        except Exception as e:
            logging.error(f"Failed to restart container '{cid}': {e}")
            self.notifier.send_restart_failure_alert(cid)
            
    def _check_reputation(self) -> None:
        if not self.config.get("reputation_check_enabled"): return
        logging.info("Performing Reputation Health Check...")
        base_url = self.config.get("reputation_api_base_url", "").rstrip('/')
        window = self.config.get("reputation_check_window", 20)
        threshold = self.config.get("reputation_failure_threshold", 5)
        node_addresses = self.config.get("node_addresses", {})
        for cid, address in node_addresses.items():
            state_info = self.container_states.get(cid)
            if not (state_info and state_info.get("warmed_up")): continue
            api_url = f"{base_url}/{address}"
            try:
                container = self.client.containers.get(cid)
                response = requests.get(api_url, timeout=10)
                if response.status_code != 200:
                    logging.warning(f"Reputation API for '{cid}' returned status {response.status_code}."); continue
                data = response.json()
                for stage in ["precommit", "commit"]:
                    stage_data = data.get(stage, {})
                    all_ts, success_ts = stage_data.get("all_timestamps", []), stage_data.get("success_timestamps", [])
                    if not all_ts: continue
                    recent_tasks, successful_tasks = set(all_ts[-window:]), set(success_ts)
                    current_failures = recent_tasks - successful_tasks
                    failure_count = len(current_failures)
                    ignored_failures_list = state_info.get("ignored_failures_at", {}).get(stage, [])
                    ignored_failures = set(ignored_failures_list)
                    if failure_count < threshold and ignored_failures:
                        logging.info(f"Node '{cid}' ({stage}) is now healthy. Clearing ignored failures list.")
                        state_info.get("ignored_failures_at", {}).pop(stage, None)
                        self._save_state()
                        ignored_failures.clear()
                    if failure_count > 0:
                        logging.info(f"Reputation Check for '{cid}' ({stage}): Found {failure_count} total failed tasks. Ignoring {len(ignored_failures)} known failures.")
                    new_unseen_failures = current_failures - ignored_failures
                    if failure_count >= threshold and len(new_unseen_failures) > 0:
                        details = f"Node had {failure_count} total failed {stage} tasks, including {len(new_unseen_failures)} new failure(s)."
                        failed_tasks_info_to_save = state_info.get("ignored_failures_at", {})
                        failed_tasks_info_to_save[stage] = list(current_failures)
                        self._restart_container(container, "Reputation Failure", details, failed_tasks_info=failed_tasks_info_to_save)
                        break 
                    elif failure_count >= threshold:
                        logging.info(f"Ignoring known historical failures for '{cid}' ({stage}). No new failures detected.")
            except Exception as e:
                logging.error(f"Error during reputation check for '{cid}': {e}")
    
    def run(self) -> None:
        self.notifier.send_watcher_start_message()
        while True:
            try:
                # PASTIKAN BARIS INI TIDAK ADA TANDA '#' DI DEPANNYA
                # os.system("clear")
                
                now_utc = datetime.now(timezone.utc)
                self._print_status_header(now_utc)
                is_warmed_up = (now_utc - self.start_time).total_seconds() >= WARMUP_SECONDS
                for cid in self.config.get("containers", []):
                    if cid in self.container_states: self.container_states[cid]["warmed_up"] = is_warmed_up
                if self.config.get("reputation_check_enabled"): self._check_reputation()
                all_statuses = self._get_all_container_statuses()
                running_nodes = {cid: status for cid, status in all_statuses.items() if status.get("is_running") and "session_id" in status}
                if len(running_nodes) < 2:
                    logging.warning("Not enough nodes reporting status to determine a majority.")
                else:
                    id_state_pairs = [(v["session_id"], v["state"]) for v in running_nodes.values()]
                    majority_pair, count = Counter(id_state_pairs).most_common(1)[0]
                    logging.info(f"Network Majority (ID, State): {majority_pair} ({count}/{len(running_nodes)} nodes)")
                    self._check_for_majority_stagnation(now_utc, majority_pair)
                    print()
                    self._evaluate_all_nodes(all_statuses, majority_pair)
                time.sleep(self.config["check_interval_seconds"])
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.critical(f"An unhandled error in the main loop: {e}", exc_info=True)
                self.notifier.send_watcher_error_message(e)
                time.sleep(10)

    def _get_all_container_statuses(self) -> Dict[str, Dict[str, Any]]:
        # ... (Method content is unchanged)
        statuses = {}
        for cid in self.config["containers"]:
            try:
                container = self.client.containers.get(cid)
                status_data = {"container": container, "is_running": container.status == "running", "docker_status": container.status}
                if not status_data["is_running"]: statuses[cid] = status_data; continue
                log_lines = container.logs(tail=self.config.get("tail_lines", 500)).decode("utf-8", "ignore").splitlines()
                if self.container_states.get(cid, {}).get("warmed_up", False):
                    if any(PATTERN_TRACEBACK in ln for ln in log_lines):
                        self._restart_container(container, "Python Traceback", "A Python 'Traceback' was detected.")
                        continue
                    ping_failures = sum(1 for ln in log_lines[-52:] if PATTERN_PING_FAIL in ln)
                    if ping_failures >= 2:
                        self._restart_container(container, "Ping Failure", f"{ping_failures} instances of '{PATTERN_PING_FAIL}' found.")
                        continue
                for ln in reversed(log_lines):
                    m = RE_LOG_STATE.search(ln)
                    if m: status_data["session_id"], status_data["state"] = int(m.group(1)), int(m.group(2)); break
                statuses[cid] = status_data
            except docker.errors.NotFound:
                logging.error(f"Container '{cid}' not found.")
                statuses[cid] = {"is_running": False, "container": None}
            except Exception as e:
                logging.error(f"Error processing container '{cid}': {e}")
                statuses[cid] = {"is_running": False, "container": None}
        return statuses

    def _evaluate_all_nodes(self, all_statuses: Dict[str, Any], majority_pair: Tuple[int, int]) -> None:
        # ... (Method content is unchanged)
        grace_period, id_lag_threshold, now = timedelta(seconds=self.config.get("grace_period_seconds", 30)), timedelta(minutes=2), datetime.now(timezone.utc)
        majority_id, majority_state = majority_pair
        for cid, status in all_statuses.items():
            container, docker_status = status.get("container"), status.get("docker_status", "unknown")
            if not status.get("is_running") or container is None:
                logging.warning(f"Container '{cid}' is not running (Status: {docker_status}).")
                if majority_state == 6 and container:
                    self._restart_container(container, "Inactive Node", f"Node status was '{docker_status}' while majority concluded session.")
                continue
            if "session_id" not in status:
                logging.warning(f"Could not parse state for running container '{cid}'."); continue
            current_id, current_state = status["session_id"], status["state"]
            state_info = self.container_states[cid]
            if (current_id, current_state) == majority_pair:
                if state_info.get("state_deviation_start_time") or state_info.get("id_lag_start_time"):
                    logging.info(f"'{cid}' has re-synced with the majority at {majority_pair}.")
                state_info["state_deviation_start_time"], state_info["id_lag_start_time"] = None, None
                print(f"  - [{cid}]: OK. In sync with majority at state {(current_id, current_state)}."); continue
            if current_state != majority_state:
                if state_info.get("state_deviation_start_time") is None:
                    state_info["state_deviation_start_time"] = now
                    logging.warning(f"'{cid}' state ({current_state}) deviates from majority ({majority_state}). Starting grace period timer.")
                else:
                    elapsed = now - state_info["state_deviation_start_time"]
                    if elapsed >= grace_period:
                        if state_info["warmed_up"]:
                            details = f"Node state was {current_state} at ID {current_id}, but majority is at state {majority_state} (ID: {majority_id}). Lagged for {int(elapsed.total_seconds())}s."
                            self._restart_container(container, "State Deviation", details)
                        else: logging.warning(f"'{cid}' state deviation detected but not restarting (still in warm-up).")
                    else: logging.info(f"'{cid}' deviating for {int(elapsed.total_seconds())}s of {int(grace_period.total_seconds())}s grace period.")
                continue
            elif current_id < majority_id:
                if state_info.get("id_lag_start_time") is None:
                    state_info["id_lag_start_time"] = now
                    logging.warning(f"'{cid}' ID ({current_id}) lags behind majority ({majority_id}). Starting 2-minute timer.")
                else:
                    elapsed = now - state_info["id_lag_start_time"]
                    if elapsed >= id_lag_threshold:
                        if state_info["warmed_up"]:
                            details = f"Node was stuck at ID {current_id} while majority progressed to ID {majority_id}. Lagged for over 2 minutes."
                            self._restart_container(container, "Session ID Lag", details)
                        else: logging.warning(f"'{cid}' ID lag detected but not restarting (still in warm-up).")
                    else: logging.info(f"'{cid}' ID lagging for {int(elapsed.total_seconds())}s of {int(id_lag_threshold.total_seconds())}s.")
    
    def _print_status_header(self, now: datetime) -> None:
        # ... (Method content is unchanged)
        uptime, is_warmed_up = timedelta(seconds=int((now - self.start_time).total_seconds())), (now - self.start_time).total_seconds() >= WARMUP_SECONDS
        warmup_status = "ACTIVE" if is_warmed_up else f"WARMING UP ({int(uptime.total_seconds())}/{WARMUP_SECONDS}s)"
        header = f"\n--- Cortensor Watcher Status | {now.strftime('%Y-%m-%d %H:%M:%S UTC')} ---\nUptime: {uptime} | Monitoring Status: {warmup_status}"
        print(header)

    def _handle_telegram_command(self, message: Dict) -> None:
        # ... (Method content is unchanged)
        text, parts = message.get("text", "").strip(), message.get("text", "").strip().split()
        command = parts[0].lower()
        logging.info(f"Received command from Telegram: {text}")
        if command in ["/start", "/stop", "/restart", "/logs"]:
            if len(parts) < 2: self.notifier.send_command_response(f"Error: Missing container name.\nUsage: <code>{command} &lt;container_name&gt;</code>"); return
            cid = parts[1]
            try:
                container = self.client.containers.get(cid)
                if command == "/start": container.start(); self.notifier.send_command_response(f"Container <code>{cid}</code> started.")
                elif command == "/stop": container.stop(); self.notifier.send_command_response(f"Container <code>{cid}</code> stopped.")
                elif command == "/restart": container.restart(); self.notifier.send_command_response(f"Container <code>{cid}</code> restarted.")
                elif command == "/logs":
                    num_lines_str = parts[2] if len(parts) > 2 else "20"
                    if not num_lines_str.isdigit(): self.notifier.send_command_response("Error: Line count must be a number."); return
                    logs = container.logs(tail=int(num_lines_str)).decode("utf-8", "ignore")
                    if len(logs) > 4000: logs = "...\n" + logs[-4000:]
                    self.notifier.send_command_response(f"Last {int(num_lines_str)} lines of logs for <code>{cid}</code>:\n<pre>{logs}</pre>")
            except docker.errors.NotFound: self.notifier.send_command_response(f"Error: Container <code>{cid}</code> not found.")
            except Exception as e: self.notifier.send_command_response(MSG_CMD_ERROR.format(error=str(e)))
            return
        response = ""
        if command == "/stagnation":
            if len(parts) > 1:
                sub_cmd = parts[1].lower()
                if sub_cmd == "on": self.config["stagnation_alert_enabled"] = True; response = "Stagnation alerts have been ENABLED."
                elif sub_cmd == "off": self.config["stagnation_alert_enabled"] = False; response = "Stagnation alerts have been DISABLED."
                else: response = f"Unknown sub-command '<code>{sub_cmd}</code>'. Use 'on' or 'off'."
            else: response = "Missing sub-command. Use '<code>/stagnation on</code>' or '<code>/stagnation off</code>'."
        elif command == "/stagnation_timer":
            if len(parts) > 1:
                try:
                    minutes = int(parts[1])
                    if minutes > 0: self.config["stagnation_threshold_minutes"] = minutes; response = f"Stagnation timer set to {minutes} minutes."
                    else: response = "Please provide a positive number of minutes."
                except ValueError: response = "Invalid number. Please provide an integer for minutes."
            else: response = "Missing argument. Usage: <code>/stagnation_timer &lt;minutes&gt;</code>"
        elif command == "/status":
            stagnation_status, stagnation_time, num_containers = "ENABLED" if self.config.get("stagnation_alert_enabled") else "DISABLED", self.config.get("stagnation_threshold_minutes"), len(self.config.get("containers", []))
            response = (f"<b>Watcher Status</b>\n- Monitoring {num_containers} containers.\n- Stagnation Alerts: <b>{stagnation_status}</b>\n- Stagnation Threshold: <b>{stagnation_time} minutes</b>")
        elif command == "/help": self.notifier.send_help_response(); return
        else:
            self.notifier.send_unknown_command_response(); return
        self.notifier.send_command_response(response)
    
    def _check_for_majority_stagnation(self, now: datetime, majority_pair: Tuple[int, int]) -> None:
        # ... (Method content is unchanged)
        if not self.config.get("stagnation_alert_enabled", False): return
        if self.last_seen_majority_pair != majority_pair:
            logging.info(f"Majority has progressed to {majority_pair}. Resetting stagnation timer.")
            self.last_seen_majority_pair, self.majority_stagnation_start_time, self.alert_sent_for_stagnant_pair = majority_pair, None, None
            return
        if self.majority_stagnation_start_time is None:
            self.majority_stagnation_start_time = now
            logging.info(f"Stagnation timer started for majority state {majority_pair} at {now.isoformat()}")
        else:
            threshold_minutes = self.config.get("stagnation_threshold_minutes", 30)
            elapsed = now - self.majority_stagnation_start_time
            if elapsed >= timedelta(minutes=threshold_minutes) and self.alert_sent_for_stagnant_pair != majority_pair:
                logging.warning(f"Network stagnation detected! Majority state {majority_pair} stuck for over {threshold_minutes} minutes.")
                self.notifier.send_stagnation_alert(majority_pair, threshold_minutes)
                self.alert_sent_for_stagnant_pair = majority_pair
            else:
                if self.alert_sent_for_stagnant_pair != majority_pair:
                    logging.info(f"Majority state {majority_pair} has been stable for {int(elapsed.total_seconds() / 60)} minutes.")
