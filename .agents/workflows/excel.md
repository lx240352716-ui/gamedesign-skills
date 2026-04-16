---
description: "填配表：需求分析 → 执行计划 → 各 Agent 填表 → QA"
allowed-tools: ["Bash", "FileRead", "FileWrite"]
arguments: ["requirement"]
argument-hint: "需求描述，如：新增SP角色-风暴骑士"
whenToUse: "用户要做完整的策划填表流程（从理解需求到输出配表 JSON）"
---

# /excel — 填配表

激活后，你（LLM）进入**完整策划流程**，从理解需求到最终输出配表 JSON。

用户的需求：${requirement}

> [!NOTE]
> 这是原 `/design` 的重命名版。流程完全一致。

## 启动步骤

### Step 0: Preflight 检查

// turbo

```shell
python scripts/core/workflow_runner.py --check
```

### Step 1: 启动工作流

// turbo

```shell
python scripts/core/workflow_runner.py --skill excel
```

### Step 2: 按状态机指令工作

根据引擎输出的状态和 instruction，执行当前步骤。

## 流程说明

```text
L0 主策划 (coordinator):
  parse         → 理解需求
  split_modules → 拆分功能模块
  user_confirm  → 用户确认
  dispatch      → 派发给 L1

L1 设计 (design):
  数值策划: match → split → confirm → locate → fill → output
  战斗策划: match → split → confirm → categorize → translate → output → review
  系统策划: research → draft → review → export

L2 执行 (executor):
  read → write

L3 QA (pipeline):
  validate → report → done
```

## 注意事项

- **不可跳步**：必须按步骤顺序执行
- **不确定就问**：不确定的内容向用户确认
- **知识优先**：每步骤都有注入的知识库，优先参考
