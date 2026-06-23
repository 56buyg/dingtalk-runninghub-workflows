---
name: dingtalk-runninghub-workflows
description: >-
  Build, modify, or debug DingTalk AI Table automations for RunningHub workflows and compatible third-party providers. Use when an agent needs a bilingual Chinese/English guided workflow for DingTalk submit nodes, RunningHub text-to-image or image-to-image jobs, quantity/batch variables, provider-specific submit adapters, callback/query adapters, stable task IDs or external IDs, normalized outputs, or troubleshooting DingTalk Python and response validation errors. 适用于钉钉宜搭/多维表格/AI 表格自动化对接 RunningHub 或其他第三方工具时，设计发起节点、回调/查询节点、字段映射、批量出图数量变量和错误排查。
---

# DingTalk RunningHub Workflows / 钉钉 RunningHub 工作流

Use this skill to design DingTalk AI Table automations that submit work to RunningHub first, while still supporting other third-party tools when the user chooses a different provider.

使用本 Skill 搭建钉钉 AI 表格自动化：默认以 RunningHub 出图工作流为主线，同时保留“其他第三方工具”的发起节点和回调/查询节点扩展方式。

## Platform Compatibility / 平台兼容

This skill is plain Markdown plus optional Python templates. It can be reused by Codex, OpenAI Agents, Claude, Gemini, Dify, Coze, n8n-style agents, or any platform that can read instructions and adapt code.

本 Skill 不依赖某个专属平台。任何能读取 Markdown 指令、生成 Python/HTTP 节点配置的 Agent 都可以复用。

- Read `SKILL.md` first for the guided workflow.
- Read `references/automation-guide.md` when field bindings, adapter contracts, callback normalization, or troubleshooting details are needed.
- Use `scripts/runninghub_submit.py` only as the RunningHub submit-node template.
- Do not treat the RunningHub script as universal code for every provider.

## First Confirmation / 第一步确认

Before writing code or node configuration, ask the user:

```text
这次按 RunningHub 标准来，还是其他第三方工具？
Should this use the RunningHub standard, or another third-party tool?
```

Route by the answer:

| User answer / 用户回答 | Route / 处理方式 |
| --- | --- |
| RunningHub, 文生图, 图生图, webapp_id, RunningHub app | Use the RunningHub adapter and `scripts/runninghub_submit.py`. 使用 RunningHub 模板。 |
| Other third-party tool, internal API, webhook, unknown provider | Use the generic provider path. Ask for submit and callback/query samples. 走通用第三方工具路径，先要样例。 |
| Unclear / 不明确 | Ask one short clarification before designing the workflow. 先追问工具名称或调用方式。 |

Do not assume the callback/query format is RunningHub just because the submit node is RunningHub. The later node may call another tool, receive a custom webhook, or parse a different response shape.

不要因为前面的发起节点是 RunningHub，就默认后面的回调/查询节点也一定是 RunningHub；它可能换成其他工具、Webhook 或完全不同的响应格式。

## Core Model / 核心模型

Treat every automation as two independent adapters around one DingTalk record:

```text
DingTalk record -> submit adapter -> provider task or request ID
DingTalk record <- callback/query adapter <- provider result
```

把每条钉钉记录看成中间状态，前后两段都可以独立替换：

```text
钉钉记录 -> 发起适配器 -> 外部任务 ID
钉钉记录 <- 回调/查询适配器 <- 外部结果
```

The submit adapter starts work and returns identifiers. The callback/query adapter normalizes provider-specific results back into DingTalk fields.

发起适配器只负责启动任务并返回 ID；回调/查询适配器负责把第三方结果标准化后写回钉钉字段。

## Operating Rules / 操作规则

1. Keep the submit node small. It should start the job and return `external_id` or `task_id`.
2. Keep callback/query handling separate from submission unless the user explicitly wants synchronous behavior.
3. Build unknown providers from real request/response samples, not guesses.
4. Preserve DingTalk's top-level success envelope so platform output validation passes.
5. For provider business failures, return `success=true, ok=false`; do not let the whole Python node fail.

中文规则：

1. 发起节点保持轻量，只启动任务并返回 `external_id` 或 `task_id`。
2. 回调/查询逻辑和发起逻辑分开，除非用户明确要同步等待结果。
3. 未知第三方工具必须基于真实请求/响应样例配置。
4. 钉钉节点顶层始终返回 `success=true`，避免“出参校验不通过”。
5. 第三方业务失败用 `ok=false` 表达，不要让 Python 节点直接抛到顶层。

Recommended submit return shape / 推荐发起节点返回：

