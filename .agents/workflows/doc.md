---
description: "出设计文档：需求分析 → 执行计划 → 各 Agent 写 draft.md"
allowed-tools: ["Bash", "FileRead", "FileWrite"]
arguments: ["requirement"]
argument-hint: "需求描述，如：冰火双世界PVE活动 / 新增SP角色-风暴骑士"
whenToUse: "用户要出一份策划文档（活动方案、角色设计、系统设计），不需要直接填表"
---

# /doc — 出设计文档

激活后，你（LLM）进入**项目经理**身份，按工作流引擎驱动策划文档的编写。

用户的需求：${requirement}

## 启动步骤

### Step 0: Preflight 检查

// turbo

```shell
python scripts/core/workflow_runner.py --check
```

如果检查失败，告诉用户先运行 `/init` 修复项目。

### Step 1: 启动工作流

// turbo

```shell
python scripts/core/workflow_runner.py --skill doc
```

### Step 2: 按状态机指令工作

根据引擎输出的状态和 instruction，执行当前步骤。

## 流程说明

```
L0 项目经理:
  parse    → 理解需求类型
  plan     → 拆分 L1 TODO 列表（谁先做、做什么、交什么）
  confirm  → 用户确认执行计划
  run      → 按顺序派发给 L1 agent
  sync     → L1 完成后更新 TODO
  deliver  → 全部完成，交付用户

L1 系统策划:
  parse → draft → assemble → review → export（已有，不变）

L1 数值/战斗策划:
  draft  → 读上游 draft.md + 查知识库 → 写本 agent 的 draft.md
  review → 用户确认设计方案
  done   → 标记完成，通知 L0
```

## 注意事项

- **不可跳步**：必须按步骤顺序执行
- **系统策划优先**：系统文档是数值/战斗的输入
- **不确定就问**：不确定的内容向用户确认
