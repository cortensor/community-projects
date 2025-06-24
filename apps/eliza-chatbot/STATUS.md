## 🗺️ Roadmap

This roadmap outlines our future goals, organized by priority and complexity. It is subject to change.

### Version 1.1 (Core Improvements)
*Easy*
- [ ] **Add More Commands**: Implement essential user commands for better usability.
  - [ ] `/help`: To provide usage instructions.
  - [ ] `/status`: To check the bot's connection to the Cortensor API.
- [ ] **Enhanced Error Handling**: Provide more specific and helpful feedback to users when the API fails or returns unexpected data.
- [ ] **Code Refactoring**: Separate the API communication logic from the main bot logic (`main.py`) for better maintainability and future expansion.

### Version 1.2 (Stateful Application)
*Medium*
- [ ] **Implement User-Specific Sessions**: This is a high-priority feature to make the bot truly conversational.
  - **Goal**: Transition from a single, shared `SESSION_ID` to a system where each user has their own unique session.
  - **Outcome**: The bot will have "memory" for each user's conversation (`1 user = 1 session`), addressing the current limitation of it being stateless.

### Version 1.3 (DevOps & Deployment)
*Medium*
- [ ] **Support for Docker**: Create a `Dockerfile` and `docker-compose.yml` for easier, consistent, and isolated deployment.
- [ ] **Add Basic CI/CD**: Implement GitHub Actions to automate code linting and testing on every push to maintain code quality.

### Future (Major Features)
*Hard*
- [ ] **Web3 Integration**: Explore and implement Web3 capabilities to evolve the project.
  - **Goal**: Integrate wallet connections or smart contract interactions to create a hybrid or fully decentralized application with more user control.
  - **Status**: This is a long-term research and development goal that will require significant architectural changes.
