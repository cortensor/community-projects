# Project Status

This document provides a high-level overview of the project's status, development roadmap, and known issues.

* **Current Status**: `Active`
* **Latest Version**: `v1.2.0`
* **Last Updated**: `2025-06-24`

The project is stable and has undergone significant reliability improvements. It is actively monitoring nodes and provides a rich feature set for remote management and health checking.

---

## 🗺️ Roadmap

This roadmap outlines potential future goals and features, organized by version and complexity.

### Version 1.3: Quality of Life & Foundational Improvements
*Easy to Medium*
- [ ] **Enhanced Health Checks**: Add a new command (`/resources <node_name>`) to get real-time CPU and Memory usage for a specific container.
- [ ] **Test Suite Implementation**: Begin developing a suite of unit and integration tests to ensure long-term reliability and prevent regressions.

### Version 1.4: Advanced Management & Reporting
*Medium*
- [ ] **Dynamic Node Management**: Implement commands (`/add_node`, `/remove_node`) to manage the list of monitored nodes at runtime without needing a bot restart.
- [ ] **Scheduled Summary Reports**: Automatically send a daily or weekly performance summary (e.g., uptime percentages, total restarts per node) to the configured Telegram chat.

### Future / v2.0: Major Capabilities
*Hard*
- [ ] **Data Visualization**: Integrate a plotting library (e.g., Matplotlib) to generate and send simple charts as images, such as reputation history or restart frequency, for easier analysis.

---

## ⚠️ Known Issues & Limitations

This is a list of known limitations.

* **Telegram-Only Notifications**
    * **Description**: The notification system is currently coupled directly with the `TelegramNotifier`. Expanding to other platforms would require refactoring.
    * **Status**: `Pending / Future Enhancement`

* **Docker-Dependent**
    * **Description**: The monitor is designed specifically to interact with the Docker API. It cannot monitor Cortensor nodes that are run as standalone processes without Docker.
    * **Status**: `By Design`
