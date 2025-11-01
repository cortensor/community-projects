# Release History

## v1.0.0 (Initial Release) - 2025-08-29

### Added

* **Initial Bot Implementation**: Core structure of the Telegram bot using the `python-telegram-bot` library.
* **Child Safety Features**:
    * Integrated a robust profanity and unsafe topic filter to ensure all conversations are child-friendly.
    * System for parents to add and remove custom filtered words.
* **Parent Mode**:
    * Password-protected mode (`/parent` command) for administrative access.
    * Functionality for parents to set and change the PIN (`/setpin` command).
* **Customizable Bot Personality**:
    * Implemented multiple "agent styles" (e.g., Friendly Buddy, Storyteller) that users can switch between using the `/style` command.
* **Conversational State Management**:
    * The bot now maintains conversational memory to provide more coherent and context-aware responses.
    * `/reset` command to clear the current chat memory and style.
* **Cortensor API Integration**: Established connection to the Cortensor network for all AI-powered conversational logic.
* **Configuration**: Secure and easy setup using a `.env` file for API keys, tokens, and other settings.
