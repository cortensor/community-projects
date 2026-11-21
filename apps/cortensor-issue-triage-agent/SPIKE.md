# Spike：OpenMinion 0.1.21 SDK + Pollinations 免费模型

- 日期：2026-11-17（CST 00:56–01:05 左右；日志时间为 UTC 11-16 16:56–17:01）
- 目的：为 Cortensor Hackathon #5 Issue 分流 agent 验证两件事——SDK 能不能按参考作品的路子用；免费模型 Pollinations 能不能撑起工具调用与结构化 JSON 输出。
- 约束遵守：只读外部服务，未注册、未登录、未花钱、未用任何 API key（Pollinations 免 key；传给 SDK 的 `api_key="pollinations-no-key-needed"` 是占位字符串，不是真实 key）。未建仓库、未写正式代码、未提 PR。未读 `~/workspace/free-benefits/secrets/`。
- 参考笔记：`../cortensor-reference-study-20261117.md`（huadeng408 Verifier）、`../cortensor-competitive-landscape-20261117.md`（只学模式，未抄代码）。
- 工作目录：`~/workspace/hackathon-tracker/cortensor-issue-triage-agent/`（本文件所在目录）
- 探针脚本（可复现）：`probe_api.py`（离线 API 构造）、`probe_pollinations.py`（Pollinations 三项直测）、`pollinations_probe_log.json`（原始返回日志）。`/tmp/probe_subagent*.py`、`/tmp/probe_e2e.py` 为一次性脚本，未保留（步骤见下文）。

## 1. 环境与安装

- Python 3.12.3、pip 24.0（安装时 pip 自升到未记录的新版；freeze 以实际为准）。
- venv：工作目录下 `.venv`（`python3 -m venv .venv`）。
- 安装命令：`.venv/bin/pip install "openminion==0.1.21" pydantic pytest httpx`，一次成功。
- 实际装上的版本（`pip freeze` 相关行）：
  - `openminion==0.1.21`、`pydantic==2.14.3`、`pydantic_core==2.50.4`
  - `pytest==9.2.0`、`httpx==0.28.1`、`httpcore==1.0.9`、`anyio==4.16.0`
  - 另带：`typing_extensions==4.16.0`、`SQLAlchemy==2.1.8`、`typer==0.29.1` 等（SDK 依赖，完整 freeze 未存档，需要时 `.venv/bin/pip freeze` 重打）。

## 2. SDK API 事实（全部以实际 import / 构造结果为准）

验证方式：`probe_api.py` 离线运行（只 import 与构造，不调模型），11/12 通过；`subagent()` 一项初版失败，后经 `from_config` 方式打通（见 2.2）。

### 2.1 顶层导出（懒加载，全部存在）

`import openminion` 后可用（`openminion/__init__.py` 的 `_LAZY_EXPORTS`）：

```python
from openminion import APIRuntime, Agent, AgentOutputValidationError, AgentRunResult
from openminion import Handoff, MemoryBundle, ProviderError, TurnTimeoutError
from openminion import subagent, tool
```

另有 `openminion.api` 直接导出同一批（见 `openminion/api/__init__.py` 的 `__all__`，外加 `TurnChunk`、`TurnResponse`、`TurnTelemetry`、`ToolCallSummary`、`TurnError`、`RuntimeTurnHandle`、`dispatch_request`）。

### 2.2 `create_isolated_runtime` —— 在 0.1.21 里不存在

- 复现：`getattr(openminion, "create_isolated_runtime")` 抛 `AttributeError`；全包 grep `create_isolated_runtime` 零定义。
- 结论：参考作品笔记里的 `create_isolated_runtime()` 是该仓库自己 `runtime_factory.py` 的封装，不是 SDK 公共 API。等价的 SDK 原生做法是 `APIRuntime.from_config_path()` / `APIRuntime.from_config()` 并传 `home_root` / `data_root` 实现隔离。实测可用的最小写法：

```python
from openminion import APIRuntime
from openminion.base.config import OpenMinionConfig
from openminion.base.config.core import AgentProfileConfig
from openminion.base.config.providers import OpenAIProviderConfig

cfg = OpenMinionConfig(
    agents={"triage": AgentProfileConfig(name="triage", provider="openai",
                                         default_channel="console")})
cfg.providers.openai = OpenAIProviderConfig(
    model="openai", api_key="pollinations-no-key-needed",
    base_url="https://text.pollinations.ai/openai/v1")
rt = APIRuntime.from_config(config=cfg, home_root=tmp/"home", data_root=tmp/"data")
# 实测：runtime 约 1.7 s 建成；rt.close() 正常关闭
```

