# 📦 Release History

## v1.0.0 – Initial Public Release (2025-06-23)

This is the first official release of the **Daily Motivation Bot** project, built using the Cortensor API and Telegram Bot integration.

### ✨ Features

- **Daily Motivational Messages**  
  Users receive AI-generated motivational quotes daily at 08:00 AM (UTC+7) based on their selected timezone and emotional state.

- **Interactive Onboarding**  
  Users can set their timezone and emotional tone using `/start` and `/settimezone` commands.

- **Cortensor API Integration**  
  The bot uses the Cortensor AI network to generate personalized motivational quotes in real-time.

- **Secure Configuration**  
  Credentials and configuration (e.g., `TELEGRAM_BOT_TOKEN`, `CORTENSOR_API_KEY`, `SESSION_ID`) are stored in a local `.env` file for security and flexibility.

- **Lightweight and Extendable**  
  Built in Python 3.9+ using:
  - `python-telegram-bot`
  - `requests`
  - `dotenv`
  - `apscheduler` for daily scheduling

---

## 📌 Coming Soon

See our [Roadmap](./STATUS.md) for upcoming features, improvements, and version plans.
