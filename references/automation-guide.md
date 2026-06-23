# DingTalk AI Table RunningHub Workflow Guide / 钉钉 AI 表格 RunningHub 工作流指南

Use this reference when configuring or debugging DingTalk AI Table automations that call RunningHub or another external provider through Python or HTTP nodes.

当你需要配置或排查钉钉 AI 表格自动化，并通过 Python/HTTP 节点调用 RunningHub 或其他第三方工具时，读取本参考文件。

## Provider Route Confirmation / 工具路线确认

Start every new workflow by asking:

```text
这次按 RunningHub 标准来，还是其他第三方工具？
Should this use the RunningHub standard, or another third-party tool?
```

Route:

| Answer / 回答 | Action / 动作 |
| --- | --- |
| RunningHub | Use the RunningHub worked example and `scripts/runninghub_submit.py`. |
| 其他第三方工具 / Other provider | Request submit request, submit response, and callback/query response samples. |
| 不明确 / Unclear | Ask for the provider/tool name before writing code. |

This prevents accidental assumptions when the submit node and callback/query node use different providers or payload shapes.

这样可以避免误把所有节点都按 RunningHub 处理，尤其是发起节点和回调/查询节点可能属于不同工具时。

## DingTalk Official Docs Lookup / 钉钉官方文档查询

Use this verified route when the task needs DingTalk developer standards:

```text
GET https://open.dingtalk.com/api/open/search?keyword={query}&page=1&pageSize=5
```

Search returns official document candidates with title, summary, link, and repository. Convert links like:

```text
https://developers.dingtalk.com/document/{namespace}/{slug}
```

to full document-body HTML:

```text
https://icms-document.oss-cn-beijing.aliyuncs.com/zh-CN/dingtalk/{namespace}/topics/{slug}.html
```

Use the helper:

```bash
python scripts/dingtalk_doc_lookup.py "钉钉机器人 webhook 卡片消息" --fetch-first
```

中文流程：

1. 用自然语言关键词调用 `open.dingtalk.com/api/open/search`。
2. 从搜索结果中读取官方标题、摘要、链接和仓库分类。
3. 将 `/document/{namespace}/{slug}` 转成 OSS 正文地址。
4. 读取 HTML 正文，提取接口地址、请求方式、参数表、示例和错误码。
5. 回答时附上官方链接；生成代码时以正文参数表为准。

Validated example:

- Query: `钉钉机器人 webhook 卡片消息`
- Relevant result: `自定义机器人发送群消息`
- Official link: `https://developers.dingtalk.com/document/orgapp/custom-robots-send-group-messages`
- Body source: `https://icms-document.oss-cn-beijing.aliyuncs.com/zh-CN/dingtalk/orgapp/topics/custom-robots-send-group-messages.html`
- Observed standards include `POST https://oapi.dingtalk.com/robot/send`, `access_token`, optional `timestamp` and `sign`, `msgtype`, and message bodies for `text`, `markdown`, `actionCard`, and `feedCard`.

Do not treat `POST https://api.dingtalk.com/v1.0/aiPaaS/ai/complete` as a verified standard-query source yet. Test results showed the endpoint is reachable, but a usable answer requires request fields such as `messages` and `accessToken`; keep it out of the default workflow until a working authenticated request is confirmed.

暂不要把 `POST https://api.dingtalk.com/v1.0/aiPaaS/ai/complete` 当作已验证标准查询源。当前测试只确认接口可达，但返回提示需要 `messages` 和 `accessToken` 等字段；在拿到可用鉴权请求并跑通前，不放入默认流程。

## Recommended Table Fields / 推荐表格字段

Use provider-neutral names when the workflow may call multiple tools.

如果后续可能接入多个工具，字段尽量保持中立。

| Field / 字段 | Type / 类型 | Purpose / 用途 |
| --- | --- | --- |
| `状态` / `status` | single select | `待处理`, `处理中`, `完成`, `失败`, `已取消` |
| `工具` / `provider` | select/text | Human provider name or machine key, e.g. `runninghub` |
| `workflow_id` / `webapp_id` | text | Provider workflow/app ID |
| `提示词` / `prompt` | text | Prompt or main text input |
| `数量` / `image_count` | number/select/text | Batch count; default `1`; clamp to a safe range |
| `输入图片` / `input_image` | attachment/url | Optional image/file input |
| `请求参数JSON` / `request_json` | text | Optional provider-specific overrides |
| `外部任务ID` / `external_id` | text | External job/task/request ID; newline-separated if multiple |
| `输出链接` / `output_urls` | text | URL outputs, one per line when applicable |
| `输出JSON` / `output_json` | text | Raw or normalized provider output when URL-only output is insufficient |
| `失败原因` / `error_message` | text | Failure details |