- 三个连环坑（全部实际复现到）：
  1. `Agent()` 不传 `runtime` 时，首次 `run()` 会调 `APIRuntime.from_config_path(None)`，要求当前工作目录下存在 `.openminion/agents.json`，否则 `ConfigManagerError: config file not found: <cwd>/.openminion/agents.json`（`probe_api.py` 的 `subagent_construct` 初版即因此失败；`.openminion/` 空目录是这次失败留下的）。
  2. 直接 `OpenMinionConfig()` 默认构造的 `agents` 目录为空，`from_config` 抛 `ConfigValidationError: OpenMinionConfig.agents is empty; no default agent is available`——必须至少填一个 `AgentProfileConfig`。
  3. `AgentProfileConfig` 未设 `default_channel` 时，turn 的 channel 为空串，网关鉴权直接拒绝：`RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`。注意 mode 明明是 `warn` 也照样拒绝——空 channel 在 `modules/controlplane/channels/authenticity.py` 里是无条件 `allowed=False`。设 `default_channel="console"`（默认受信 channel）后通过。

### 2.3 `Agent` 与 `@tool`（已验证构造）

```python
from openminion import Agent, tool
from pydantic import BaseModel

class Verdict(BaseModel):
    label: str
    confidence: float

@tool(min_scope="READ_ONLY")
def lookup_issue(number: int) -> str:
    """Look up a GitHub issue by number."""
    return f"Issue #{number}: login fails on Safari"

@tool(dangerous=True, min_scope="WRITE_SAFE")
def publish_note(text: str) -> str:
    """Publish a note."""
    return f"published:{text}"

agent = Agent(instructions="Triage issues.", output_type=Verdict,
              model="openai", tools=[lookup_issue],
              forced_tools=["lookup_issue"], name="triage", runtime=rt)
res = agent.run("Issue #12 ...", timeout_seconds=280)   # 未在本次 spike 跑通，见 §4
res = agent.run_stream("...", on_delta=print)            # 同 _run_once，加 on_delta 回调
```

- 实测：`@tool(min_scope="READ_ONLY")` 装饰后 `tool_decl.name/min_scope/dangerous` 与传入一致，`tool_family_spec` 属性存在；`dangerous=True, min_scope="WRITE_SAFE"` 同理。
- `Agent(...)` 构造本身不启动 runtime、不调模型；`tools` 接受装饰过的函数或已注册工具名字符串；`forced_tools` 是工具名列表。
- `Agent.run()` / `run_stream()` 均接受 `session_id`、`thread_id`、`timeout_seconds`、`approval_callback`、`cancel_event`；返回 `AgentRunResult(output, text, raw, run_id, run_state, session_id, thread_id, metadata, stats)`。
- 注意：`Agent` 构造时传了 `handoffs` 会立即编译 `transfer_to_<name>` 工具名并做重名校验（`_validate_unique_resolved_names`）。

### 2.4 `subagent()` 与 `SubagentRunContext`（已验证构造）

```python
from openminion import subagent
child = subagent(parent, instructions="Classify.", name="classifier",
                 timeout_seconds=60)
# child.subagent_context: tool_allowlist, timeout_seconds=60,
#   parent_transcript_inherited=False
```

- 实测：父 agent 须先有 runtime（`subagent()` 内部调 `parent._ensure_runtime()`）；用 §2.2 的 `from_config` runtime 打通，`child.name == "classifier"`，`timeout_seconds=60`，`parent_transcript_inherited=False`。
- `SubagentRunContext` 可直接构造（`openminion.api.handoff.SubagentRunContext`），必填 6 个 id 字段（`context_id`、`parent_agent_id`、`child_agent_id`、`parent_run_id`、`child_run_id`、`trace_parent_id`）；可选 `tool_allowlist`、`timeout_seconds`、`memory_posture`（仅 `"none"` / `"read_only_bounded"`，后者须配 `memory_grant_id`）。
- 实测硬约束：`parent_transcript_inherited=True` 构造即抛 `ValueError: developer subagents require isolated context`；`typed_result_handback=False`、`implicit_memory_write=True` 同样构造即拒。

