# Verifiable Claim & Market Evidence Consensus Auditor on OpenMinion 0.1

- **Status**: accepted

## Problem Statement

在去中心化 AI 推理与预测市场证据审核场景中，单一模型单次输出容易产生幻觉、遗漏反例或在未授权的情况下对外发布结论；同时，Cortensor Hackathon #5 要求开发者基于 `OpenMinion 0.1 Python SDK` 构建一个真实可用、可一键复现的工作流，全面实测其核心模块并提交包含 `Building Blocks Tested`、`What We Learned` 与 1–5 分钟演示视频在内的完整开源作品。

## Solution

基于隔离安装的 `OpenMinion 0.1 Python SDK` 构建多源可验证声明与市场证据共识审计 Agent：围绕每份 `Claim Dossier` 调度相互独立的只读佐证与质疑 `Redundant Verifier Pass`（由多个 `subagent` 与 Pydantic 结构化输出驱动），跨轮次维护证据溯源与会话记忆，经由可观测聚合与 `Approval-Gated Publication`（`Handoff` 审批暂停/恢复）形成 `Consensus Verdict`；同时配套运行覆盖 `OpenMinion` 10 大核心模块的 `Building Block Probe` 实测诊断套件，并自动生成无真人出镜的高清带字幕实机演示 MP4 与完整的黑客松 PR 提交包。

## User Stories

1. As a Cortensor Hackathon judge, I want to run one documented CLI command against a clean virtual environment and observe a real `OpenMinion 0.1` multi-agent audit workflow end-to-end, so that I can verify reproducibility immediately.
2. As an auditor operator, I want each `Claim Dossier` inspected through `READ_ONLY` decorated tools (market fixture loader, public evidence search, source excerpt reader), so that evidence gathering cannot mutate workspace state.
3. As a reliability engineer, I want each verifier pass to validate structured JSON outputs into typed Pydantic models and propagate `ProviderError` or `AgentOutputValidationError` cleanly, so that malformed or failing model responses never masquerade as valid verdicts.
4. As a consensus designer, I want at least two independent `Redundant Verifier Pass` subagents (corroborator and skeptic) to examine the same `Claim Dossier` and synthesize a `Consensus Verdict` with agreement score and disagreement notes, so that single-pass bias is mitigated (aligned with Cortensor PoI/PoUW).
5. As an operator, I want multi-turn follow-up verification to share session continuity and `MemoryBundle` persistence while keeping separate claim audits isolated, so that verified citations carry over cleanly across turns without cross-contamination.
6. As a safety gatekeeper, I want publication of any `Consensus Verdict` routed through an `OpenMinion` `Handoff` policy gate (`Approval-Gated Publication`) supporting allow-once, deny, and paused `thread_id` resumption, so that no conclusion is emitted externally without explicit authorization.
7. As a Cortensor & OpenMinion maintainer, I want an executable `Building Block Probe` suite covering all 10 core SDK primitives (`Agent`, Pydantic structured output, `@tool`, policy confirmation pause/resume, sessions, memory, `subagent`, `Handoff`, `submit_turn` streaming + `TurnTelemetry`, and error/timeout contracts) to emit factual `BUILDING_BLOCKS_TESTED` and `WHAT_WE_LEARNED` reports, so that product feedback is backed by reproducible evidence and exact SDK telemetry.
8. As a builder without dedicated Cortensor Portal access yet, I want provider switching via configuration presets (OpenAI-compatible, Cortensor Portal, Cortensor Router) without changing application code, so that the project runs today on real models and remains drop-in ready for Cortensor endpoints.
9. As a contestant, I want an automated demo video renderer that turns real audit and probe transcripts into a crisp 60–300 second captioned MP4 video, so that submission satisfies the 1–5 minute demo requirement reproducibly.

## Implementation Decisions

