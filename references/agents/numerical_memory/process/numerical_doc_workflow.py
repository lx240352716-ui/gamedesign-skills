# -*- coding: utf-8 -*-
"""
数值策划 /doc 模式 Workflow 定义

状态流程：draft -> review -> done
仅出设计文档，不做填表。填表流程在 numerical_excel_workflow.py 中。
"""

# -- 基本信息 --
name = "numerical_doc"
description = "数值策划 (/doc 模式)：读上游设计 -> 写数值设计文档 -> 用户确认"

# -- 初始状态 --
initial = "draft"

# -- 状态列表 --
states = [
    {"name": "draft",  "type": "llm",    "description": "读上游 draft.md + 查知识库 -> 写本 agent 的 draft.md"},
    {"name": "review", "type": "pause",  "description": "用户确认数值设计方案"},
    {"name": "done",   "type": "script", "description": "标记完成，通知 L0"},
]

# -- 状态转移 --
transitions = [
    ["drafted",  "draft",  "review"],
    ["approved", "review", "done"],
    ["rejected", "review", "draft"],   # 打回修改
]

# -- 知识库映射 --
knowledge = {
    "draft": ["numerical_rules.md", "numerical_examples.md", "__manifest__"],
}

# -- hooks 映射 --
hooks = {
    "on_enter_draft": "numerical_hooks.on_enter_draft",
    "on_enter_done":  "numerical_hooks.on_enter_done",
}