```json
{
  "success": true,
  "ok": true,
  "provider": "runninghub",
  "external_id": "...",
  "task_id": "...",
  "error_message": "",
  "debug_info": ""
}
```

## Quick Workflow / 快速流程

1. Ask the First Confirmation.
2. Identify whether the submit provider is RunningHub or another tool.
3. Confirm DingTalk input fields, especially prompt, app/workflow ID, and quantity.
4. Design the submit adapter and return DingTalk extraction JSON.
5. Ask for the callback/query response sample before writing the continuation node.
6. Normalize completion results into status, output links/files/text/JSON, and error message.
7. Return DingTalk update-record mapping.

中文流程：

1. 先确认“RunningHub 标准”还是“其他第三方工具”。
2. 确认发起节点调用的工具。
3. 确认钉钉字段：提示词、应用/工作流 ID、数量变量等。
4. 输出发起节点代码或 HTTP 配置，以及参数提取 JSON。
5. 在写回调/查询节点前，先拿真实响应样例。
6. 把结果标准化为状态、输出链接/文件/文本/JSON、失败原因。
7. 输出钉钉记录更新映射。

## RunningHub Main Path / RunningHub 主线

Use `scripts/runninghub_submit.py` when the submit provider is RunningHub.

当发起节点是 RunningHub 时，优先使用 `scripts/runninghub_submit.py`。

Known text-to-image defaults / 已知文生图默认配置：

```text
webapp_id = 2048647046302801921
prompt node = nodeId 3, fieldName text
aspect ratio node = nodeId 1, fieldName aspectRatio
resolution node = nodeId 1, fieldName resolution
quantity variable = RUNNINGHUB_IMAGE_COUNT
```

Quantity behavior / 数量变量逻辑：

- If the RunningHub app has a native quantity node, configure `image_count.node_id` and `image_count.field_name`.
- If it has no native quantity node, submit the same `nodeInfoList` repeatedly according to `RUNNINGHUB_IMAGE_COUNT`.
- Clamp quantity to `1-8` unless the user and provider explicitly require another safe range.
- Return multiple task IDs as newline-separated values.

中文说明：

- 如果 RunningHub 应用本身有“数量/张数”节点，就填写 `image_count.node_id` 和 `image_count.field_name`。
- 如果没有原生数量节点，就按 `RUNNINGHUB_IMAGE_COUNT` 重复发起多次。
- 默认把数量限制在 `1-8`，避免误触发大量任务。
- 多个任务 ID 用换行拼接，便于写回同一个钉钉字段。

## Other Providers / 其他第三方工具

When the user chooses another provider, ask for:

1. Provider/tool name.
2. Submit endpoint or request sample.
3. Submit response sample and the ID path.
4. Callback/query response sample if the task is asynchronous.
5. DingTalk table fields for inputs and outputs.

用户选择其他第三方工具时，先要：

1. 工具名称。
2. 发起接口或请求样例。
3. 发起响应样例，以及任务 ID 在哪里。
4. 异步任务的回调/查询响应样例。
5. 钉钉输入/输出字段。

Then create a provider-specific adapter while keeping the DingTalk envelope and normalized output shape stable.

然后只替换第三方适配逻辑，钉钉侧的返回包络和标准化结果尽量保持稳定。

## References / 参考文件

Read `references/automation-guide.md` for detailed field design, adapter contracts, callback/query normalization, RunningHub mappings, and common errors.

需要字段设计、节点配置、回调标准化、RunningHub 映射和报错排查时，读取 `references/automation-guide.md`。

Read `scripts/runninghub_submit.py` only when the submit provider is RunningHub or when a Python submit adapter example is useful.

只有在发起节点是 RunningHub，或需要参考 Python 发起适配器写法时，读取 `scripts/runninghub_submit.py`。

## Maintenance / 维护约定

When new validated workflow content is added later, update the narrowest relevant file:

- Put routing rules and core behavior in `SKILL.md`.
- Put field mappings, node contracts, callback shapes, and troubleshooting notes in `references/automation-guide.md`.
- Put reusable RunningHub submit code in `scripts/runninghub_submit.py`.
- Keep important instructions bilingual, with Chinese first when the workflow is DingTalk-specific.
- Commit the change and push the repository to `main`.

后续有新的有效内容时，按最小范围维护：

- 路由规则和核心行为放进 `SKILL.md`。
- 字段映射、节点约定、回调格式、报错排查放进 `references/automation-guide.md`。
- 可复用的 RunningHub 发起代码放进 `scripts/runninghub_submit.py`。
- 重要说明保持中英文双语；钉钉场景优先中文。
- 修改后提交并推送到 `main`。
