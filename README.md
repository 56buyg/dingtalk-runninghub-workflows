<p align="center">
  <img src="assets/icon.svg" alt="DingTalk RunningHub Workflows icon" width="128" />
</p>

<h1 align="center">dingtalk-runninghub-workflows</h1>

<p align="center">
  <a href="SKILL.md"><img alt="Skill entry" src="https://img.shields.io/badge/Skill-SKILL.md-1677ff"></a>
  <a href="scripts/runninghub_submit.py"><img alt="Python template" src="https://img.shields.io/badge/Python-RunningHub%20submit-0f766e"></a>
  <img alt="Bilingual" src="https://img.shields.io/badge/Docs-%E4%B8%AD%E8%8B%B1%E5%8F%8C%E8%AF%AD-f59e0b">
  <img alt="DingTalk workflow" src="https://img.shields.io/badge/DingTalk-AI%20Table-111827">
</p>

钉钉 AI 表格 / 多维表格对接 RunningHub 的自动化工作流 Skill。

A bilingual Skill for building DingTalk AI Table automations that submit jobs to RunningHub and can be extended to other third-party tools.

## 这是什么 / What This Is

这个仓库沉淀了我们对话里整理出来的钉钉自动化工作流经验，重点覆盖：

- RunningHub 文生图、图生图等发起节点
- 数量变量，一次生成多张图
- 钉钉字段到第三方 API 参数的映射
- 钉钉官方开发文档查询与标准核对
- 发起节点和回调/查询节点分离
- RunningHub 之外的第三方工具扩展方式
- 钉钉 Python 节点常见错误排查

This repository captures a reusable automation Skill for:

- RunningHub text-to-image and image-to-image submit nodes
- Quantity/batch variables for generating multiple images
- DingTalk field to external API parameter mapping
- Official DingTalk developer-doc lookup and standard verification
- Separate submit and callback/query adapters
- Extension to non-RunningHub third-party providers
- Troubleshooting DingTalk Python node and output validation errors

## 给 Agent 怎么用 / How Agents Should Use It

入口文件是 [`SKILL.md`](SKILL.md)。

The main entry point is [`SKILL.md`](SKILL.md).

推荐提示词 / Recommended prompt:

```text
Use $dingtalk-runninghub-workflows to configure a DingTalk AI Table workflow for RunningHub or a compatible third-party tool.
```

开始设计工作流前，先确认：

```text
这次按 RunningHub 标准来，还是其他第三方工具？
Should this use the RunningHub standard, or another third-party tool?
```

## 文件结构 / Repository Structure

```text
SKILL.md                          Core bilingual Skill instructions
agents/openai.yaml                OpenAI Agent UI metadata
references/automation-guide.md    Detailed field mappings and adapter contracts
scripts/runninghub_submit.py      RunningHub submit-node Python template
scripts/dingtalk_doc_lookup.py    DingTalk official-doc lookup helper
```

## 维护方式 / Maintenance

以后有新的有效内容时，按最小范围更新：

- 核心规则更新到 `SKILL.md`
- 字段映射、回调格式、排错经验更新到 `references/automation-guide.md`
- 可复用代码更新到 `scripts/runninghub_submit.py`
- 重要说明保持中英文双语

When new validated workflow knowledge appears:

- Put core rules in `SKILL.md`
- Put mappings, callback shapes, and troubleshooting notes in `references/automation-guide.md`
- Put reusable code in `scripts/runninghub_submit.py`
- Keep important instructions bilingual
