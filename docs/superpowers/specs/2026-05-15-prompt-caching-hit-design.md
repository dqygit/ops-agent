# Prompt Caching Hit Design

## 目标

在当前项目中实现真正可命中的厂商侧 prompt caching，请求发到模型厂商 API 后，厂商后台能够看到缓存创建/读取命中。第一优先级支持 [`AnthropicLLMProvider`](src/app/core/llm/providers/anthropic.py:11)，同时为 [`OpenAICompatibleLLMProvider`](src/app/core/llm/providers/openai_compatible.py:13) 预留能力驱动的兼容扩展位。

本轮目标聚焦于“请求正确发出并可命中缓存”，不要求前端展示缓存命中率。

## 范围

### 本轮包含

- 为 [`LLMMessage`](src/app/core/llm/types.py:9) 和 [`LLMCompletionRequest`](src/app/core/llm/types.py:19) 增加厂商中立的缓存语义。
- 新增统一请求构建层，收敛 [`AgentLoop`](src/app/core/loop/agent_loop.py) 中分散的 prompt 拼装逻辑。
- 在 [`AnthropicLLMProvider`](src/app/core/llm/providers/anthropic.py:11) 中实现显式 prompt cache breakpoint 与 `cache_control` 注入。
- 在 [`OpenAICompatibleLLMProvider`](src/app/core/llm/providers/openai_compatible.py:13) 中增加 capability 驱动的缓存参数注入入口。
- 优先提升 system prompt、稳定历史消息、稳定工具定义的复用率。

### 本轮不包含

- 前端显示缓存命中率。
- 统一 usage 看板。
- 所有厂商的 usage 归一化展示。
- 为所有 OpenAI-compatible 厂商默认启用缓存字段。

## 设计原则

1. **Anthropic 优先落地**：先保证 Anthropic 的显式 prompt caching 可以真正命中。
2. **Provider-neutral 语义**：loop 层和消息结构不直接暴露厂商私有字段。
3. **稳定前缀最大化**：尽量让 system、已完成轮次历史、历史摘要、稳定工具定义进入可缓存前缀。
4. **动态后缀隔离**：当前轮用户输入、运行时上下文、本轮工具结果保持为非缓存后缀。
5. **降级安全**：缓存能力不可用时，必须自动退化为普通请求，不能影响正常对话和工具调用。

## 架构设计

实现分三层边界：

### 1. 中立语义层

在 [`src/app/core/llm/types.py`](src/app/core/llm/types.py) 扩展缓存相关类型和字段，只表达“哪些内容可缓存”和“缓存策略是否启用”，不携带 Anthropic 的 `cache_control` 等私有协议字段。

### 2. 请求构建层

新增 [`src/app/core/loop/request_builder.py`](src/app/core/loop/request_builder.py)，作为统一 request builder，将 [`AgentLoop`](src/app/core/loop/agent_loop.py) 当前分散构造请求的逻辑收敛成稳定前缀和动态后缀。

这个 builder 负责：

- 标注 system / history / summary / current_user / runtime_context / assistant_response / tool_result。
- 根据默认规则推导哪些消息可缓存。
- 统一生成带 `cache_policy` 的 [`LLMCompletionRequest`](src/app/core/llm/types.py:19)。

### 3. Provider 序列化层

- [`AnthropicLLMProvider`](src/app/core/llm/providers/anthropic.py:11) 将中立语义翻译为 Anthropic block content 与 `cache_control`。
- [`OpenAICompatibleLLMProvider`](src/app/core/llm/providers/openai_compatible.py:13) 根据 provider capability 决定是否注入兼容厂商的缓存参数。

## 数据结构设计

### 扩展 [`LLMMessage`](src/app/core/llm/types.py:9)

增加缓存语义字段：

- `cache_segment`：描述消息所在区段。
- `cache_status`：描述消息是否允许进入缓存前缀。

建议的语义枚举：

