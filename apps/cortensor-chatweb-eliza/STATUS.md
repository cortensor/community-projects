# Project Status

This document outlines the current status, roadmap, and known issues for the **Cortensor ChatWeb ELIZA** application.

## 🟢 Current Status

* **Version:** `1.0.0`
* **Status:** `Active`
* **Description:** The project is stable and under active development. The core features are functional, with ongoing work to improve functionality and address known issues.

---

## 🗺️ Roadmap

Here is a high-level overview of our planned features and improvements, organized by upcoming versions.

### **v1.1.0 — Quality-of-Life Update**
* **Dynamic Session ID Handling**: Implement a robust mechanism to map the `tx_hash` from the session creation endpoint to the integer `session_id` required by the completions endpoint.
* **UI/UX Enhancements**: Refine the user interface for better readability, smoother animations, and a more polished user experience.
* **Improved Error Handling**: Provide more granular and user-friendly error messages for both API and network-related issues.

### **v1.2.0 — Feature Release**
* **Model Configuration**: Add options in the UI for users to select different models or adjust LLM parameters (e.g., temperature, max tokens).
* **Streaming Responses**: Implement support for streaming API responses to display text as it's being generated, improving perceived performance.
* **Code Refactoring**: Further clean up the codebase and improve component structure for better maintainability.

### **v2.0.0 — Major Evolution**
* **Full Web3 Integration**: Add support for connecting wallets to manage sessions and tasks directly on the blockchain, moving away from local storage.
* **Multi-User Support**: Explore options for user authentication and multi-user session management.
* **Advanced Analytics**: Integrate a dashboard to provide insights into usage, performance, and costs for authenticated users.

---

## 🐛 Known Issues

* **Session ID Mismatch**:
    * **Description**: The `/api/session/create` endpoint returns a string `tx_hash`, while the `/api/chat` (completions) endpoint currently requires a static integer `session_id`.
    * **Impact**: The application currently uses a static `session_id` from the environment variables as a temporary workaround. This prevents true dynamic session context between different chats.
    * **Priority**: `High`. This is the primary blocker for full session management functionality and is scheduled to be addressed in **v1.1.0**.
