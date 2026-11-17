# Isolated Virtualenv and Real Runtime Loopback Seam

- **Status**: accepted

我们决定为本仓库创建独立 `.venv` 以隔离安装 `openminion==0.1.21` 及其锁定依赖（例如 `alembic==1.18.4`），并规定全部主测试接缝必须启动真实的 `openminion` `APIRuntime`、`Agent`、`subagent` 与 `Handoff` 状态机，仅在本地 `127.0.0.1` 确定性 HTTP 模型兼容桩处隔离外部网络。

## Considered Options

- **直接安装进系统全局 Anaconda 环境**：会强行覆盖或降级系统既有包版本，污染其他本地研究项目。
- **在测试中 Mock `openminion` 内部 `Agent` 或 `APIRuntime` 类**：会导致测试与 SDK 真实行为脱节，既无法验证 `0.1.21` 真实兼容契约，也无法为黑客松 `Building Blocks Tested` 与 `What We Learned` 产出可信证据。

## Consequences

- 仓库内部维护与外部环境完全解耦，测试与演示视频均由真实 `openminion==0.1.21` 运行时驱动产出。
- 工作树并行子代理运行测试时需显式使用主仓 `.venv\Scripts\python.exe` 并设置各自工作树 `PYTHONPATH`，确保测到当前修改代码。
