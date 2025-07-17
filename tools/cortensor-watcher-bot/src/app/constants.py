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

Restarting container: <code>{cid}</code>
<b>Reason</b>: {reason}
<b>Details</b>: {details}
<b>Timestamp</b>: {timestamp}

<b>Last 25 lines of logs:</b>
<pre>{logs}</pre>"""

MSG_RESTART_FAILED = "🔥 <b>CRITICAL</b> 🔥\nFailed to restart container <code>{cid}</code>.\nManual intervention may be required."
MSG_WATCHER_STARTED = "✅ <b>Cortensor Watcher Started</b>\nMonitoring service is now online. Send /help for commands."
MSG_WATCHER_STOPPED = "⏹️ <b>Cortensor Watcher Stopped</b>\nService has been shut down gracefully."
MSG_WATCHER_ERROR = "🔥 <b>WATCHER CRITICAL ERROR</b> 🔥\nThe monitoring script has crashed: {error}\nManual intervention required."

MSG_STAGNATION_ALERT = """⚠️ <b>Network Stagnation Alert</b> ⚠️

The network majority state <code>{pair}</code> has not changed for over {duration} minutes. This may indicate an issue with the Oracle or RPC."""

MSG_STALE_NODE_ALERT = """🧊 <b>Stale Node Alert</b> 🧊

Node <code>{cid}</code> is reported as stale by its internal check ({pool_type}).

<b>Suggested Actions:</b>
- Check the node's connectivity.
- Consider a manual restart using <code>/restart {cid}</code>."""

MSG_CMD_RESPONSE = "✅ <b>Command Executed</b>\n\n{response}"
MSG_CMD_ERROR = "❌ <b>Action Failed</b>\n\n{error}"
MSG_CMD_UNKNOWN = "❓ <b>Unknown Command</b>\n\nI don't recognize that command. Send /help to see available commands."

# <<< UPDATED HELP MESSAGE >>>
MSG_HELP = """<b>🤖 Cortensor Watcher Bot Help</b>

This bot monitors your Cortensor nodes, performs automated actions, and allows for remote management.

---

<b>🧠 Core Logic</b>

1.  <b>Majority State Monitoring</b>: The bot periodically checks the <code>(ID, State)</code> of all nodes. It determines the "majority state" and identifies any nodes that deviate. If a node deviates for too long, the bot can be configured to take action (e.g., restart).

2.  <b>Status Reporting</b>: The bot reads descriptive statuses from your node logs, such as the current Task Mode (NETWORK/USER) and the last logged Event from Event Stats. The <code>/status</code> command provides a full report based on this real-time data.

3.  <b>Remote Management</b>: You can directly manage the lifecycle of your Docker containers and retrieve information on demand using the commands below.

---

<b>⌨️ Command Reference</b>

<code>/status</code>
Provides a detailed, real-time status report for all monitored nodes, sent as separate messages for clarity.

<code>/logs [node_name]</code>
Fetches recent logs. Shows a 25-line summary for all nodes if no name is provided.
- Usage: <code>/logs</code> or <code>/logs cortensor-1</code>

<code>/resources [node_name]</code>
Shows CPU and Memory usage. Shows a summary for all nodes if no name is provided.
- Usage: <code>/resources</code> or <code>/resources cortensor-1</code>

<code>/restart &lt;node_name&gt;</code>
Restarts a specific Docker container.

<code>/start &lt;node_name&gt;</code>
Starts a stopped Docker container.

<code>/stop &lt;node_name&gt;</code>
Stops a running Docker container."""

# --- Resource Monitoring Messages ---
MSG_RESOURCE_USAGE = """📊 <b>Resource Usage for <code>{container_name}</code>:</b>
  - <b>CPU:</b> {cpu_percent:.2f}%
  - <b>Memory:</b> {mem_usage:.2f} MB / {mem_limit:.2f} MB"""
MSG_RESOURCE_USAGE_NOT_FOUND = "❌ Container <code>{container_name}</code> not found."
MSG_RESOURCE_USAGE_FAILED = "⚠️ Could not retrieve resource usage for <code>{container_name}</code>."
