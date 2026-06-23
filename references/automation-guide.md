# DingTalk AI Table External Tool Automation Guide

Use this reference when configuring or debugging a DingTalk AI Table automation that calls any external provider through Python or HTTP nodes. RunningHub is included only as a worked example.

## Provider Route Confirmation

Start every new workflow by asking:

```text
这次按 RunningHub 标准来，还是其他第三方工具？
```

Then route:

- **RunningHub**: use the RunningHub worked example and `scripts/runninghub_submit.py`.
- **Other third-party tool**: request the submit request sample, submit response sample, and callback/query response sample.
- **Unclear**: ask for the provider/tool name before writing code.

This prevents accidental RunningHub assumptions in workflows that call another image/video/file/internal tool.

## Recommended Table Fields

Use provider-neutral names when the workflow may call multiple tools:

| Field | Type | Purpose |
| --- | --- | --- |
| `状态` | single select | `待处理`, `处理中`, `完成`, `失败`, `已取消` |
| `工具` / `应用` | select/link | Human provider/workflow name |
| `provider` | text/select | Optional machine provider key, e.g. `runninghub`, `internal-api` |
| `workflow_id` / `webapp_id` | text | Provider workflow/app ID |
| `输入提示词` / `提示词` | text | Prompt or text input |
| `数量` | number/select/text | Batch count, default `1`, clamp to a safe range |
| `输入图片` | attachment | Optional image/file input |
| `请求参数JSON` | text | Optional provider-specific overrides |
| `外部任务ID` | text | External job/task/request ID, newline-separated if multiple |
| `输出链接` | text | URL outputs, one per line when applicable |
| `输出JSON` | text | Raw or normalized provider output when URL-only output is insufficient |
| `失败原因` | text | Failure details |

If the workflow is RunningHub-only, existing fields such as `RunningHub任务ID` are fine. Do not force a rename.

## Submit Adapter Contract

The submit adapter starts work in an external provider and returns identifiers. It should not assume the continuation provider result shape.

Recommended return shape:

```json
{
  "success": true,
  "ok": true,
  "provider": "provider-key",
  "external_id": "外部任务ID",
  "task_id": "兼容旧字段的任务ID",
  "error_message": "",
  "debug_info": ""
}
```

Business failures should return `success=true, ok=false`. Reserve thrown exceptions for syntax/runtime failures you cannot catch.

Submit parameter extraction JSON:

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

Record update:

| Condition | Update |
| --- | --- |
| `ok=true` | `状态=处理中`, write `外部任务ID` or provider-specific task field |
| `ok=false` | `状态=失败`, `失败原因=error_message` |

## Designing A Submit Adapter

When the submit provider is unknown:

1. Ask for the provider name and one submit request example or API documentation.
2. Extract endpoint, method, auth, required body fields, and response ID path.
3. Bind DingTalk fields to provider variables.
4. Return a provider-specific Python/HTTP node plan.
5. Keep output shape stable: `success`, `ok`, `external_id`/`task_id`, `error_message`, `debug_info`.

Do not reuse the RunningHub script for a non-RunningHub provider. Use it only as an implementation pattern.

## Continuation / Callback Adapter Contract

The continuation adapter may be:

- A provider callback.
- A polling query node.
- A webhook receiver.
- A second HTTP/Python node.
- A different tool than the submit node.

Before writing it, collect one real response payload. Normalize into:

```json
{
  "success": true,
  "ok": true,
  "done": true,
  "provider": "provider-key",
  "external_id": "任务ID或外部ID",
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

Record update:

| Normalized value | DingTalk field |
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
- Keep submit adapter unchanged unless the submit API changes.

## RunningHub Worked Example

Use `scripts/runninghub_submit.py` only when the submit provider is RunningHub.

### Text-to-image

```text
webapp_id = 2048647046302801921
```

Node mapping:

| Purpose | nodeId | fieldName |
| --- | --- | --- |
| prompt | `3` | `text` |
| aspect ratio | `1` | `aspectRatio` |
| resolution | `1` | `resolution` |
| channel | `1` | `channel` |

Python input bindings:

| Python input | DingTalk source |
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

## File / Attachment Handling

Many providers cannot consume DingTalk internal resource URLs directly. Preferred pattern:

```text
DingTalk temporary download URL -> Python download -> provider upload -> provider file ID/name -> submit payload
```

If a payload contains a relative DingTalk path such as `/core/api/resources/...`, bind the attachment temporary download URL instead.

## Common Errors

### `IndentationError`

The pasted Python lost indentation. Re-copy from the script file and confirm every `def` has an indented body.

### Output validation expects `success=true`

The remote Python wrapper failed before returning the expected envelope. Catch provider errors and return `success=true, ok=false`.

### Empty prompt/input

DingTalk variable binding is missing or uses the wrong field. Bind the Python input directly to the table field.

### Unknown workflow/app ID

The provider ID does not exist in the adapter config, or the table field is bound to a display label instead of a machine ID.

### Node/field mismatch

For RunningHub, inspect `nodeInfoList`. For other providers, inspect the submit request schema. Patch only the provider adapter.

### Callback extraction mismatch

The response format differs from the assumed extractor. Request a real callback/query payload and rewrite the continuation adapter only.

## Adding A New Provider

Ask for:

1. Provider/tool name.
2. Submit request sample or API docs.
3. Submit response sample.
4. Callback/query response sample, if asynchronous.
5. DingTalk table fields available for inputs and outputs.

Then deliver:

1. Submit-node input bindings.
2. Submit adapter code or HTTP-node config.
3. Submit parameter extraction JSON.
4. Record-update mapping after submit.
5. Continuation adapter plan/code based on the real response sample.
6. Record-update mapping after completion.
