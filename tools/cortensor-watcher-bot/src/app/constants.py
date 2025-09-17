import re
from pathlib import Path

# --- Filesystem Constants ---
LOG_DIR = Path("restart_logs")
WATCHER_LOG_FILE = Path("watcher.log")

# --- Timing Constants ---
WARMUP_SECONDS = 180

# --- Performance Thresholds ---
SLOW_PROCESSING_THRESHOLD_BPS = 0.5

# --- Regex Constants (Final Corrected Version) ---
RE_LOG_STATE = re.compile(r"Latest ID:\s*(\d+)\s*/\s*Latest State:\s*(\d+)")
RE_TASK_MODE = re.compile(r"^\s*\*\s+Task Mode:\s*(.*)", re.MULTILINE)
RE_EVENT_STATS = re.compile(r"Event Stats:\s*(\{.*\})")


# --- Notification Message Templates (HTML) ---
MSG_RESTART = """🚨 <b>Node Watcher Alert</b> 🚨

Restarting node: <code>{cid}</code>
<b>Reason</b>: {reason}
<b>Details</b>: {details}
<b>Timestamp</b>: {timestamp}

<b>Last 25 lines of logs:</b>
<pre>{logs}</pre>"""

MSG_RESTART_FAILED = "🔥 <b>CRITICAL</b> 🔥\nFailed to restart node <code>{cid}</code>.\nManual intervention may be required."
MSG_WATCHER_STARTED = "✅ <b>Cortensor Watcher Started</b>\nMonitoring service is now online. Send /help for commands."
MSG_WATCHER_STOPPED = "⏹️ <b>Cortensor Watcher Stopped</b>\nService has been shut down gracefully."
MSG_WATCHER_ERROR = "🔥 <b>WATCHER CRITICAL ERROR</b> 🔥\nThe monitoring script has crashed: {error}\nManual intervention required."

MSG_STAGNATION_ALERT = """⚠️ <b>Network Stagnation Alert</b> ⚠️

The network majority state <code>{pair}</code> has not changed for over {duration} minutes. This may indicate an issue with the Oracle or RPC."""

MSG_STALE_NODE_ALERT = """🧊 <b>Stale Node Alert</b> 🧊

Node <code>{cid}</code> is reported as stale by its internal check.

<b>Suggested Actions:</b>
- Check the node's connectivity.
- Consider restarting the process manually on the server if needed."""

# New: Deviation alert when a node diverges from the majority for longer than grace period
MSG_DEVIATION_ALERT = """⚠️ <b>Node State Deviation</b> ⚠️

Node <code>{cid}</code> has deviated from the majority state for {minutes} minutes.

<b>Details</b>:
- Node state: <code>{node_state}</code>
- Majority: <code>{majority_state}</code>

Please investigate logs and connectivity on the server. No automatic restart will be performed by the bot."""

MSG_CMD_RESPONSE = "✅ <b>Command Executed</b>\n\n{response}"
MSG_CMD_ERROR = "❌ <b>Action Failed</b>\n\n{error}"
MSG_CMD_UNKNOWN = "❓ <b>Unknown Command</b>\n\nI don't recognize that command. Send /help to see available commands."

# <<< UPDATED HELP MESSAGE >>>
MSG_HELP = """<b>🤖 Cortensor Watcher Bot Help</b>

This bot monitors your Cortensor nodes and sends warnings when issues are detected. It does not perform automatic restarts, and manual start/stop via bot is disabled.

---

<b>🧠 Core Logic</b>

1.  <b>Majority State Monitoring</b>: The bot periodically checks the <code>(ID, State)</code> of all nodes. It determines the "majority state" and identifies any nodes that deviate. If a node deviates beyond a grace period, the bot will send a warning notification.

2.  <b>Status Reporting</b>: The bot reads descriptive statuses from your node logs, such as the current Task Mode and the last logged Event from Event Stats. The <code>/status</code> command provides a full report.

3.  <b>Telemetry</b>: The bot can fetch recent on-chain history data if configured.

---

<b>⌨️ Command Reference</b>

<code>/start</code>
Shows a quick start message.

<code>/status</code>
Shows a detailed, real-time status report for all monitored nodes.

<code>/logs [node_name]</code>
Fetches recent logs. Shows a 25-line summary for all nodes if no name is provided.
- Usage: <code>/logs</code> or <code>/logs cortensor-1</code>

<code>/resources [node_name]</code>
Shows process and container resource usage for a node (CPU, memory). If no name is provided, shows all nodes.
- Usage: <code>/resources</code> or <code>/resources cortensor-1</code>

<code>/models [node_name]</code>
Shows Docker containers ("models") grouped per node using strict name prefixes from config.
- Usage: <code>/models</code> or <code>/models cortensor-1</code>

<code>/history [node_name]</code>
Shows the latest 25 transactions for the node's configured address via Etherscan/Arbiscan.

 
"""

MSG_HISTORY_HEADER = "<b>📜 Transaction History</b> (latest 25)"

# --- Resource Monitoring Messages ---
MSG_RESOURCE_USAGE = """📊 <b>Resource Info for <code>{node_name}</code>:</b>
  - <b>Log Size:</b> {log_size_mb:.2f} MB
  - <b>Last Write:</b> {last_write}"""
MSG_RESOURCE_USAGE_NOT_FOUND = "❌ Node <code>{node_name}</code> not found or log file missing."
MSG_RESOURCE_USAGE_FAILED = "⚠️ Could not retrieve resource info for <code>{node_name}</code>."