### 2.5 `Handoff`（已验证构造）

```python
from openminion import Agent, Handoff
specialist = Agent(instructions="Specialist.", name="specialist")
h = Handoff(target=specialist)   # resolved_name() == "transfer_to_specialist"
agent = Agent(instructions="...", handoffs=[h], runtime=rt)
```

- 实测：`resolved_name()` 默认 `transfer_to_<target.name>`；`resolved_description()` 默认取目标 instructions 首行；重名 handoff 在 `Agent` 构造时抛 `ValueError`。
- 注意：`Handoff` 编译出的委托工具在目标端同步调 `target.run(message)`；参考笔记称 Handoff 不转发超时与审批回调（上游 issue #774）——本次 spike 未复现（需真模型跑通才可验证），只作记录，不列为本 spike 的发现。

### 2.6 `MemoryBundle`（已验证全程往返，纯 JSON，不调模型）

```python
from openminion.modules.memory.portability import (
    MemoryBundle, export_bundle, save_bundle, load_bundle, import_bundle)
b = export_bundle([{"kind": "issue", "id": 1}], metadata={"agent": "triage"})
save_bundle(b, "b.json")
b2 = load_bundle("b.json")
info = import_bundle(b2, trust_mode="direct")  # {"trust_mode": "direct", "item_count": 1, ...}
import_bundle(b2, trust_mode="bogus")  # 抛 InvalidArgumentError
```

- 实测：`export → save → load → import` 全程可用；bundle 版本为 `memory_bundle.v1`；`trust_mode` 只接受 `"direct"` / `"candidate"`，其他抛 `InvalidArgumentError: trust_mode must be 'direct' or 'candidate'`。
- 注意：`import_bundle` 只返回摘要 dict，不直接写 runtime 内存；把它接进 runtime 内存是实现时要自己写的部分。

### 2.7 `PolicyGrantInput`（已验证构造）

```python
from openminion.modules.policy.models import PolicyGrantInput
from openminion.modules.policy.constants import POLICY_GRANT_EFFECT_ALLOW
g = PolicyGrantInput(effect=POLICY_GRANT_EFFECT_ALLOW,
                     tool="publish_note", max_uses=1)
```

- 实测字段：`effect`、`tool="*"`（默认全工具）、`method="*"`、`target_json={}`、`duration_type`（默认 `POLICY_DURATION_FOREVER`）、`session_id`、`invocation_hash`、`max_uses`（`None` 为不限）、`reason`、`approval_id`。`max_uses=1` 构造成功。

### 2.8 `approval_callback` 与 fail-closed（仅代码级证据，未端到端复现）

- 签名：`_ApprovalCallback = Callable[[str, dict[str, Any], str], bool | Awaitable[bool]]`，即 `(tool_name, args, approval_id) -> bool`，可同步可异步；`Agent.run(..., approval_callback=...)` 透传。
- 代码证据（`api/agent.py`）：`approval_callback=None` 时不包装回调、直接以 `None` 传给 `runtime.run_turn`；`modules/brain/adapters/tool/runtime.py` 里 `approval_callback is None` 时内联审批复放返回 `None`（不执行）；`modules/tool/sidecars.py` 里 `approval_callback is None` 时抛 `ToolRuntimeError(TOOL_ERROR_CONFIRM_REQUIRED)`。
- `RuntimeTurnHandle.resolve_approval(approval_id=..., decision=...)` 存在，docstring 写明 "Apply allow_once or deny"。
- 未复现：完整的 "dangerous 工具 + approval_callback=None → 暂停留 thread_id → allow_once 恢复" 全流程需要一次跑通真模型的 turn，本次因 §4 的 402 未能跑到那一步。参考笔记的说法与上述代码证据一致，但本 spike 不把它算作已验证。

### 2.9 `submit_turn` 流式输出与 `TurnTelemetry`（仅签名级验证）

```python
handle = rt.submit_turn(payload={"message": "...", "session_id": "..."})
chunks = handle.stream()          # Iterator[TurnChunk]
result = handle.result()          # TurnResponse
handle.resolve_approval(approval_id="...", decision="allow_once")
handle.cancel()
```