- `cache_segment`
  - `system`
  - `history`
  - `summary`
  - `current_user`
  - `runtime_context`
  - `assistant_response`
  - `tool_result`
- `cache_status`
  - `cacheable`
  - `volatile`
  - `inherit`

默认规则：

- `system` → `cacheable`
- `history` → `cacheable`
- `summary` → `cacheable`
- `current_user` → `volatile`
- `runtime_context` → `volatile`
- `assistant_response` → `volatile`
- `tool_result` → `volatile`

这里“尽量把所有对话历史都纳入缓存”的具体落地方式是：

- 所有已完成轮次的历史消息，在下一轮请求中都默认视为 `history`，因此属于可缓存前缀。
- 当前轮刚输入的用户消息以及本轮新增动态内容不进入缓存前缀。

### 扩展 [`LLMCompletionRequest`](src/app/core/llm/types.py:19)

增加 `cache_policy`，至少包含：

- `enabled: bool`
- `ttl: Literal["ephemeral", "one_hour"]`
- `breakpoint: Literal["last_cacheable_message"]`

第一版 breakpoint 固定为最后一个可缓存消息，不开放更复杂的 message index API，避免 prompt 布局变化导致调用点失效。

## 缓存断点规则

统一规则如下：

1. 如果 `cache_policy` 未开启，则不发送任何 provider cache hint。
2. 将 `inherit` 展开为默认缓存规则。
3. 从请求消息尾部向前，寻找最后一个 `cache_status="cacheable"` 的消息。
4. 将该消息作为缓存前缀的结尾，也就是 provider breakpoint。
5. 断点之后的消息全部视为动态后缀，正常发送但不参与缓存。

这样可以最大化复用长历史，同时保持当前轮动态上下文的稳定边界。

## 请求构建与数据流

建议新增 [`AgentLLMRequestBuilder`](src/app/core/loop/request_builder.py) 并由 [`AgentLoop`](src/app/core/loop/agent_loop.py) 调用。

主要数据流：

1. `LoopState`、会话历史、system prompt、工具定义进入 builder。
2. builder 负责生成带缓存语义的 [`LLMMessage`](src/app/core/llm/types.py:9) 列表。
3. builder 输出带 `cache_policy` 的 [`LLMCompletionRequest`](src/app/core/llm/types.py:19)。
4. provider 根据自身能力决定是否把语义翻译成厂商缓存参数。
5. 请求发往模型厂商，厂商后台统计缓存创建/读取。

builder 需要至少覆盖这些场景：

- 普通 agent turn 请求
- plan 生成请求
- plan step 执行请求
- plan summary 请求

## Provider 行为设计

### Anthropic

在 [`AnthropicLLMProvider`](src/app/core/llm/providers/anthropic.py:11) 中实现显式缓存：

1. 当 `cache_policy.enabled=True` 时，先计算最后一个 `cacheable` message。
2. 如果断点落在 system prompt：
   - 将 [`_serialize_system_prompt()`](src/app/core/llm/providers/anthropic.py:130) 从纯字符串升级为 block list。
   - 在最后一个可缓存 system block 上写入 `cache_control`。
3. 如果断点落在普通 message：
   - 将该 message 的 `content` 从字符串升级为 text block。
   - 在对应 block 上写入 `cache_control`。
4. 不命中断点的普通消息继续保持当前最小改动路径，避免扩大兼容面。
5. 工具定义按稳定顺序输出，使稳定工具定义尽量自然纳入可复用前缀。

Anthropic 成功接入后，连续发送相同前缀、尾部少量变化的请求时，厂商后台应能看到 prompt cache 的创建和读取命中。

### OpenAI-compatible

在 [`OpenAICompatibleLLMProvider`](src/app/core/llm/providers/openai_compatible.py:13) 中增加 capability 驱动的扩展入口，而不是统一硬编码：