- 严格遵守 `CONTEXT.md` 领域术语与 `ADR-0001`：使用仓库本地 `.venv` 隔离安装 `openminion==0.1.21`，项目状态隔离于 `.openminion-state`，严禁任何真实凭据落盘或写入 `agents.json`。
- 通过 `APIRuntime.from_config_path` 统一托管配置、会话、策略与生命周期；内置多套无明文密钥的 provider 预设（环境变量驱动），支持模型无关切换。
- 主审计流采用「双视角冗余子代理 (`Redundant Verifier Pass`) + 结构化聚合器 + 受控 `Handoff` 发布门禁 (`Approval-Gated Publication`)」，真实采集每次运行的 `AgentRunResult.stats` / `TurnTelemetry`（请求数与 Token 用量）。
- `Building Block Probe` 以真实 `openminion` 运行时对象逐项检验 10 个模块并捕获可复现的开发者体验（DX）边界现象（例如网关路径拼接、认证头兼容及 Windows 环境隔离细节），直接驱动生成 `docs/BUILDING_BLOCKS_TESTED.md` 与 `docs/WHAT_WE_LEARNED.md`。
- 演示视频生成模块读取真实审计与探针运行产物，使用图像帧渲染与编码生成 1080p 带中英双语步骤条与实时状态面板的 MP4 视频（输出路径默认被 `.gitignore` 忽略，脚本入库可随时复现）。

## Testing Decisions

- **唯一测试接缝（Seam）**：`ConsensusAuditor.audit_claim()`、`BuildingBlockProbeRunner.run_all()` 与 CLI 入口（`audit`、`probe`、`render-demo`），所有测试均启动真实 `openminion==0.1.21` `APIRuntime` 并连接本地 `127.0.0.1:0` 确定性 OpenAI 兼容 HTTP 桩服务（支持普通 JSON、tool calling 与 SSE 流式块）。
- 严禁在测试中 Mock `openminion` 的 `Agent`、`APIRuntime`、`subagent` 或 `Handoff` 内部实现。
- 按垂直切片顺序红→绿推进：单轮结构化审计与只读工具 → 双子代理冗余核验 + Session/Memory + `Handoff` 审批门禁（含 `pause`/`thread_id` 恢复） → 10 模块探针与报告导出 → 真实大模型校准实跑 + MP4 视频合成验证 + PR 草稿包生成。

## Out of Scope

- 构建复杂 Web 前端界面或长期无人值守生产级守护进程。
- 对未经授权的外部社交账号或仓库执行自动公开推送与提 PR 操作。
- 伪造或离线硬编码任何模型运行统计与 `What We Learned` 结论。

## Further Notes

垂直切片工单图：`C1`（无阻塞）→ `C2` 与 `C3`（并发，均被 `C1` 阻塞）→ `C4`（被 `C2` 与 `C3` 阻塞）。

## Remediation Addendum (v0.1.1 — Submission-Grade Telemetry & Live Terminal Demo)

### Problem & Solution

1. **Telemetry Interpolation Mismatch**: `build_empirical_dx_findings(probes)` previously queried mismatched metadata keys (`reply_len`, `block`, `tool_call_count`, `digest_seen`, `other_session_isolated`, `bundle_id`, `payload_keys`, `handoff_tool_calls`), injecting misleading fallback defaults (`calls=0`, `digest_seen=False`, `other_session_isolated=False`, `bundle_id=n/a`, `handoff_tool_calls=0`) into `fixtures/calibrated_sample_run.json`, `docs/WHAT_WE_LEARNED.md`, and Scene 7 of the demo video. Fix all key lookups to match exact probe metadata and prohibit fallback sentinel leakage into any `Empirical Telemetry Finding`.
2. **Cross-Audit Session Memory & Import Isolation**: `ConsensusAuditor` previously appended only a message count (`Prior openminion session messages recorded: N`) instead of concise prior verdict/message summaries, and `import_session_memory` retained stale `pass_session_ids` metadata on overwrite. Keep Pass-1 (`corroborator`) and Pass-2 (`skeptic`) blind within the same `audit_claim` turn, inject concise prior-turn summaries across turns/imported sessions, and clear stale `pass_session_ids` on import.
3. **Live Terminal Demo & Caption Wrapping**: Upgrade `demo_renderer.py` to wrap long bilingual captions inside card bounds (`x <= 1840`), add a multi-stage animated live CLI terminal pane (`Live Terminal Storyboard`) showing progressive command streaming and pass arbitration within scenes, regenerate `calibrated_sample_run.json`, Markdown reports, and the 1080p MP4 video, and add a standard `Apache-2.0` `LICENSE` file at the repository root.