- 实测签名：`APIRuntime.submit_turn(*, payload: dict) -> RuntimeTurnHandle`；`RuntimeTurnHandle` 有 `.stream()`（`Iterator[TurnChunk]`）、`.result()`（`TurnResponse`）、`.cancel()`、`.resolve_approval()`、`.trace_id`。
- `TurnChunk` 字段：`trace_id`、`kind`、`data`、`ts`、`schema_version="openminion.turn-stream.v1"`、`sequence`、`event_id`。
- `TurnTelemetry` 字段：`tokens_in=0`、`tokens_out=0`、`duration_ms=0`、`retries=0`、`queue_wait_ms=0`（构造默认值）；`TurnResponse` 含 `final_text`、`metadata`、`stats`、`artifacts`、`tool_calls_summary`、`telemetry`、`errors`。
- 未复现：真实流式 chunk 与遥测数值（需跑通 turn）。参考笔记称 `TurnTelemetry.tokens_in/tokens_out` 为 0 而 `TurnResponse.stats` 有真实值（上游 issue #773，已有修复 PR #775 被接受）——本次未复现，不列为本 spike 的新发现。

### 2.10 错误类型（已验证 import 与两处实际触发）

| 类型 | 位置 | 本次验证 |
|---|---|---|
| `AgentOutputValidationError` | `openminion.api.agent`（`ValueError` 子类，带 `raw_text`、`validation_error`） | 已触发：`agent._coerce_output("this is not json at all")` 对 `output_type=Verdict` 抛此错，`validation_error` 非空 |
| `TurnTimeoutError` | `openminion.api.turns`（转自 `services.runtime.ingress.orchestrator`） | 仅 import 成功，未触发 |
| `ProviderError` | `openminion.modules.llm`（`RuntimeError` 子类） | 已触发两次以上：见 §4，Pollinations 402 被包成 `PROVIDER_ERROR: ... openai request failed with HTTP 402 ...` |

## 3. Pollinations 免费端点实测（`probe_pollinations.py`，原始日志 `pollinations_probe_log.json`）

- 端点：`https://text.pollinations.ai/openai`，无 key；`model` 字段填 `"openai"`（文档默认免费模型）。
- 先修了一个环境坑才跑通：本沙箱的 `NO_PROXY` 含 `[::1]`，httpx 解析时抛 `InvalidURL: Invalid port: ':1]'`，curl 不受影响。把 `NO_PROXY`/`no_proxy` 改为 `localhost,127.0.0.1` 后全部通过。注意：SDK 的 provider 层同样走 httpx，同一环境变量可能在真跑时咬到它（未单独验证，只记录现象与 workaround）。
- `GET /models`：200，0.41 s，返回模型列表仅 `["openai-fast"]`。

### 3.1 (a) 普通 JSON 输出 —— 通过（首次即成功）

- 请求：`POST /v1/chat/completions`，`model="openai"`，极小提示词（只要求原样返回 `{"label": "bug", "confidence": 0.9}`）。
- 结果：200，6.35 s；返回 `model="gpt-oss-20b"`（即 `"openai"` 别名实际跑的模型），`finish_reason="stop"`；`content` 恰为 `{"label": "bug", "confidence": 0.9}`；`usage={"prompt_tokens": 333, "completion_tokens": 88, "total_tokens": 421}`。
- 注意：提示词本身约 30 token，`prompt_tokens` 却 333——服务端计入了额外系统提示或按其他口径计数；做 token 预算时不要按裸提示词估算。

### 3.2 (b) 工具调用 —— 通过（首次即成功）

- 请求：同上 + 一个 `function` tool（`lookup_issue`，参数 `{"number": integer}`），问 "issue #12 titled 'login fails on Safari'，用 lookup_issue 工具"。
- 结果：200，9.44 s；返回 `model="gpt-oss-20b"`，`finish_reason="tool_calls"`，`content` 为空；`tool_calls=[{"id": "chatcmpl-tool-849415c8217f2470", "type": "function", "function": {"name": "lookup_issue", "arguments": "{\"number\": 12}"}}]`——工具名与参数完全正确；`usage={"prompt_tokens": 386, "completion_tokens": 33, "total_tokens": 419}`。

### 3.3 (c) `response_format={"type": "json_object"}` —— 通过（首次即成功）

