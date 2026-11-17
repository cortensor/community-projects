# Cortensor OpenMinion Verifier 工作区规范 (AGENTS.md)

> **定位**：面向 **Cortensor Hackathon #5** 的基于 `OpenMinion 0.1 Python SDK` 构建的多源可验证声明与市场证据共识审计 Agent（验收与提交准备阶段保持 `PRIVATE`，仅在最终提交 PR 前经用户明确确认后转为 `PUBLIC`）。

---

## 一、核心原则与安全边界

1. **简体中文沟通**：仓库工程说明、汇报与文档对话使用简体中文；公开参赛材料（`README.md`、`BUILDING_BLOCKS_TESTED.md`、`WHAT_WE_LEARNED.md`、`PR_SUBMISSION_DRAFT.md`）按官方评委习惯提供清晰英文或双语对照。
2. **凭据零入库与公开门禁**：
   - 严禁将任何真实 API Key、`.env`、`.openminion/`、`.openminion-state/`、`agents.json` 中的密钥明文或私有网关域名写入代码或提交入 Git；运行时统一通过 `api_key_env` 引用环境变量。
   - 严禁未获用户确认将仓库转为 `PUBLIC` 或提交外部 PR。
3. **真实 SDK 接缝与独立环境隔离**：
   - 使用项目内独立 `.venv` 隔离 `openminion==0.1.21`（避免与系统 Anaconda 发生 `alembic==1.18.4` 等依赖冲突）；
   - 测试必须在真实 `openminion` `APIRuntime`、`Agent`、`@tool`、`subagent`、`Handoff` 与 `MemoryBundle` 上运行，仅在本地 `127.0.0.1` 确定性 HTTP 模型桩边界隔离网络，严禁 Mock `openminion` 内部实现。

---

## 二、标准研发流水线

遵循 Matt Pocock 工程技能流水线：`/grill-with-docs` → `/to-spec` → `/to-tickets` → `/implement-spec`（严格 `/tdd` 红→绿循环）→ 双轴 `/code-review`（Standards + Spec）。

- **Python 测试基线**：`& ".\.venv\Scripts\python.exe" -m pytest -q`
- **唯一主测试接缝**：`ConsensusAuditor.audit_claim()`、`BuildingBlockProbeRunner.run_all()` 与 `cortensor_verifier.cli.main()`。

---

## Agent skills

### Issue tracker

GitHub Issues on `huadeng408/cortensor-openminion-verifier` (via `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/` at repo root). See `docs/agents/domain.md`.
