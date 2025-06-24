# Project Status: Cortensor Monitor Bot

**Current Status:** `Active`

This file outlines the development roadmap and known issues for the Cortensor Monitor Bot.

---

## 🗺️ Roadmap

The roadmap is broken down into versions focused on incremental improvements, starting from quality-of-life fixes to major features.

### ☑️ v1.0 (Initial Release)
- [x] Basic node management (`/register`, `/unregister`, `/list`).
- [x] On-demand health and stats reports (`/stats`, `/health`).
- [x] Live-updating reports (`/autoupdate`).
- [x] Proactive failed transaction alerts (`/auto`).
- [x] Historical data logging to SQLite database.

---

### ⏳ v1.1 (Quality of Life & Usability)

Focuses on improving the user experience and providing more control over existing functionality.

- **Difficulty:** `Easy`
- **Tasks:**
  - [ ] **Enhanced Help Command:** Create a `/help` command that explains every command in detail with examples.
  - [ ] **Edit Node Labels:** Add an `/editlabel <address> <new_label>` command to allow users to update existing node labels without removing and re-adding them.
  - [ ] **More Detailed List:** Enhance the `/list` command to show the current monitoring status for each node (e.g., whether `/autoupdate` or `/auto` is active).
  - [ ] **Informative Startup Message:** When the bot starts, print a brief summary to the console (e.g., 'Loaded X users and Y nodes from the database').

---

### ⏳ v1.2 (Core Feature Expansion)

Introduces significant new functionality that expands the bot's capabilities.

- **Difficulty:** `Medium`
- **Tasks:**
  - [ ] **User Timezone Settings:** Allow users to set their own timezone via a `/set_timezone <timezone>` command (e.g., `UTC+7`) so that reports and alerts are delivered in their local time.
  - [ ] **Customizable Alert Thresholds:** Enhance the `/auto` feature to let users set thresholds, such as `/auto <failure_count> <minute_period>` to only receive an alert if more than X transactions fail within Y minutes.
  - [ ] **Dual Network Support:** Refactor the API checker (`arbiscan_checker.py`) to support other networks (e.g., Ethereum Mainnet). Users could specify the network when registering an address.
  - [ ] **Automatic Database Backups:** Implement a scheduled task that automatically backs up the SQLite database file daily.

---

### ⏳ v2.0 (Architectural Overhaul & Advanced Features)

Major revisions to improve scalability, reliability, and introduce advanced features.

- **Difficulty:** `Hard`
- **Tasks:**
  - [ ] **Full Multi-User System:** Refactor the bot to move away from the single `ADMIN_USER_ID` model to a system where any Telegram user can interact with the bot and manage their own nodes separately.
  - [ ] **Read-Only Web Dashboard:** Create a simple web application (using Flask or FastAPI) that provides a visual dashboard of all monitored nodes, reading from the same database.
  - [ ] **Database Migration to PostgreSQL:** Migrate the database backend from SQLite to PostgreSQL to handle higher concurrency and data volume as the user base grows.
  - [ ] **Interactive Report Customization:** Allow users to build their own custom reports by choosing which metrics to include through a series of interactive commands.

---

## ❗ Known Issues

- **Long-Running Process Management:**
  - **Description:** This bot is designed as a long-running service. Running `python3 src/main.py` directly in a terminal will cause the bot to stop when the terminal session is closed.
  - **Recommendation:** For continuous operation, the script should be run as a background service using a process manager like `systemd` (on Linux) or `pm2`.
  - **Priority:** High (for production use)

- **Python Environment Conflicts:**
  - **Description:** The project relies on specific library versions. Installing these packages globally instead of in a virtual environment can lead to conflicts with other Python projects on your system.
  - **Recommendation:** Always use a dedicated Python virtual environment (`venv`) as instructed in the setup guide to isolate dependencies.
  - **Priority:** Low (if setup guide is followed)
