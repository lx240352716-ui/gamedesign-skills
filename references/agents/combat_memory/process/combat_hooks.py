# -*- coding: utf-8 -*-
"""
战斗策划 Hooks

每个 on_enter / on_exit 函数对应 workflow 中的一个状态。
函数无参数，读文件获取上下文，返回 dict 给 LLM 或下游。

hooks 做确定性操作（查文件、保存JSON），LLM 做判断决策。
结构对齐 numerical_hooks.py。
"""

import os
import sys
import json
from datetime import datetime

# ── 路径 ──
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'references', 'scripts', 'core'
))

from constants import agent_paths
from hook_utils import (
    load_json as _load_json, save_json as _save_json,
    load_md as _load_md_raw, load_md_batch,
    init_pending, append_pending,
    prepare_field_context,
)

_p = agent_paths('combat_memory')
KNOWLEDGE_DIR = _p['knowledge_dir']
DATA_DIR = _p['data_dir']
COORDINATOR_DATA = agent_paths('coordinator_memory')['data_dir']
SYSTEM_DATA_DIR = agent_paths('system_memory')['data_dir']


# ── /doc 模式 hooks ─────────────────────────────────

def on_enter_draft():
    """/doc 模式: 读上游 system draft.md + plan.json -> 返回上下文供 LLM 写战斗设计文档。"""
    context = {}

    # 1. 读 plan.json 获取本 agent 的任务描述
    plan_path = os.path.join(COORDINATOR_DATA, 'plan.json')
    if os.path.exists(plan_path):
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        for item in plan.get('todo', []):
            if item.get('agent') == 'combat':
                context['task'] = item.get('task', '')
                context['input_from'] = item.get('input', '')
                break

    # 2. 读上游 system draft.md 作为参考
    system_draft = os.path.join(SYSTEM_DATA_DIR, 'draft.md')
    if os.path.exists(system_draft):
        with open(system_draft, 'r', encoding='utf-8') as f:
            context['system_draft'] = f.read()

    # 3. 读本 agent 已有的 draft.md（如果有，用于继续编辑）
    my_draft = os.path.join(DATA_DIR, 'draft.md')
    if os.path.exists(my_draft):
        with open(my_draft, 'r', encoding='utf-8') as f:
            context['existing_draft'] = f.read()

    instruction = (
        "你是战斗策划。请根据上游系统设计文档和任务描述，写出战斗设计方案。\n"
        "产出写入 data/draft.md。\n"
        "方案需包含：战斗机制、技能设计、Boss设计、元素系统。\n"
        "写完后输出 trigger: drafted"
    )

    return {
        "instruction": instruction,
        "context": context,
        "knowledge": [],
    }


def on_enter_done():
    """/doc 模式: 标记战斗策划完成，更新 plan.json。"""
    plan_path = os.path.join(COORDINATOR_DATA, 'plan.json')
    if os.path.exists(plan_path):
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        for item in plan.get('todo', []):
            if item.get('agent') == 'combat' and item.get('status') == 'running':
                item['status'] = 'done'
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

    return {"status": "done", "trigger": "agent_done"}


# ── /excel 模式 hooks（原有） ───────────────────────

def _load_md(filename):
    """加载知识库 MD 文件"""
    return _load_md_raw(KNOWLEDGE_DIR, filename)


# ────────────────────────────────────────────
# match: 读上游需求 + 查案例
# ────────────────────────────────────────────
def on_enter_match():
    """
    进入 match: 加载上游需求、战斗案例库。
    初始化 pending。
    """
    # 读 coordinator output
    coordinator_output = _load_json(os.path.join(COORDINATOR_DATA, 'output.json'))
    upstream = {}
    if coordinator_output and 'dispatch' in coordinator_output:
        upstream = coordinator_output['dispatch'].get('combat', {})

    # 初始化 pending（覆盖写，清除上一次残留）
    init_pending(DATA_DIR, upstream.get('task_id', ''), upstream.get('requirement', ''))

    return {
        "knowledge": [
            _load_md('combat_rules.md'),
            _load_md('combat_examples.md'),
        ],
        "upstream": upstream,
        "instruction": (
            "你现在是战斗策划。请阅读上游需求和案例库：\n"
            "1. 在案例库中查找类似的 buff/技能实现方案\n"
            "2. 判断需求复杂度（单 buff / 多 buff 联动 / 全新机制）\n"
            "3. 如有匹配案例，标注参考案例编号"
        ),
    }


# ────────────────────────────────────────────
# split: 逐句拆解需求
# ────────────────────────────────────────────
def on_enter_split():
    """
    进入 split: 加载 match 结果 + 理解知识 → 拆句。
    """
    match_result = _load_json(os.path.join(DATA_DIR, 'match_result.json')) or {}

    return {
        "knowledge": [
            _load_md('understand/rules.md'),
            _load_md('combat_rules.md'),
        ],
        "match_result": match_result,
        "instruction": (
            "请将需求逐句编号拆解：\n"
            "1. 每句独立描述一个效果或条件\n"
            "2. 标注每句涉及的表（FightBuff / _Buff / BuffActive / _BuffCondition）\n"
            "3. 将结果写入 data/split_result.json\n"
            "格式：{requirement, clauses: [{id, text, tables: [...]}]}"
        ),
    }


