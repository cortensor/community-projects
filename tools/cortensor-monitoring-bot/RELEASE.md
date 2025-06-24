# Release History: cormonitor

## `v1.0.0` - 2025-06-24

**Initial Release**

This is the first public release of the Cortensor Monitoring Bot.

### Features
- **Node Management:** Register, unregister, and list multiple node addresses.
- **On-Demand Reports:** Fetch detailed statistics and real-time health checks for your nodes using the `/stats` and `/health` commands.
- **Live Monitoring:** Use the `/autoupdate` command to start a live-updating report in your chat.
- **Automatic Alerts:** Enable the `/auto` feature to receive proactive notifications for any failed transactions on your monitored nodes.
- **Data Persistence:** User data is stored locally in a SQLite database.
- **Historical Trends:** Statistics reports include trend analysis by comparing current data against historical snapshots from 1, and 24 hours ago.
