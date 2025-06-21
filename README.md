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
- Must comply with the shared [MIT License](./LICENSE)

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
