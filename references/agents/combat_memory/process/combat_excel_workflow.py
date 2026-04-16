# -*- coding: utf-8 -*-
"""
战斗策划 /excel 模式 Workflow 定义

状态流程与原 combat_workflow.py 完全一致：
  match → split → confirm → categorize → translate → output → review

本文件是 excel 模式的独立副本，方便未来独立调整。
"""

# -- 基本信息 --
name = "combat_excel"
description = "战斗策划 (/excel 模式)：匹配案例 → 拆句 → 确认 → 分类 → 翻译 → 输出 → 确认"

# -- 初始状态 --
initial = "match"

# -- 状态列表 --
states = [
    {"name": "match",      "type": "llm",    "description": "读上游需求 + 查案例库"},
    {"name": "split",      "type": "llm",    "description": "逐句编号拆解需求"},
    {"name": "confirm",    "type": "pause",  "description": "等用户确认拆分结果"},
    {"name": "categorize", "type": "llm",    "description": "四要素分类：触发/效果/清除/限制"},
    {"name": "translate",  "type": "llm",    "description": "自然语言 → design_json"},
    {"name": "output",     "type": "script", "description": "组装标准 output.json"},
    {"name": "review",     "type": "pause",  "description": "等用户确认设计方案"},
]

# -- 状态转移 --
transitions = [
    ["match_done",      "match",      "split"],
    ["split_done",      "split",      "confirm"],
    ["confirmed",       "confirm",    "categorize"],
    ["categorize_done", "categorize", "translate"],
    ["translate_done",  "translate",  "output"],
    ["output_done",     "output",     "review"],
]

# -- 知识库映射 --
knowledge = {
    "match":      ["combat_rules.md", "combat_examples.md", "__manifest__"],
    "split":      ["understand/rules.md", "combat_rules.md"],
    "categorize": ["understand/rules.md"],
    "translate":  ["translate/rules.md", "translate/condition_map.md",
                   "combat_rules.md", "combat_examples.md", "__manifest__"],
    "output":     ["combat_rules.md"],
}

# -- hooks 映射（复用现有 combat_hooks） --
hooks = {
    "on_enter_match":      "combat_hooks.on_enter_match",
    "on_enter_split":      "combat_hooks.on_enter_split",
    "on_exit_confirm":     "combat_hooks.on_exit_confirm",
    "on_enter_categorize": "combat_hooks.on_enter_categorize",
    "on_enter_translate":  "combat_hooks.on_enter_translate",
    "on_enter_output":     "combat_hooks.on_enter_output",
}
