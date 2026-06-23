---
name: dingtalk-external-tool-workflows
description: Build, modify, or debug DingTalk AI Table automations that call external tools through Python or HTTP nodes. Use when an agent needs to design a guided DingTalk workflow with provider-specific submit adapters and callback/query adapters, bind AI Table fields to external API variables, map arbitrary request/response payloads, support RunningHub text-to-image as one example, add quantity/batch variables, return stable task IDs or external IDs, normalize callback results, or troubleshoot DingTalk Python errors and output validation failures.
---

# DingTalk External Tool Workflows

## Platform Compatibility

This skill is plain Markdown plus optional Python templates. Any agent platform can use it:

- Read `SKILL.md` first.
- Read `references/automation-guide.md` when detailed field bindings, adapter contracts, callbacks, or troubleshooting are needed.
- Use scripts only as provider examples, not as universal code.
- Do not rely on Codex-specific tools or hidden memory.

## Core Model

Treat every automation as two independent adapters around a DingTalk AI Table record:

```text
DingTalk record -> submit adapter -> external provider task/id
DingTalk record <- callback/query adapter <- external provider result
```

Neither side is assumed to be RunningHub.

- The submit adapter may call RunningHub, another image model, a video API, an internal service, a storage API, a webhook, or any HTTP/Python-accessible tool.
- The callback/query adapter may receive a provider callback, poll a status endpoint, parse an HTTP response, or read another system.
- The payload shape is provider-specific. Ask for real request/response samples when the shape is unknown.

## First Confirmation

Before writing code or node configuration, confirm the provider route:

```text
这次按 RunningHub 标准来，还是其他第三方工具？
```

Route by the answer:

| Answer | Route |
| --- | --- |
| RunningHub / 文生图 / 图生图 / RunningHub app or webapp_id | Use the RunningHub example adapter and `scripts/runninghub_submit.py`. |
| Other third-party tool / internal API / webhook / unknown provider | Use the generic external-tool adapter path. Ask for a submit request sample and a callback/query response sample. |
| Unclear | Ask one short clarification before designing the workflow. |

Do not assume RunningHub just because the workflow is about AI images. Image, video, file, and internal automation providers often have different submit and callback schemas.

## Operating Rules

1. Keep the submit node small and stable. It should start the job and return identifiers, not wait for long outputs unless the user explicitly wants synchronous behavior.
2. Keep callback/query handling separate from submission. Do not hard-code callback output as `output_urls`.
3. Build provider adapters from concrete samples:
   - Submit request sample or API docs.
   - Callback/query response sample.
   - DingTalk table fields.
4. Preserve DingTalk's stable envelope:

```json
{
  "success": true,
  "ok": true,
  "external_id": "...",
  "task_id": "...",
  "error_message": "",
  "debug_info": ""
}
```

For business failures, return `success=true, ok=false`; do not let provider errors escape the top-level handler.

## Quick Workflow

1. Run the First Confirmation.
2. Identify the provider/tool for the submit node.
3. Ask for or inspect a submit request sample if it is not already known.
4. Confirm the DingTalk fields to bind.
5. Design a submit adapter:
   - Inputs: `API_KEY`/token, provider app/workflow ID, user variables.
   - Output: `external_id` or `task_id`, `ok`, `error_message`, `debug_info`.
6. Return DingTalk parameter extraction JSON for the submit step.
7. Ask for or inspect the callback/query response sample.
8. Design a continuation adapter that normalizes the provider result.
9. Return DingTalk update-record mapping based on the normalized result.

## RunningHub Example

RunningHub text-to-image is an existing provider example. Use `scripts/runninghub_submit.py` only when the submit provider is RunningHub.

Known 文生图 defaults:

```text
webapp_id = 2048647046302801921
prompt node = nodeId 3, fieldName text
aspect ratio node = nodeId 1, fieldName aspectRatio
resolution node = nodeId 1, fieldName resolution
quantity variable = RUNNINGHUB_IMAGE_COUNT
```

If the RunningHub app has no native quantity node, submit the same `nodeInfoList` repeatedly according to `RUNNINGHUB_IMAGE_COUNT`. Return multiple task IDs joined with newlines. Clamp quantity to `1-8`.

## Submit Extraction

For a submit node, keep extraction minimal and provider-neutral:

```json
{
  "ok": true,
  "external_id": "外部任务ID",
  "task_id": "任务ID",
  "error_message": "失败原因",
  "debug_info": "调试信息"
}
```

Update the current record according to the actual fields:

```text
外部任务ID/RunningHub任务ID = external_id or task_id
状态 = 处理中 if ok=true
状态 = 失败 if ok=false
失败原因 = error_message
```

## Continuation Adapter

When designing callback/query nodes, do not assume the result format. Normalize provider-specific payloads into:

```json
{
  "success": true,
  "ok": true,
  "done": true,
  "provider": "tool-name",
  "external_id": "任务ID或外部ID",
  "outputs": [],
  "error_message": "",
  "debug_info": ""
}
```

Only map `outputs` to `输出链接` when the payload actually contains URLs. If the payload contains files, media IDs, generated text, JSON, or status-only responses, preserve those fields and design matching DingTalk output fields.

## Troubleshooting

Classify errors before changing code:

- `IndentationError`: pasted Python lost indentation.
- Output validation expects `success=true`: the top-level Python node failed; wrap provider errors and return `success=true, ok=false`.
- Empty prompt/input: DingTalk variable binding is missing or wrong.
- Unknown provider app/workflow ID: fix the submit adapter config.
- Node/field mismatch: inspect provider request schema or RunningHub `nodeInfoList`.
- Callback extraction mismatch: request a real callback/query payload and rewrite only the continuation adapter.

## References

Read `references/automation-guide.md` for field design, provider adapter contracts, callback/query normalization, RunningHub example mappings, and common errors.

Read `scripts/runninghub_submit.py` only when the submit provider is RunningHub or when a Python submit adapter example is useful.
