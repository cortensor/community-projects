# 🟢 Current Status

- **Version**: 1.0.0  
- **Status**: Active  
- **Description**:  
  The bot is currently stable and actively being developed. Core functionality—including daily motivation delivery, mood tone selection, and timezone support—is operational. The project is focused on expanding usability, improving stability, and preparing for more personalized and scalable features.

---

# 🗺️ Roadmap

This roadmap outlines our future goals, organized by priority and complexity. It is subject to change as development progresses.

---

## ✅ Version 1.0 (MVP - Completed)
- [x] Send motivational messages automatically every day at 08:00 (user timezone)
- [x] Support `/start`, `/settimezone`, and mood selection
- [x] Save recent users and broadcast to active ones daily
- [x] Cortensor API integration with customizable tone
- [x] Store and load user preferences

---

## 🔧 Version 1.1 — Core Improvements
*Easy*
- [ ] **Add More Commands**
  - [ ] `/help`: Provide detailed usage instructions
  - [ ] `/status`: Display bot health and Cortensor API connectivity
- [ ] **Enhanced Error Handling**: Show meaningful messages when the API fails or behaves unexpectedly
- [ ] **Code Refactoring**: Split logic into modules (e.g., `api.py`, `scheduler.py`, `commands.py`) for clarity and extensibility

---

## 🧠 Version 1.2 — Stateful Application
*Medium*
- [ ] **Implement User-Specific Sessions**
  - **Goal**: Move from shared `SESSION_ID` to per-user session system
  - **Benefit**: Enables continuity in conversations and more contextual motivational messages

---

## ⚙️ Version 1.3 — DevOps & Deployment
*Medium*
- [ ] **Add Docker Support**
  - [ ] Create `Dockerfile` and `docker-compose.yml` for easier deployment
- [ ] **CI/CD Automation**
  - [ ] Setup GitHub Actions for auto-linting and basic tests on push

---

## 🚀 Future (v2.0.0+) — Major Enhancements
*Hard*
- [ ] **Web3 Integration**
  - **Goal**: Add wallet support or smart contract interactions
  - **Use Case**: Users “own” their sessions or customize experience via decentralized features
  - **Status**: Under research, will require full architectural review

---

# 🐛 Known Issues

### 1. Shared Session Context
- **Description**: Currently using a static `SESSION_ID` for all users
- **Impact**: No memory between user conversations, leading to stateless interactions
- **Planned Fix**: Move to per-user sessions in v1.2

---

# 🧩 Contributing

We're open to contributions! Check the [README.md](./README.md) for setup instructions and feel free to submit issues or pull requests.

