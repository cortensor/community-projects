# Cortensor Community Projects

This repository serves as a central hub for **community-built tools, apps, and infrastructure** that extend and support the Cortensor decentralized AI network.

Whether you're building a Telegram bot, monitoring tool, custom dashboard, or deploying node infra — this is the place to collaborate, consolidate, and ship together.

---

## 📁 Repository Structure

Projects are organized into three main directories:

🔹 `tools/` — Utility scripts, monitoring bots, helpers  
🔹 `apps/` — Community-facing applications built on Cortensor APIs  
🔹 `infras/` — Deployment scripts, Docker templates, node automation

Each project should include:
- `README.md` — What the project does and how to use it
- `STATUS.md` — Project status, roadmap, and known issues
- `RELEASE.md` — Changelog and version history
- Entry in the root-level `PROJECTS.yml`
- Must comply with the shared [MIT License](./LICENSE.md)

## 🚀 Getting Started with Templates

We provide "Hello World" templates for each category to help you bootstrap your own projects quickly:

### Using the Templates

1. **Choose a template** that matches your project type:
   - `apps/hello-world-bot` - Template for application projects
   - `tools/hello-world-tool` - Template for utility tools
   - `infras/hello-world-infra` - Template for infrastructure projects

2. **Copy the template** to create your new project:

   ```bash
   # For a new app
   cp -r apps/hello-world-bot apps/your-project-name
   
   # For a new tool
   cp -r tools/hello-world-tool tools/your-tool-name
   
   # For new infrastructure
   cp -r infras/hello-world-infra infras/your-infra-name
   ```

3. **Update the project files**:
   - Edit `PROJECTS.yml` with your project details
   - Update `README.md` with your project description
   - Modify `STATUS.md` and `RELEASE.md` accordingly
   - Start building in the `src/` directory

4. **Test your project** locally before submitting

## 🔄 Development Workflow

### Contributing to the Repository

We follow this branching structure:
```
main <- dev-userid <- dev-userid-feature1
```

1. **Create your developer branch** first:
   ```bash
   git checkout -b dev-{userid}
   ```
   Example: `dev-ryuma`

2. **Create feature branches** from your developer branch:
   ```bash
   git checkout -b dev-{userid}-{featurename}
   ```
   Example: `dev-ryuma-wallet-monitor`

3. **Make your changes** and commit them with descriptive messages:
   ```bash
   git add .
   git commit -m "Add wallet monitoring functionality"
   ```

4. **Test thoroughly** to ensure your project works as expected

5. **Merge your feature branch** back to your developer branch:
   ```bash
   git checkout dev-{userid}
   git merge dev-{userid}-{featurename}
   ```

6. **Create a pull request** to the main repository:
   - Push your developer branch to your fork
   - Go to the main repository on GitHub
   - Click "New Pull Request"
   - Select your developer branch (not the feature branch)
   - Fill out the PR template with details about your contribution
   - Submit the PR for review

7. **Address review feedback** if requested by maintainers

---

## 👥 Project Ownership & Tracking

Ownership and collaboration info for all projects is tracked in `PROJECTS.yml`. This helps us coordinate efforts and identify maintainers for each contribution.

Example entry:

```yaml
- name: hello-world-app-bot
  category: apps
  owner: "@cortensor-ryuma"
  collaborators:
    - "@alexdev#0001"
  status: active
  created: 2025-06-10
  version: v0.2.0
  tags: [telegram, llm, bot]