# ────────────────────────────────────────────
# confirm: 用户确认拆分（pause 状态，on_exit 保存）
# ────────────────────────────────────────────
def on_exit_confirm():
    """
    退出 confirm: 保存确认后的拆分结果 + 追加案例。
    """
    split_result = _load_json(os.path.join(DATA_DIR, 'split_result.json')) or {}

    # 保存确认版本
    _save_json(os.path.join(DATA_DIR, 'confirmed_split.json'), split_result)

    # 追加到 pending（不直接写 examples.md）
    clauses = split_result.get('clauses', [])
    requirement = split_result.get('requirement', '未知需求')
    clause_texts = ', '.join(c.get('text', '?')[:20] for c in clauses[:3])
    append_pending(DATA_DIR, "combat_examples.md",
                   f"\n### 案例: {requirement}\n- 子句: {clause_texts}\n")

    return {"status": "OK", "confirmed_clauses": len(clauses)}


# ────────────────────────────────────────────
# categorize: 四要素分类
# ────────────────────────────────────────────
def on_enter_categorize():
    """
    进入 categorize: 加载确认后的拆分 + 分类规则 → LLM 分类。
    """
    confirmed = _load_json(os.path.join(DATA_DIR, 'confirmed_split.json'))
    if not confirmed:
        confirmed = _load_json(os.path.join(DATA_DIR, 'split_result.json')) or {}
        if confirmed:
            _save_json(os.path.join(DATA_DIR, 'confirmed_split.json'), confirmed)
            print("  [WARN] confirmed_split.json not found, auto-copied from split_result.json")

    return {
        "knowledge": [
            _load_md('understand/rules.md'),
        ],
        "confirmed_split": confirmed,
        "instruction": (
            "对每个子句分类为四要素之一：\n"
            "- 触发(trigger): 什么时候生效\n"
            "- 效果(effect): 产生什么效果\n"
            "- 清除(clear): 什么时候消失\n"
            "- 限制(limit): 有什么约束条件\n"
            "将结果写入 data/categorized.json\n"
            "格式：{clauses: [{id, text, category, tables}]}"
        ),
    }


# ────────────────────────────────────────────
# translate: 自然语言 → design_json
# ────────────────────────────────────────────
def on_enter_translate():
    """
    进入 translate: 加载翻译规则 + 条件映射 + 案例 → LLM 翻译。
    注入 field_context 确保 LLM 使用真实 Row6 字段名。
    """
    categorized = _load_json(os.path.join(DATA_DIR, 'categorized.json')) or {}

    # 从分类结果中提取涉及的表名
    table_names = set()
    for clause in categorized.get('clauses', []):
        for t in clause.get('tables', []):
            table_names.add(t)
    if not table_names:
        table_names = {'FightBuff', '_Buff', 'BuffActive', '_BuffCondition'}

    # 统一取字段映射
    field_ctx = prepare_field_context(list(table_names))

    return {
        "knowledge": [
            _load_md('translate/rules.md'),
            _load_md('translate/condition_map.md'),
            _load_md('combat_rules.md'),
            _load_md('combat_examples.md'),
        ],
        "categorized": categorized,
        "field_context": field_ctx,
        "instruction": (
            "将分类后的子句翻译为 design_json：\n"
            "1. 每个 buff 对应一组 FightBuff + _Buff + BuffActive 行\n"
            "2. 条件类子句对应 _BuffCondition 行\n"
            "3. 参考案例中的字段值模式\n"
            "4. 不确定的字段标注 _note 说明\n"
            f"5. {field_ctx['instruction']}\n"
            "将结果写入 data/translated.json\n"
            "格式：{tables: {FightBuff: [...], _Buff: [...], BuffActive: [...], _BuffCondition: [...]}}"
        ),
    }


# ────────────────────────────────────────────
# output: 组装标准 output.json
# ────────────────────────────────────────────
def on_enter_output():
    """
    进入 output: 读 translated.json → 组装标准 output.json 交给下游。
    注入 field_context 供 LLM 校验字段名。
    """
    translated = _load_json(os.path.join(DATA_DIR, 'translated.json')) or {}
    confirmed = _load_json(os.path.join(DATA_DIR, 'confirmed_split.json'))
    if not confirmed:
        confirmed = _load_json(os.path.join(DATA_DIR, 'split_result.json')) or {}
        if confirmed:
            _save_json(os.path.join(DATA_DIR, 'confirmed_split.json'), confirmed)
            print("  [WARN] confirmed_split.json not found, auto-copied from split_result.json")

    tables = translated.get('tables', {})
    requirement = confirmed.get('requirement', translated.get('requirement', ''))

    # 统一取字段映射
    field_ctx = prepare_field_context(list(tables.keys()))

    # 组装标准 output（与 numerical 格式一致）
    output = {
        "_schema": "combat_output",
        "requirement": requirement,
        "tables": tables,
    }
    _save_json(os.path.join(DATA_DIR, 'output.json'), output)

    # 追加到 pending
    table_names = list(tables.keys())
    row_counts = {t: len(rows) if isinstance(rows, list) else 0 for t, rows in tables.items()}
    content = f"\n- 需求: {requirement}\n- 涉及表: {', '.join(table_names)}\n"
    for t, c in row_counts.items():
        content += f"  - {t}: {c} 行\n"
    append_pending(DATA_DIR, "combat_examples.md", content)

    return {
        "status": "OK",
        "tables": table_names,
        "requirement": requirement,
        "row_counts": row_counts,
        "field_context": field_ctx,
        "instruction": (
            "校验 output.json 中所有字段名是否与 field_context 一致。\n"
            + field_ctx['instruction']
        ),
    }
