# Release History

## v1.0.0 (Initial Release) - 2025-08-28

### Added

* **Initial Bot Setup**: Implementation of the Telegram bot using `python-telegram-bot`.
* **Content Generation Modes**:
    * Generate new tweets and multi-part threads.
    * Generate replies by fetching context from an X (formerly Twitter) post link.
* **Interactive Controls**:
    * Inline keyboard for users to select generation modes (New Thread, New Tweet, Reply).
    * Controls to adjust the tone and length of the generated content.
    * Buttons to regenerate content, edit individual lines, and request hashtag suggestions.
* **Cortensor API Integration**: Connects to the Cortensor API for AI-powered text generation.
* **User Settings**:
    * `/settings` command to allow users to configure their default tone, length, and hashtags.
    * User preferences are stored locally in a SQLite database.
* **Configuration**: Environment variable management for API keys and bot tokens.
