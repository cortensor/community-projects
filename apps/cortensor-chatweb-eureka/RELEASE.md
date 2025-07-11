# Release Notes: Version 1.1.0

**Release Date:** July 10, 2025

This version marks a significant milestone for the **Cortensor AI Chat** application. The architecture has been completely overhauled to ensure stability, reliability, and a superior user experience. The primary focus of this release was to resolve critical issues related to response handling and session management.

## ✨ New Features & Improvements

* **Robust Response Aggregation**: The backend logic has been rewritten from the ground up. It now correctly processes the raw data stream from the Cortensor network, aggregates responses from all available miners, and intelligently selects the most complete and accurate answer to be presented to the user.
* **Local-First Chat History**: The application now fully embraces a client-side architecture for chat histories.
    * **Static Session ID**: Utilizes a single, persistent session ID from the environment variables, eliminating the slow and unreliable on-chain session creation process during initialization.
    * **Client-Side "New Chat"**: The "New Chat" button is now a purely local operation, creating a new, independent conversation history in the browser's storage without any server calls.
* **Frontend Context Isolation**: Implemented a crucial logic change where the application only sends the message history of the *currently active chat* to the AI. This completely prevents context mixing between different local conversations, even though they share the same server session ID.
* **Toggleable Memory Mode**: Users now have direct control over the AI's conversational memory via a UI switch, allowing for both deep, context-aware dialogues and quick, single-turn queries.
* **Enhanced Error Handling**: Improved user-facing error messages to be more specific, distinguishing between network timeouts and a lack of response from miners.

## 🐛 Bug Fixes

* **Resolved "No Valid Responses" Error**: Fixed the critical bug where the backend would fail to parse the mixed data stream from miners. The new aggregation logic ensures a valid response is always selected if one is available.
* **Fixed UI Initialization Lock**: By removing the dynamic, on-chain session creation at startup, the application no longer gets stuck on the "Initializing..." screen.
* **Resolved Disappearing Chat Bug**: Corrected the frontend state management logic to prevent the user's last message from disappearing while waiting for an AI response.
* **Fixed Inconsistent AI Memory**: Removed the conflicting dual-prompt system in the backend. The AI's memory is now exclusively controlled by the "Memory Mode" switch on the frontend, ensuring its behavior is always predictable.