If the workflow is RunningHub-only, existing names such as `RunningHub任务ID` are fine. Do not force a rename.

如果工作流只服务 RunningHub，已有的 `RunningHub任务ID` 等字段可以保留，不必强行改名。

## Submit Adapter Contract / 发起适配器约定

The submit adapter starts work in an external provider and returns identifiers. It should not assume the final result shape.

发起适配器负责启动外部任务并返回 ID，不要假设最终结果一定是图片链接。

Recommended return shape:

```json
{
  "success": true,
  "ok": true,
  "provider": "runninghub",
  "external_id": "external task id",
  "task_id": "legacy compatible task id",
  "error_message": "",
  "debug_info": ""
}
```

Business failures should return `success=true, ok=false`. Reserve thrown exceptions for syntax/runtime failures that cannot be caught.

第三方业务失败时返回 `success=true, ok=false`；只有无法捕获的语法/运行时错误才会导致顶层失败。

Submit extraction JSON for DingTalk:

```json
{
  "ok": true,
  "provider": "工具",
  "external_id": "外部任务ID",
  "task_id": "任务ID",
  "error_message": "失败原因",
  "debug_info": "调试信息"
}
```

Record update after submit:

| Condition / 条件 | Update / 更新 |
| --- | --- |
| `ok=true` | `状态=处理中`; write `外部任务ID` or provider-specific task field |
| `ok=false` | `状态=失败`; write `失败原因=error_message` |

## RunningHub Submit Node / RunningHub 发起节点

Use `scripts/runninghub_submit.py` for RunningHub submit nodes.

RunningHub 发起节点优先使用 `scripts/runninghub_submit.py`。

### Text-to-image / 文生图

```text
webapp_id = 2048647046302801921
```

Node mapping:

| Purpose / 用途 | nodeId | fieldName |
| --- | --- | --- |
| prompt / 提示词 | `3` | `text` |
| aspect ratio / 比例 | `1` | `aspectRatio` |
| resolution / 尺寸 | `1` | `resolution` |
| channel / 通道 | `1` | `channel` |

Python input bindings:

| Python input | DingTalk source / 钉钉来源 |
| --- | --- |
| `RUNNINGHUB_API_KEY` | Secret/text variable |
| `RUNNINGHUB_WEBAPP_ID` | `webapp_id` / `workflow_id` |
| `RUNNINGHUB_APP_NAME` | Optional `应用` |
| `RUNNINGHUB_PROMPT` | `提示词` |
| `RUNNINGHUB_IMAGE_COUNT` | `数量` |
| `RUNNINGHUB_ASPECT_RATIO` | Optional `比例` |
| `RUNNINGHUB_RESOLUTION` | Optional `大小` |
| `RUNNINGHUB_NEGATIVE_PROMPT` | Optional `负面提示词` |
| `RUNNINGHUB_INPUT_IMAGE` | Optional `输入图片` |

Quantity behavior:

- If `APP_CONFIG["文生图"]["image_count"]` is empty, the script submits multiple RunningHub tasks and returns newline-separated task IDs.
- If the RunningHub app exposes a native quantity node, fill `image_count.node_id` and `image_count.field_name`; the script submits once and writes the quantity node.
- Clamp quantity to `1-8` by default.

数量逻辑：

- 如果 `APP_CONFIG["文生图"]["image_count"]` 为空，脚本会重复发起多个 RunningHub 任务，并返回换行分隔的任务 ID。
- 如果 RunningHub 应用有原生数量节点，填写 `image_count.node_id` 和 `image_count.field_name` 后，脚本只提交一次。
- 默认数量限制为 `1-8`。

## Generic Provider Submit Node / 通用第三方发起节点

When the provider is not RunningHub:

1. Ask for provider/tool name.
2. Ask for one submit request sample or API documentation.
3. Extract endpoint, method, auth, required body fields, and response ID path.
4. Bind DingTalk fields to provider variables.
5. Return Python/HTTP node config with the same top-level envelope.

当工具不是 RunningHub：