- 请求：同上 + `"response_format": {"type": "json_object"}`。
- 结果：200，12.14 s；被接受，未报错；返回 `model="gpt-oss-20b"`，`finish_reason="stop"`；`content` 为 `{"label":"failure","confidence":0.92}`；`usage={"prompt_tokens": 324, "completion_tokens": 170, "total_tokens": 494}`。
- 注意：JSON 结构正确，但 `label` 取值 "failure" 不在提示词给定的候选语义内——小模型语义质量有波动，结构化输出能用，标签准确性要靠提示词收紧 + Pydantic 枚举校验兜底。

### 3.4 (4) 降级方案：纯提示词 JSON 文本 + 本地 `json.loads` + Pydantic —— 通过

- 验证：直接解析 (a) 的返回文本，`json.loads` + `Verdict.model_validate` 成功：`label='bug' confidence=0.9`；(c) 的文本同样通过校验（`label='failure' confidence=0.92`）；故意给错类型（`{"label": 1}`）时 Pydantic 抛 `ValidationError`（2 条错误），兜底有效。
- 结论：即使不用 `tool_calls`，(a) 的路子本身就是可用的降级方案。

## 4. 端到端 `Agent.run` 经 Pollinations —— 未跑通（3 次均被 402 限速拦下）

- 走法：§2.2 的 runtime（`base_url=https://text.pollinations.ai/openai/v1`，`model="openai"`）+ `Agent(output_type=Verdict, tools=[lookup_issue])` + `agent.run(..., timeout_seconds=280)`。
- 尝试 1：先撞 `invalid_channel`（§2.2 坑 3），修 `default_channel="console"` 后推进到模型调用，随即 `ProviderError: ... openai request failed with HTTP 402: Free limit reached: 1 reply every 45 seconds per IP. Retry after 19s, or get unlimited replies with a pollen key ...`。
- 尝试 2：等待 60 s 后重试，仍 402（`Retry after 26s`），总耗时约 89 s 后 SDK 重试耗尽抛错。
- 尝试 3：等待 50 s 后重试，仍 402（`Retry after 25s`），总耗时约 81 s。
- 对照实验：同一窗口等待 50 s 后单发一次直接 HTTP 调用，200，2.3 s，正常返回。说明免费额度本身可用，但 SDK 一次 `Agent.run` 背后是多次连续模型调用（主 decide + 内部三分类轮次等，见参考笔记 §4 第 2 条），在 "1 reply / 45 s / IP" 的免费限速下：第 1 次调用占掉额度后，后续调用立即 402；SDK 自带重试（`provider_retry_max_attempts=3`）的退避等不够 45 s 窗口，最终以 `ProviderError` 收场。
- 补充不确定性：本沙箱出口 IP 是共享的，无法排除同一 IP 上其他流量也在消耗该额度；但三次端到端失败的模式一致（均在 decide 阶段 402），而单发直接调用每次都成功，结构性原因（SDK 多调用 vs 45 s 窗口）是最直接的解释。

## 5. 推荐

- **模型与预设**：`base_url=https://text.pollinations.ai/openai/v1`，`model="openai"`（实测跑的是 `gpt-oss-20b`，`user_tier` 为匿名免费层）；`GET /models` 只列出 `openai-fast`，不要用列表里的名字去猜模型——以 `chat/completions` 返回的 `model` 字段为准。`api_key` 可填任意占位字符串，Pollinations 不校验。
- **推荐走哪条路**：**主路用 JSON 文本降级（§3.4），工具调用只作演示/可选**。理由：
  1. Pollinations 直测三项全过，但 SDK 内一次 turn 要发多次请求，45 s/IP 的免费限速下端到端 3/3 失败；降级路把模型调用减到每步 1 次，且不依赖 SDK 的 turn 循环，最容易在免费额度内跑通、也最容易控制重试间隔（≥45 s）。
  2. 工具调用本身在直测里是好的（(b) 一次成功），可以保留为"有额度时"的增强路径，但不要把它放在关键路径上；实现时把 tool_calls 与 JSON 文本解析做成双通道：先看 `tool_calls`，没有就解析文本 JSON，都过 Pydantic 校验。
  3. 如果后续拿到 Cortensor Portal 或 OpenRouter 免费模型（参考笔记建议的优先平替），再切回 SDK 原生 `Agent` + `forced_tools` 路线；切换成本只是换 `base_url`/`model` 与恢复 `Agent.run`，工具定义与 Pydantic 模型不用重写。
