Cortensor Watcher

This tool monitors Cortensor node logs (systemd services like cortensor-1, cortensor-2, etc.) and automatically restarts them if specific error conditions are detected.

Features

Auto-discovers nodes by reading .env-* files in /home/deploy/.cortensor/.
Tails corresponding log files (/var/log/cortensord-<n>.log or fallback /var/log/cortensor-<n>.log).

Detects and restarts nodes for:
Python tracebacks (immediate and unrecovered).
Ping failures (configurable count within a window).
Node pool stale flags.
Wrong user state (address in Assigned Miners list while running in USER mode).

Displays:

Last complete session (highest State=6 seen).
Current Session ID / State per node (e.g., 1012/State=3).
Cognitive Level (CL:...).
Time since last restart.
Evidence logs for each restart saved in ./restart_logs/, and a summary log in watcher.log.
Configurable options via config.json.

Installation
Copy the script onto your node host (Python 3.10+ required).
Ensure it runs as the same user that can:
Read /home/deploy/.cortensor/.env-*.
Read /var/log/cortensord-*.log.
Restart systemd services (systemctl restart cortensor-<n>).

Usage
python3 watcher.py


The script will:

Discover all configured nodes.
Start following their logs in real time.
Print a status table to the terminal every cycle.

Stop with Ctrl+C.

Configuration

On first run it creates config.json. Key options:

check_interval_seconds: how often to scan logs.

tail_lines: number of log lines kept in memory.

traceback_recovery_seconds: grace window for unrecovered tracebacks.

pingfail_threshold / pingfail_window: controls for detecting repeated ping failures.

cooldown_minutes: minimum time between restarts of the same node.

restart_dry_run: set to true to test without restarting.

restart_flags: enable/disable restarts for specific reasons.

Example Output
=== 2025-08-19T23:45:00Z | nodes=2 | interval=5s | cooldown=5m | last_complete_session=1012 | dry_run=False ===
Flags: traceback=off, traceback_unrecovered=on, pingfail=on, node_pool_stale=on, wrong_user_state=on
[cortensor-1] addr=0xABC...123 | 1012/State=3 | CL:4 | last_restart=85s ago
[cortensor-2] addr=0xDEF...456 | USER/Mode=USER | CL:2 | last_restart=-

Logs

./restart_logs/ → evidence for each restart, including surrounding log lines.

watcher.log → master list of all restarts.