1. 询问工具名称。
2. 索要一个发起请求样例或 API 文档。
3. 提取 endpoint、method、鉴权、请求体必填字段、任务 ID 路径。
4. 把钉钉字段绑定到第三方变量。
5. 输出 Python/HTTP 节点配置，并保持同样的顶层返回包络。

Do not reuse the RunningHub script for a non-RunningHub provider. Use it only as a pattern.

不要把 RunningHub 脚本直接拿去调用非 RunningHub 工具，只参考它的结构。

## Continuation / Callback Adapter / 回调或查询适配器

The continuation adapter may be:

- A provider callback.
- A polling query node.
- A webhook receiver.
- A second HTTP/Python node.
- A different tool than the submit node.

回调/查询适配器可能是：

- 第三方回调。
- 轮询查询节点。
- Webhook 接收节点。
- 第二个 HTTP/Python 节点。
- 和发起节点不同的另一个工具。

Before writing it, collect one real response payload. Normalize into:

```json
{
  "success": true,
  "ok": true,
  "done": true,
  "provider": "provider-key",
  "external_id": "task or request id",
  "outputs": [
    {
      "type": "image|file|text|json|url|unknown",
      "url": "https://...",
      "text": "",
      "file_name": "",
      "media_id": "",
      "mime_type": "",
      "raw": {}
    }
  ],
  "error_message": "",
  "debug_info": ""
}
```

Record update after continuation:

| Normalized value / 标准化值 | DingTalk field / 钉钉字段 |
| --- | --- |
| `done=true && ok=true` | `状态=完成` |
| `done=false && ok=true` | `状态=处理中` |
| `ok=false` | `状态=失败`, `失败原因=error_message` |
| URL outputs | `输出链接`, one URL per line |
| text outputs | Text output field or `输出JSON` |
| file/image objects | Upload/attach only if the user requires DingTalk attachment fields |
| raw JSON | `输出JSON` or `debug_info` |

Rules:

- Do not require every provider to output `output_urls`.
- Preserve raw JSON if the output type is unclear.
- Keep the submit adapter unchanged unless the submit API changes.

规则：

- 不要求所有工具都输出 `output_urls`。
- 输出类型不确定时保留原始 JSON。
- 只要发起接口没变，就不要改发起适配器。

## File / Attachment Handling / 文件与附件处理

Many providers cannot consume DingTalk internal resource URLs directly. Preferred pattern:

```text
DingTalk temporary download URL -> Python download -> provider upload -> provider file ID/name -> submit payload
```

很多第三方工具不能直接读取钉钉内部资源地址。推荐流程：

```text
钉钉临时下载地址 -> Python 下载 -> 上传到第三方 -> 第三方文件 ID/名称 -> 发起请求
```

If a payload contains a relative DingTalk path such as `/core/api/resources/...`, bind the attachment temporary download URL instead.

如果字段里拿到的是 `/core/api/resources/...` 这类相对路径，改绑附件的临时下载 URL。

## Common Errors / 常见错误

### `IndentationError`

The pasted Python lost indentation. Re-copy from the script file and confirm every `def` has an indented body.

Python 缩进丢失。重新复制脚本，确认每个 `def` 后都有缩进代码块。

### Output validation expects `success=true`

The remote Python wrapper failed before returning the expected envelope. Catch provider errors and return `success=true, ok=false`.

远程 Python 节点没有返回钉钉期望的顶层包络。捕获第三方错误，并返回 `success=true, ok=false`。

### Empty prompt/input

DingTalk variable binding is missing or uses the wrong field. Bind the Python input directly to the table field.

钉钉变量绑定缺失或绑错字段。把 Python 输入直接绑定到表格字段。

### Unknown workflow/app ID

The provider ID does not exist in adapter config, or the table field is bound to a display label instead of a machine ID.

工具 ID 不在适配器配置里，或表格字段绑定成了展示名而不是机器 ID。

### Node/field mismatch

For RunningHub, inspect `nodeInfoList`. For other providers, inspect the submit request schema. Patch only the provider adapter.

RunningHub 需要检查 `nodeInfoList`；其他工具需要检查发起请求结构。只修改对应适配器。

### Callback extraction mismatch

The response format differs from the assumed extractor. Request a real callback/query payload and rewrite only the continuation adapter.

响应格式和提取器假设不一致。索要真实回调/查询 payload，只改回调/查询适配器。
