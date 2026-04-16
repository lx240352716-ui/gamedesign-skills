# -*- coding: utf-8 -*-
"""
数值策划 /excel 模式 Workflow 定义

状态流程与原 numerical_workflow.py 完全一致：
  match → split → confirm → locate → fill → output

本文件是 excel 模式的独立副本，方便未来独立调整（如去掉 match/split）。
"""

# -- 基本信息 --
name = "numerical_excel"
description = "数值策划 (/excel 模式)：匹配案例 → 拆模块 → 确认 → 定位 → 填值 → 输出"

# -- 初始状态 --
initial = "match"

# -- 状态列表 --
states = [
    {"name": "match",   "type": "llm",   "description": "读上游需求，查 examples 找同类案例"},
    {"name": "split",   "type": "llm",   "description": "按系统知识拆解为独立模块"},
    {"name": "confirm", "type": "pause", "description": "用户确认模块拆分"},
    {"name": "locate",  "type": "llm",   "description": "查 table_directory 定位真实表名+字段，查参考数据过滤"},
    {"name": "fill",    "type": "pause", "description": "展示字段清单，用户填值"},
    {"name": "output",  "type": "llm",   "description": "组装标准 output.json 交给下游"},
]

# -- 状态转移 --
transitions = [
    ["match_done",    "match",   "split"],
    ["split_done",    "split",   "confirm"],
    ["confirmed",     "confirm", "locate"],
    ["locate_done",   "locate",  "fill"],
    ["fill_done",     "fill",    "output"],
    ["retry_locate",  "fill",    "locate"],
]

# -- 知识库映射 --
knowledge = {
    "match":  ["numerical_rules.md", "systems_index.md", "numerical_examples.md", "__manifest__"],
    "split":  ["numerical_rules.md", "requirement_structures.md"],
    "locate": ["table_directory.md", "numerical_rules.md", "requirement_structures.md", "__manifest__"],
    "output": ["numerical_rules.md"],
}

# -- hooks 映射（复用现有 numerical_hooks） --
hooks = {
    "on_enter_match":    "numerical_hooks.on_enter_match",
    "on_enter_split":    "numerical_hooks.on_enter_split",
    "on_exit_confirm":   "numerical_hooks.on_exit_confirm",
    "on_enter_locate":   "numerical_hooks.on_enter_locate",
    "on_exit_locate":    "numerical_hooks.on_exit_locate",
    "on_enter_fill":     "numerical_hooks.on_enter_fill",
    "on_enter_output":   "numerical_hooks.on_enter_output",
    "on_exit_output":    "numerical_hooks.on_exit_output",
}
