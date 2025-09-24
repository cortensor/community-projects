# Release History

## [v1.2.0] - 2025-06-23

This is a major stability release that addresses numerous critical bugs discovered during long-term operation within a Docker environment. The focus of this update is to significantly improve the bot's reliability, error handling, and the robustness of its state persistence mechanism.

All users are strongly encouraged to update to this version for a much more stable monitoring experience.

---

### 🐛 Critical Bug Fixes & Improvements

* **State Persistence Overhaul (`TypeError` Fix):**
    The state saving and loading mechanism (`_save_state`, `_load_state`) has been completely rewritten. This resolves a fatal `TypeError` related to `datetime` object serialization, ensuring that all timers are now correctly saved and loaded from `state.json` across bot restarts.

* **Startup Crash Prevention (`AttributeError`, `NameError`):**
    Fixed multiple bugs that could cause the bot to crash on startup by ensuring all state-tracking variables are correctly initialized and all required modules are imported at the right time.

* **Filesystem Robustness (`FileNotFoundError` Fix):**
    The bot now automatically creates the required `state_data` directory on startup, preventing crashes and simplifying the initial setup process.

### ✨ Core Features (Now More Stable)

All existing features, including **Remote Management** and **Majority/Stagnation Monitoring**, remain fully functional and are now significantly more reliable.


## [v1.1.1] - 2025-06-20

 

---

### 🐛 Key Improvement

* **Restart Loop Prevention:** The bot now "remembers" the specific failed tasks that triggered a restart by saving its state to a `state.json` file. It will not restart the same node again for those same historical failures, effectively eliminating restart loops.

### ✨ Core Features (Unchanged)

* All remote management commands (`/start`, `/stop`, `/restart`, `/logs`) and watcher settings (`/status`, `/stagnation`) remain fully functional.

---

## [v1.1.0] - 2025-06-17

This is the first major feature release for the Cortensor Watcher Bot, transforming it from a simple script into an active remote management and performance analysis tool.

---

### ✨ New Features

* **Remote Management via Telegram**
    * Added `/start`, `/stop`, and `/restart` commands to control container lifecycle directly from Telegram.
    * Added `/logs` command to fetch the most recent logs for any monitored node.

 

* **Enhanced Bot Commands**
    * Stagnation alerts can now be configured on the fly with `/stagnation on|off` and `/stagnation_timer`.
    * A new `/status` command provides a summary of the bot's current settings.

### 🐛 Bug Fixes & Improvements

 
* **Resolved Startup Crashes:** Fixed a series of fatal errors (`AttributeError`, `NameError`, `IndentationError`, `ImportError`).
* **Hardened Startup Process:** Added validation for the Telegram Bot Token and node address formats.
* **Refined Restart Logic:** The core monitoring logic now correctly differentiates between `State Deviation` and `Session ID Lag`.