### Approved Testing Seams

- `build_empirical_dx_findings` & `write_probe_markdown_reports`
- `ConsensusAuditor.audit_claim` & `ConsensusAuditor.import_session_memory`
- `render_demo_video` (frame layout bounds & intra-scene live terminal animation)

### Remediation Ticket Graph

`C5` (#8: Telemetry interpolation, session memory summary injection & `LICENSE`, Blocked by: None) → `C6` (#9: Live CLI terminal demo renderer, caption wrapping & submission artifacts regeneration, Blocked by: #8). Spec Issue: #7.

---

## v0.1.2 Submission Readiness & Audit Hardening Addendum (ADR-0002)

### Problem & Solution

1. **MIT Relicensing, Pinned SDK & Community Metadata (`C7`)**: Switch `LICENSE` and `pyproject.toml` from `Apache-2.0` to `MIT`, pin `openminion==0.1.21` strictly, and add upstream `cortensor/community-projects/apps/*` compatible `PROJECTS.yml`, `STATUS.md`, and `RELEASE.md`.
2. **Scoped Evidence Toolset & Metadata Hygiene (`C7`)**: Replace static module-global fixture lookups with `build_scoped_verifier_tools(fixture_path=..., dossier=..., allow_private_network=False)` returning 4 `@tool(min_scope="READ_ONLY", idempotent=True)` tools (`load_delphi_market_fixture`, `search_public_evidence`, `fetch_source_excerpt`, `fetch_public_url_excerpt`), forwarding CLI `--fixtures` and inline `dossier.metadata["evidence_sources"]` plus SSRF-guarded public URL excerpts, and populating `calibration_status`, `calibrated_model`, and `endpoint_host` in `AuditRunBundle.metadata`.
3. **Actionable SDK Report & Upstream Bonus Drafts (`C8`)**: Upgrade `render_what_we_learned_md()` and regenerate `docs/WHAT_WE_LEARNED.md` + `docs/BUILDING_BLOCKS_TESTED.md` with structured `What Worked Cleanly`, `What Broke & Rough Edges`, and `Actionable SDK Improvement Proposals` (Repro + Expected vs. Actual), plus `docs/UPSTREAM_OPENMINION_BONUS_DRAFTS.md` covering 3 verified `openminion==0.1.21` upstream bug drafts (`daemon.py:550`, `handoff.py:169`, `task_context.py:179`).
4. **English CJK-Safe 1080p Live-CLI Demo & Dual-Channel PR Guide (`C9`)**: Convert `demo_renderer.py` to 100% English ASCII/Latin-safe UI/captions (zero CJK `□□□` risk), remove the stale `"Repo kept PRIVATE..."` Scene 7 footer line, show accurate per-scene model badges (`grok-4.6` vs `grok-4.7`) and explicit `--model` flags, embed authentic CLI stdout snippets, clean stale `artifacts/live_calibration.json`, regenerate `artifacts/cortensor_hackathon5_demo.mp4`, and upgrade `docs/PR_SUBMISSION_DRAFT.md` with DoraHacks `#2418` + `cortensor/community-projects` (`dev-huadeng408`) templates and zero broken relative links.

### Approved Testing Seams

- `build_scoped_verifier_tools` & `ConsensusAuditor.audit_claim` / `cli.main`
- `render_what_we_learned_md` & `export_probe_docs`
- `render_demo_video` (English ASCII rendering, per-scene model badges, margin pixel bounds, zero secret leakage)

### Remediation Ticket Graph

`C7` (Blocked by: None) and `C8` (Blocked by: None) run in parallel → `C9` (Blocked by: `C7`, `C8`).
