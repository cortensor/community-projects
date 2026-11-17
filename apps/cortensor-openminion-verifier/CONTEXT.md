# Cortensor OpenMinion Verifier

基于 `OpenMinion 0.1` Python SDK 构建的多源可验证声明审计、冗余推理共识裁决与 SDK 模块实测上下文。

## Language

**Claim Dossier**:
待审计的原始事实声明与配套公开上下文档案，包含目标命题、来源快照与预期裁决域。
_Avoid_: 普通聊天提示, 交易订单

**Redundant Verifier Pass**:
由相互独立提示或视角（如佐证者与质疑者）对同一 `Claim Dossier` 分别执行的只读取证与结构化推理轮次。
_Avoid_: 单次问答, 并发重试

**Consensus Verdict**:
汇总多轮 `Redundant Verifier Pass` 结论、证据一致性与分歧点后形成的结构化最终判定（支持、反驳或存疑）。
_Avoid_: 自由文本回复, 随机投票

**Approval-Gated Publication**:
在将 `Consensus Verdict` 对外归档或移交下游发布前，必须经过策略确认暂停或操作者回调授权的安全发布边界。
_Avoid_: 自动发送, 静默写入

**Building Block Probe**:
针对 `OpenMinion` 核心原语逐项执行的确定性行为验证与开发者体验诊断用例，用于生成参赛实测反馈报告。
_Avoid_: 单元测试集, 冒烟脚本

**Empirical Telemetry Finding**:
基于 `Building Block Probe` 真实运行元数据逐字段插值生成的实测观察与改进建议条目，严禁混入未命中的占位默认值。
_Avoid_: 静态文案模板, 占位默认值

**Live Terminal Storyboard**:
演示视频中将 CLI 命令执行、逐项探针耗时与多轮共识裁决流式日志同屏动态呈现的可视化分镜。
_Avoid_: 静态幻灯片, 纯文字截图

**Scoped Evidence Toolset**:
与当前审计上下文显式绑定的只读取证工具集合，覆盖指定本地档案目录、内联声明线索以及受私网拦截保护的公开网页正文摘录。
_Avoid_: 全局硬编码样表, 无界联网爬虫

**Actionable SDK Finding**:
基于探针实测整理的结构化 SDK 评估结论，明确区分已验证可用能力、实测受阻边界以及包含复现路径与预期行为对照的源码级改进建议。
_Avoid_: 纯遥测堆砌, 无复现反馈
