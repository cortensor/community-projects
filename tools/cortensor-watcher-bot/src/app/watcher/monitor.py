import logging
import os
import re
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, Optional

from app.bot.notifier import TelegramNotifier
from app.constants import (
    LOG_DIR,
    WATCHER_LOG_FILE,
    MSG_HELP,
    MSG_HISTORY_HEADER,
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

        # Nodes configuration: list of node names and mappings.
        # Supported in config.json:
        #   "nodes": ["cortensor-1", ...]
        #   "node_configs": { node: {"user": "deploy", "folder": ".cortensor", "env_file": ".env-1", "index": 1 } }
        #   "log_files": {"cortensor-1": "/var/log/cortensord-1.log", ...} (optional override)
        #   "commands": {"start"|"stop"|"restart": {node: "..."}} (optional override)
        self.nodes = self.config.get("nodes") or self.config.get("containers", [])
        self.log_files: Dict[str, str] = self.config.get("log_files", {})
        self.commands: Dict[str, Dict[str, str]] = self.config.get("commands", {})
        self.node_configs: Dict[str, Dict[str, Any]] = self.config.get("node_configs", {})
        # Optional display names and docker filters per node (for /status and /models)
        self.display_names: Dict[str, str] = self.config.get("display_names", {})
        self.docker_filters: Dict[str, str] = self.config.get("docker_filters", {})
        self.sudo_password: str = self.config.get("sudo_password")
        self.resource_sample_seconds: float = float(self.config.get("resource_sample_seconds", 1.0))

    # Etherscan/Arbiscan + external APIs
        self.etherscan_api_key: str = self.config.get("etherscan_api_key") or os.getenv("ETHERSCAN_API_KEY")
        self.tx_monitor_cfg: Dict[str, Any] = self.config.get("tx_monitor", {})
        # Use Etherscan v2 unified base by default; allow override via .env or tx_monitor
        self.etherscan_api_base: str = (
            self.config.get("etherscan_api_base")
            or self.tx_monitor_cfg.get("etherscan_api_base")
            or "https://api.etherscan.io/v2/api"
        )
        # Determine chain id: from env/config, else map from tx_monitor.network, else None
        chain_id_env = self.config.get("etherscan_chain_id")
        self.etherscan_chain_id: Optional[str] = str(chain_id_env) if chain_id_env else None
        if not self.etherscan_chain_id:
            net = (self.tx_monitor_cfg.get("network") or "").lower().strip()
            chain_map = {
                "arbitrum-sepolia": "421614",
                "arb-sepolia": "421614",
                "arbitrum": "42161",
                "arbitrum-one": "42161",
                "arbitrum-nova": "42170",
                "ethereum-sepolia": "11155111",
                "sepolia": "11155111",
                "ethereum": "1",
                "mainnet": "1",
            }
            self.etherscan_chain_id = chain_map.get(net)
        self.stats_api_url: str = self.config.get("stats_api_url")
    # reputation API removed

        self.container_states = self._load_state()
        self.majority_state = None
        self.last_cycle_statuses: Dict[str, Any] = {}

    def _load_state(self) -> Dict[str, Any]:
        """Memuat state dari file JSON untuk persistensi."""
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
        """Menyimpan state saat ini ke file JSON."""
        state_file = Path("state_data/watcher_state.json")
        state_file.parent.mkdir(exist_ok=True)
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(self.container_states, f, indent=4, default=str)

    def _read_log_tail(self, path: Path, lines: int) -> str:
        if not path.exists():
            return ""
        try:
            # Efficient tail using subprocess head/tail if available; fallback to readlines
            return subprocess.check_output(["tail", "-n", str(lines), str(path)], text=True).strip()
        except Exception:
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    return "".join(f.readlines()[-lines:])
            except Exception:
                return ""

    def _get_full_node_status(self, node_name: str) -> Dict[str, Any]:
        """Membaca semua status relevan dari log sebuah node (file-based)."""
        status = {
            "id_state": None,
            "last_event": "Unknown",
            "task_mode": "Unknown"
        }
        # Resolve log path from config or fallback to /var/log/cortensord-<index>.log
        meta = self._node_meta(node_name)
        log_path = Path(self.log_files.get(node_name, str(meta["log_path"])))
        try:
            logs = self._read_log_tail(log_path, 500)

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
            logging.error(f"Could not parse full status for {node_name}: {e}")
        return status
    
    def _node_meta(self, node_name: str) -> Dict[str, Any]:
        """Return resolved metadata for a node: user, folder, env_file, index, dir, env_path, log_path."""
        cfg = self.node_configs.get(node_name, {})
        user = cfg.get("user", "deploy")
        folder = cfg.get("folder", ".cortensor")
        env_file = cfg.get("env_file")
        # Try to infer index from env_file suffix if not provided
        index = cfg.get("index")
        if index is None and env_file:
            m = re.search(r"(\d+)$", env_file)
            if m:
                try:
                    index = int(m.group(1))
                except ValueError:
                    index = None
        if index is None:
            # fallback: try to parse from node_name like cortensor-3
            m = re.search(r"(\d+)$", node_name)
            index = int(m.group(1)) if m else 1
        # Default env_file if missing
        if not env_file:
            env_file = f".env-{index}"
        # Absolute paths
        node_dir = Path(f"/home/{user}/{folder}")
        env_path = node_dir / env_file
        log_path = Path(self.log_files.get(node_name, f"/var/log/cortensord-{index}.log"))
        return {
            "user": user,
            "folder": folder,
            "env_file": env_file,
            "index": index,
            "dir": node_dir,
            "env_path": env_path,
            "log_path": log_path,
        }

    # Removed process control helpers: start/stop/restart are not performed by the bot

    def run(self):
        """Loop pemantauan utama dengan logika status yang disempurnakan."""
        self.notifier.send_watcher_start_message()
        self.notifier.start_update_listener(self._handle_command)

        while True:
            logging.info("Starting new monitoring cycle...")
            containers_to_monitor = self.nodes
            grace_period = self.config.get("grace_period_seconds", 300)

            self.last_cycle_statuses = {}
            for cid in containers_to_monitor:
                try:
                    # Selalu dapatkan status berdasarkan file log
                    self.last_cycle_statuses[cid] = self._get_full_node_status(cid)
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
                                logging.error(f"Node '{cid}' has deviated for too long. Sending alert.")
                                # Send deviation alert instead of restarting
                                minutes = int((now - start_time).total_seconds() // 60)
                                try:
                                    self.notifier.send_deviation_alert(
                                        cid=self.display_names.get(cid, cid),
                                        node_state=str(id_state),
                                        majority_state=str(self.majority_state),
                                        minutes=minutes,
                                    )
                                finally:
                                    # keep deviation timer running until resolved to avoid spamming
                                    pass
                    else:
                        if self.container_states[cid].get('deviation_start_time'):
                            logging.info(f"Node '{cid}' returned to majority state.")
                            self.container_states[cid]['deviation_start_time'] = None

            self._save_state()
            interval = self.config.get("check_interval_seconds", 60)
            logging.info(f"Cycle finished. Waiting for {interval} seconds.")
            time.sleep(interval)

    def _handle_command(self, message: Dict):
        """Menangani perintah masuk dari Telegram."""
        text = message.get("text", "")
        parts = text.split()
        command = parts[0].lower()
        args = parts[1:]
        logging.info(f"Received command: {command} with args: {args}")

        try:
            if command == "/status":
                self._handle_status_command()
            elif command == "/start":
                self.notifier.send_command_response("Send /help for commands")
            elif command == "/help":
                self.notifier.send_help_response()
            elif command == "/models":
                self._handle_models_command(args)
            elif command == "/history":
                self._handle_history_command(args)
            
            # Manual start/stop/restart commands are disabled
            elif command == "/logs":
                self._handle_logs_command(args)
            elif command == "/resources":
                self._handle_resources_command(args)
            else:
                self.notifier.send_unknown_command_response()
        except Exception as e:
            logging.error(f"Error handling command '{command}': {e}", exc_info=True)
            self.notifier.send_command_response("An internal error occurred.")

    # Manual management is disabled; internal restarts may still occur

    # ---------------------- History command ----------------------
    def _address_for_node(self, node_name: str) -> str:
        # prefer tx_monitor.address_map, fallback to node_addresses
        addr_map = (self.tx_monitor_cfg.get("address_map") or {})
        if node_name in addr_map:
            return addr_map[node_name]
        return (self.config.get("node_addresses") or {}).get(node_name, "")

    def _etherscan_get_txs(self, address: str) -> tuple[list, str]:
        if not address:
            return [], "no address"
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 50,
            "sort": "desc",
            "apikey": self.etherscan_api_key or ""
        }
        # For v2 unified API, include chainid if available
        if self.etherscan_chain_id:
            params["chainid"] = self.etherscan_chain_id
        try:
            import requests
            r = requests.get(self.etherscan_api_base, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "1" and isinstance(data.get("result"), list):
                return data["result"], ""
            # status "0" can include messages like "No transactions found" or details in result
            msg = str(data.get("message") or "")
            res = data.get("result")
            res_txt = ""
            if isinstance(res, str):
                res_txt = res
            elif isinstance(res, list):
                res_txt = f"list[{len(res)}]"
            elif isinstance(res, dict):
                res_txt = "object"
            # Combine for clarity
            err = (f"status={data.get('status')}"
                   + (f", message={msg}" if msg else "")
                   + (f", result={res_txt}" if res_txt else ""))
            return [], err
        except Exception as e:
            logging.error(f"etherscan tx fetch failed for {address}: {e}")
        return [], str(e)

    def _handle_history_command(self, args: list):
        target = args[0] if args else None
        nodes = [target] if target else sorted(self.nodes)
        self.notifier.send_command_response(MSG_HISTORY_HEADER)
        for cid in nodes:
            addr = self._address_for_node(cid)
            disp = self.display_names.get(cid, cid)
            if not addr:
                self.notifier.send_command_response(f"<b>{disp}</b>\n(no address configured)")
                continue
            txs, err = self._etherscan_get_txs(addr)
            if not txs:
                if err:
                    self.notifier.send_command_response(f"<b>{disp}</b>\n(no transactions found; API: {err})")
                else:
                    self.notifier.send_command_response(f"<b>{disp}</b>\n(no transactions found)")
                continue

            # Build readable lines; show Age instead of value/hash
            base = self._explorer_base_for_chain()
            addr_lc = addr.lower()

            # Friendly names for specific method signatures
            SIG_NAME_MAP = {
                "0x65c815a5": "Commit",
                "0xf21a494b": "Precommit",
                "0xca6726d9": "Prepare",
            }

            def short(a: str) -> str:
                if not a or len(a) <= 12:
                    return a
                return a[:8] + "…" + a[-6:]

            def fmt_eth(wei_str: str) -> str:
                try:
                    w = int(wei_str or "0")
                except Exception:
                    w = 0
                eth = w / 1e18
                if eth == 0:
                    return "0"
                if eth < 0.001:
                    return f"{eth:.6f}".rstrip('0').rstrip('.')
                if eth < 1:
                    return f"{eth:.4f}".rstrip('0').rstrip('.')
                return f"{eth:.3f}".rstrip('0').rstrip('.')

            lines = []

            # Detect consecutive PINGs from the most recent entries
            def normalize_fn_name(t: dict) -> str:
                mid = (t.get("methodId") or "").lower()
                mapped = SIG_NAME_MAP.get(mid)
                if mapped:
                    return mapped
                fn = t.get("functionName") or t.get("methodId") or "tx"
                fn_simple = fn.split("(")[0] if "(" in fn else fn
                return fn_simple

            ping_streak = 0
            for t0 in txs:
                name0 = (normalize_fn_name(t0) or "").strip()
                if name0.upper() == "PING":
                    ping_streak += 1
                else:
                    break

            def fmt_age(ts_int: int) -> str:
                try:
                    now = int(datetime.now(timezone.utc).timestamp())
                    delta = max(0, now - int(ts_int))
                except Exception:
                    return "-"
                if delta < 60:
                    return f"{delta}s ago"
                mins = delta // 60
                if mins < 60:
                    return f"{mins} min ago" if mins == 1 else f"{mins} mins ago"
                hours = mins // 60
                if hours < 24:
                    return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"
                days = hours // 24
                return f"{days} day ago" if days == 1 else f"{days} days ago"

            for t in txs[:25]:
                # Timestamp
                try:
                    ts = datetime.fromtimestamp(int(t.get("timeStamp", "0")), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                except Exception:
                    ts = t.get("timeStamp", "-")
                try:
                    ts_int = int(t.get("timeStamp", "0"))
                except Exception:
                    ts_int = 0
                # Direction
                from_addr = (t.get("from") or "").lower()
                to_addr = (t.get("to") or "").lower()
                direction_out = (from_addr == addr_lc)
                arrow = "→" if direction_out else "←"
                peer = to_addr if direction_out else from_addr
                peer_disp = short(peer) if peer else "-"
                # Function / method
                mid = (t.get("methodId") or "").lower()
                mapped = SIG_NAME_MAP.get(mid)
                if mapped:
                    fn_simple = mapped
                else:
                    fn = t.get("functionName") or t.get("methodId") or "tx"
                    fn_simple = fn.split("(")[0] if "(" in fn else fn
                fn_safe = fn_simple.replace("<", "&lt;").replace(">", "&gt;")
                # Status icon
                ok = (t.get("isError") == "0")
                status_icon = "✅" if ok else "❌"
                # Age
                age = fmt_age(ts_int)
                dir_txt = (f"OUT {arrow} <code>{peer_disp}</code>" if direction_out
                           else f"IN  {arrow} <code>{peer_disp}</code>")
                lines.append(f"{ts} | {status_icon} {dir_txt} | {fn_safe} | {age}")

            block = "\n".join(lines)
            warning = None
            if ping_streak > 10:
                warning = f"⚠️ Detected {ping_streak} consecutive PINGs with no other transactions (most recent)."
            # include address next to name
            message = f"<b>{disp}</b> (<code>{addr}</code>)\n"
            if warning:
                message += warning + "\n"
            message += f"<pre>{block}</pre>"
            self.notifier.send_command_response(message)
            time.sleep(0.1)

    def _explorer_base_for_chain(self) -> str:
        cid = getattr(self, "etherscan_chain_id", None)
        mapping = {
            "1": "https://etherscan.io/tx/",
            "11155111": "https://sepolia.etherscan.io/tx/",
            "42161": "https://arbiscan.io/tx/",
            "42170": "https://nova.arbiscan.io/tx/",
            "421614": "https://sepolia.arbiscan.io/tx/",
        }
        return mapping.get(str(cid), "https://etherscan.io/tx/")

    def _get_node_logs(self, node_name: str, lines: int) -> str:
        """Fetch latest logs from file for a node."""
        log_path = Path(self.log_files.get(node_name, str(self._node_meta(node_name)["log_path"])))
        if not log_path or not log_path.exists():
            return f"❌ Log file for <code>{node_name}</code> not found."
        logs = self._read_log_tail(log_path, lines).replace("<", "&lt;").replace(">", "&gt;")
        return f"<b>Logs for <code>{node_name}</code> ({lines} lines):</b>\n<pre>{logs}</pre>"

    # Reputation command removed
            
    def _handle_status_command(self):
        """Menangani logika perintah /status."""
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
            
            node_display = self.display_names.get(cid, cid)
            node_report = (
                f"--- <b>{node_display}</b> ---\n"
                f"  - Mode: <code>{status.get('task_mode')}</code>\n"
                f"  - Last Event: <code>{status.get('last_event')}</code>\n"
                f"  - ID/State: <code>{id_state or 'N/A'}</code>\n"
                f"  - Sync: {sync_status}"
            )
            self.notifier.send_command_response(node_report)
            time.sleep(0.1)

    def _handle_logs_command(self, args: list):
        """Menangani logika perintah /logs."""
        if not args:
            for cid in sorted(self.nodes):
                response = self._get_node_logs(cid, 25)
                self.notifier.send_command_response(response)
                time.sleep(0.1)
        else:
            lines = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
            response = self._get_node_logs(args[0], lines)
            self.notifier.send_command_response(response)

    def _docker_ps_all(self) -> list:
        """Return a list of docker containers as tuples: (name, image, status)."""
        try:
            cmd = "docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}'"
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            entries = []
            for l in lines:
                parts = l.split('|', 2)
                if len(parts) == 3:
                    name, image, status = parts[0].strip(), parts[1].strip(), parts[2].strip()
                    entries.append((name, image, status))
            return entries
        except subprocess.CalledProcessError as e:
            logging.error(f"docker ps failed: {e}")
            return []

    def _handle_models_command(self, args: list):
        """Show docker containers per node based on simple name filters from config.json."""
        entries = self._docker_ps_all()
        targets = [args[0]] if args else sorted(self.nodes)
        for cid in targets:
            disp = self.display_names.get(cid, cid)
            # Strict prefix filter by display name: match exact name or names starting with 'DISPLAY-'
            prefix = f"{disp}-"
            filtered = [(n, img, st) for (n, img, st) in entries if n == disp or n.startswith(prefix)]
            # Optionally apply additional regex filter from config if provided
            flt = self.docker_filters.get(cid)
            if flt:
                try:
                    regex = re.compile(flt, flags=re.IGNORECASE)
                    filtered = [t for t in filtered if regex.search(" | ".join(t))]
                except re.error as e:
                    logging.warning(f"Invalid docker_filters regex for {cid}: {e}")
            if not filtered:
                msg = f"<b>{disp}</b>\n(no matching containers)"
            else:
                lines = [f"{n} | {img} | {st}" for (n, img, st) in filtered]
                safe = "\n".join(lines).replace("<", "&lt;").replace(">", "&gt;")
                msg = f"<b>{disp}</b>\n<pre>{safe}</pre>"
            self.notifier.send_command_response(msg)
            time.sleep(0.1)

    def _handle_resources_command(self, args: list):
        """Menangani logika perintah /resources."""
        if not args:
            for cid in sorted(self.nodes):
                response = self._get_resource_usage(cid)
                self.notifier.send_command_response(response)
                time.sleep(0.1)
        else:
            response = self._get_resource_usage(args[0])
            self.notifier.send_command_response(response)

    # ---------------------- Resource helpers ----------------------
    def _parse_mem_to_mib(self, s: str) -> float:
        """Parse a human-readable memory string like '96.3MiB', '15.5GiB', '1024kB' to MiB."""
        try:
            s = s.strip()
            if not s:
                return 0.0
            num = ''.join(ch for ch in s if (ch.isdigit() or ch == '.' ))
            unit = s[len(num):].strip().lower()
            val = float(num) if num else 0.0
            # Normalize
            if unit in ('mib', 'mb'):
                return val
            if unit in ('gib', 'gb'):
                return val * 1024.0
            if unit in ('kib', 'kb'):
                return val / 1024.0
            if unit in ('b', ''):
                return val / (1024.0 * 1024.0)
            # Fallback
            return val
        except Exception:
            return 0.0

    def _docker_stats(self, names: list) -> list:
        """Get docker stats for given container names. Returns list of tuples (name, cpu, mem_used_mib, mem_limit_mib, mem_percent)."""
        if not names:
            return []
        try:
            fmt = "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}"
            cmd = ["bash", "-lc", f"docker stats --no-stream --format '{fmt}' {' '.join(name for name in names)}"]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
            result = []
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) != 4:
                    continue
                name = parts[0].strip()
                cpu = parts[1].strip().rstrip('%')
                mem_usage = parts[2].strip()  # like '96.3MiB / 15.5GiB'
                mem_perc = parts[3].strip().rstrip('%')
                try:
                    cpu_val = float(cpu) if cpu else 0.0
                except ValueError:
                    cpu_val = 0.0
                used_str, _, limit_str = mem_usage.partition('/')
                used_mib = self._parse_mem_to_mib(used_str)
                limit_mib = self._parse_mem_to_mib(limit_str)
                try:
                    mem_perc_val = float(mem_perc) if mem_perc else 0.0
                except ValueError:
                    mem_perc_val = 0.0
                result.append((name, cpu_val, used_mib, limit_mib, mem_perc_val))
            return result
        except subprocess.CalledProcessError as e:
            logging.error(f"docker stats failed: {e}")
            return []

    def _cpu_usage_pid(self, pid: int, sample_sec: float = 0.5) -> float:
        """Approximate CPU usage percent for PID over a short sample using /proc."""
        try:
            clk_tck = os.sysconf(os.sysconf_names.get('SC_CLK_TCK', 'SC_CLK_TCK'))
        except Exception:
            clk_tck = 100

        def read_proc_times() -> tuple[int, int]:
            # process utime + stime (fields 14 and 15; 1-indexed in procfs docs)
            with open(f"/proc/{pid}/stat", "r") as f:
                parts = f.read().split()
                utime = int(parts[13])
                stime = int(parts[14])
                ptotal = utime + stime
            # total CPU jiffies
            with open("/proc/stat", "r") as f:
                first = f.readline()
                fields = [int(x) for x in first.strip().split()[1:]]
                # sum all modes for total jiffies
                ctotal = sum(fields)
            return ptotal, ctotal

        try:
            p1, c1 = read_proc_times()
            time.sleep(sample_sec)
            p2, c2 = read_proc_times()
            dp = max(0, p2 - p1)
            dc = max(1, c2 - c1)
            # fraction of total CPU jiffies across all CPUs; dc is already aggregated across CPUs
            frac = dp / dc
            cpu_percent = frac * 100.0
            return round(cpu_percent, 1)
        except Exception as e:
            logging.debug(f"/proc sampling failed for pid {pid}: {e}")
            return 0.0

    def _cortensord_ps_metrics(self, pid: int) -> Dict[str, float]:
        """Get CPU% (sampled) and RSS MiB for a specific PID."""
        try:
            cpu = self._cpu_usage_pid(pid, sample_sec=self.resource_sample_seconds)
            # RSS from /proc/<pid>/status (VmRSS in kB)
            rss_kb = 0.0
            try:
                with open(f"/proc/{pid}/status", "r") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                rss_kb = float(parts[1])
                            break
            except Exception:
                # Fallback to ps if status not accessible
                out = subprocess.check_output(["ps", "-p", str(pid), "-o", "rss="], text=True)
                rss_kb = float(out.strip() or 0)
            rss_mib = rss_kb / 1024.0
            return {"cpu": cpu, "rss_mib": rss_mib}
        except Exception as e:
            logging.debug(f"metrics failed for pid {pid}: {e}")
            return {"cpu": 0.0, "rss_mib": 0.0}

    def _get_resource_usage(self, node_name: str) -> str:
        """Accurate resource info for a node: cortensord process + related docker containers."""
        try:
            # Resolve display and PID
            disp = self.display_names.get(node_name, node_name)
            meta = self._node_meta(node_name)
            pid_file = f"/var/run/cortensord-{meta['index']}.pid"

            # cortensord metrics
            proc_line = "cortensord: not running"
            if Path(pid_file).exists():
                try:
                    pid = int(Path(pid_file).read_text().strip())
                    m = self._cortensord_ps_metrics(pid)
                    proc_line = f"cortensord: CPU {m['cpu']:.1f}%, Mem {m['rss_mib']:.1f} MiB"
                except Exception:
                    proc_line = "cortensord: PID file present but unreadable"

            # docker containers for this node (strict prefix by display name)
            entries = self._docker_ps_all()
            prefix = f"{disp}-"
            cont_names = [n for (n, _, _) in entries if n == disp or n.startswith(prefix)]
            stats = self._docker_stats(cont_names)
            total_cpu = sum(x[1] for x in stats)
            total_used = sum(x[2] for x in stats)
            total_limit = sum(x[3] for x in stats if x[3] > 0)
            percent_line = f"{(total_used/total_limit*100):.1f}%" if total_limit > 0 else "N/A"

            header = (
                f"📊 <b>Resource Info for <code>{disp}</code>:</b>\n"
                f"  - {proc_line}\n"
                f"  - Containers: {len(stats)} | CPU {total_cpu:.1f}% | Mem {total_used:.1f} MiB"
            )
            if total_limit > 0:
                header += f" / {total_limit:.1f} MiB ({percent_line})"

            # Show top containers by memory (up to 10)
            details = []
            for (name, cpu, used, limit, memp) in sorted(stats, key=lambda t: t[2], reverse=True)[:10]:
                lim_txt = f" / {limit:.1f} MiB" if limit > 0 else ""
                details.append(f"    • {name}: CPU {cpu:.1f}%, Mem {used:.1f} MiB{lim_txt} ({memp:.1f}%)")

            if details:
                body = header + "\n<pre>" + "\n".join(details) + "</pre>"
            else:
                body = header
            return body
        except Exception as e:
            logging.error(f"Failed to get resource info for {node_name}: {e}")
            return f"⚠️ Could not retrieve resource info for <code>{node_name}</code>."