- **实现时必须注意的坑**（按遇到顺序）：
  1. 没有 `create_isolated_runtime`——用 `APIRuntime.from_config(config, home_root, data_root)` 自己做隔离；`Agent()` 不给 runtime 会去找 `<cwd>/.openminion/agents.json`，没有就起不来。
  2. `OpenMinionConfig()` 默认 `agents` 为空，必须填一个 `AgentProfileConfig`，且 `default_channel` 必须设为 `"console"`，否则 turn 在网关鉴权层以 `invalid_channel` 被拒（`warn` 模式也拒）。
  3. 沙箱 `NO_PROXY` 含 `[::1]` 会让 httpx 抛 `InvalidURL`，跑之前把 `NO_PROXY`/`no_proxy` 清理为 `localhost,127.0.0.1`。
  4. Pollinations 免费限速是 402 + "1 reply every 45 seconds per IP"，SDK 重试等不够这个窗口；任何经 SDK 的调用都要按"一次 turn = 多次模型调用"来预算时间与额度，demo 时单步之间至少隔 45 s。
  5. `prompt_tokens` 有约 300 的固定开销（小提示词也计 317–386），上下文与成本预算别按裸提示词算。
  6. `gpt-oss-20b` 的 JSON 结构稳、语义有波动（(c) 返回了不在候选里的 `"failure"`），标签类字段用 Pydantic `Literal` 枚举锁死 + 失败重试。
  7. SDK 内部会发 `submit_output` 三分类轮次并给回复加 `agent_id:` 前缀（参考笔记 §4 第 2 条），结构化解析前要先剥离——本次未跑通 turn，未独立验证，列为实现时待验证项。
  8. `approval_callback=None` 的 fail-closed 全流程与 `TurnTelemetry` token 计数、Handoff 超时转发，本次只到代码/签名级，未端到端复现——实现时第一次跑通 turn 后要补测这三项，不要直接当已验证用。

## 6. 本次实际复现到的 SDK 粗糙点（只写复现到的）

1. **`create_isolated_runtime` 不存在**：参考作品以此为名的用法在 0.1.21 里无此导出；复现：`getattr` 抛 `AttributeError`，全包 grep 零定义。影响：照着笔记抄会直接起不来；须改用 `APIRuntime.from_config`。
2. **默认配置无法启动 runtime**：`OpenMinionConfig()` 的 `agents` 为空导致 `ConfigValidationError`；复现步骤见 §2.2。影响：最小可跑配置需要手填 agent profile，文档里不易找到。
3. **空 channel 在 `warn` 模式下仍拒绝 turn**：`Agent._build_payload` 不设 channel，`AgentProfileConfig.default_channel` 默认空串，网关以 `invalid_channel` 拒掉；复现：第一次端到端运行。影响：不读源码很难定位到是 channel 问题（错误信息只说 invalid_channel，不提示去设 `default_channel`）。
4. **Pollinations 免费限速下 SDK turn 必然撞 402**：复现：三次端到端 `Agent.run` 均在 decide 阶段得 HTTP 402，而直接单发调用成功。影响：免费模型 + SDK 原生 turn 的组合在当前限速下跑不通；SDK 重试退避（3 次）等不够 45 s 窗口。
5. **沙箱 `NO_PROXY` 含 `[::1]` 导致 httpx `InvalidURL`**：复现：`probe_pollinations.py` 首跑全部 `InvalidURL: Invalid port: ':1]'`，清理 `NO_PROXY` 后全过。影响：任何走 httpx 的客户端（含 SDK provider 层）在本沙箱都可能先撞这个，与目标服务无关。

## 7. 未复现、不写进发现的内容

- 参考笔记的 #773（telemetry token 为 0）、#774（Handoff 不转发超时与审批回调）：本次未跑通 turn，无法验证，只在 §2.8/§2.9 标注了代码级证据。
- `approval_callback=None` 的暂停 + thread_id 恢复全流程：同上，未端到端复现。
- 内部三分类轮次与 `agent_id:` 前缀：未跑通 turn，未独立验证。