1. 为 provider / model 增加缓存能力判断入口。
2. 只有明确配置支持缓存协议的兼容厂商时，才注入对应缓存参数。
3. 不支持缓存协议的厂商保持当前普通 chat completion 请求。

这样可以兼容不同 OpenAI-compatible 厂商差异，避免把错误字段发给不支持的服务端。

## 配置策略

本轮最小交付不强制增加前端开关。

配置优先级建议如下：

1. 代码层提供默认缓存策略能力。
2. 如需 provider-specific 能力开关，后续可扩展至 [`src/app/shared/schemas.py`](src/app/shared/schemas.py) 对应的模型配置结构。
3. UI 设置项可以后续补齐，不作为本轮上线前置条件。

## 错误处理与降级策略

- provider 不支持缓存协议时，自动降级为普通请求。
- cache breakpoint 计算失败时，自动不注入缓存字段。
- Anthropic block content 构造失败时，回退到当前字符串序列化路径。
- 任何缓存能力错误都不能破坏现有 tool calling、JSON mode、普通 completion 与 streaming。

## 风险与边界

### 主要风险

1. **前缀不稳定**
   如果 system prompt 或历史前缀中混入时间戳、run id、实时资产状态等动态内容，会显著降低命中率。

2. **Anthropic block 序列化兼容性**
   当前 [`_serialize_system_prompt()`](src/app/core/llm/providers/anthropic.py:130) 主要返回字符串。升级 block 序列化时必须确保现有工具调用结构不回归。

3. **OpenAI-compatible 差异化严重**
   不同兼容厂商的缓存字段可能完全不同，因此不能默认统一发送。

4. **过度缓存动态消息**
   如果把当前轮用户输入、实时工具结果也硬纳入前缀，反而可能让前缀更不稳定，真实命中率下降。

### 范围边界

本轮不要求：

- 前端展示缓存命中指标
- 抽象出统一的缓存 usage 数据面板
- 所有厂商统一实现 usage 归一化

## 验证方案

### Anthropic 验证

1. 构造 system prompt 与长历史前缀基本不变的多次请求。
2. 只修改尾部少量用户输入或当前轮动态上下文。
3. 在 Anthropic 厂商后台或 usage 统计中确认出现 cache create / cache read 指标。

### OpenAI-compatible 验证

1. 只对已明确支持缓存协议的目标厂商开启 capability。
2. 重复发送相同前缀请求，确认厂商后台存在相应缓存统计。
3. 对不支持缓存协议的兼容厂商，确认仍可正常完成对话请求。

### 本地验证

- 跑与 provider 相关的最小测试子集，确认 completion / streaming / tool calling 未回归。
- 必要时补充针对 breakpoint 计算和 Anthropic 序列化的单元测试到现有测试文件中，而不是新增独立测试文件。

## 推荐实施顺序

1. 扩展 [`src/app/core/llm/types.py`](src/app/core/llm/types.py) 的缓存语义结构。
2. 新增 [`src/app/core/loop/request_builder.py`](src/app/core/loop/request_builder.py) 并接入 [`AgentLoop`](src/app/core/loop/agent_loop.py)。
3. 在 [`src/app/core/llm/providers/anthropic.py`](src/app/core/llm/providers/anthropic.py) 实现显式缓存注入。
4. 在 [`src/app/core/llm/providers/openai_compatible.py`](src/app/core/llm/providers/openai_compatible.py) 增加 capability 驱动入口。
5. 运行 provider 相关验证并用厂商后台确认缓存命中。

## 结论

该方案通过“中立语义层 + 统一 request builder + provider 定制序列化”的方式，在不把 loop 主流程绑定到单一厂商协议的前提下，优先为 Anthropic 提供真实可命中的 prompt caching，并为 OpenAI-compatible 厂商保留安全扩展路径。这能满足当前目标：请求发到模型厂商 API 后，厂商后台可看到缓存命中，而无需先做前端展示。
