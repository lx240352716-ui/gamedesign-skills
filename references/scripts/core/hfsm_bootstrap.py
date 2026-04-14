# -*- coding: utf-8 -*-
"""
HFSM 启动/恢复/触发脚本 -- 由 /design 和 /quick skill 调用。

功能：
    - 首次启动：构建 HFSM，进入 L0，保存状态
    - 恢复：从 task_state.json 加载上次的状态
    - 快速模式（--start-at）：跳过 L0，直接从 L1 开始
    - 触发状态转移（--trigger）：执行指定触发器推进状态机
    - 列出可用触发器（--list-triggers）：输出当前状态可执行的触发器
    - 输出当前状态信息，供 LLM 读取
"""

import os
import sys
import json

# 路径设置
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, 'output')
STATE_FILE = os.path.join(OUTPUT_DIR, 'task_state.json')
AGENTS_DIR = os.path.join(os.path.dirname(SCRIPTS_DIR), 'agents')

sys.path.insert(0, CORE_DIR)
from hfsm_registry import build_hfsm

# Agent -> 知识库目录映射
KNOWLEDGE_MAP = {
    "L0": os.path.join(AGENTS_DIR, 'coordinator_memory', 'knowledge'),
    "L1.combat": os.path.join(AGENTS_DIR, 'combat_memory', 'knowledge'),
    "L1.numerical": os.path.join(AGENTS_DIR, 'numerical_memory', 'knowledge'),
    "L1.system": os.path.join(AGENTS_DIR, 'system_memory', 'knowledge'),
    "L2": os.path.join(AGENTS_DIR, 'executor_memory'),
}

# --start-at 参数 -> pytransitions 状态名 映射
START_MAP = {
    "L1.combat": "design_combat",
    "L1.numerical": "design_numerical",
    "L1.system": "design_system",
    "L2": "executor",
}


def _state_to_layer(state_str):
    """从 pytransitions 状态名解析出层级 key（对应 KNOWLEDGE_MAP）"""
    if not state_str:
        return None
    if state_str.startswith('coordinator'):
        return "L0"
    elif state_str.startswith('design_combat'):
        return "L1.combat"
    elif state_str.startswith('design_numerical'):
        return "L1.numerical"
    elif state_str.startswith('design_system'):
        return "L1.system"
    elif state_str.startswith('executor'):
        return "L2"
    return None


def get_knowledge_files(state_str):
    """根据当前 pytransitions 状态返回应加载的知识库 MD 文件列表"""
    layer = _state_to_layer(state_str)
    knowledge_dir = KNOWLEDGE_MAP.get(layer)
    if not knowledge_dir or not os.path.exists(knowledge_dir):
        return []

    md_files = []
    for f in os.listdir(knowledge_dir):
        if f.endswith('.md'):
            md_files.append(os.path.join(knowledge_dir, f))
    return md_files


def get_current_agent_info(model):
    """获取当前 Agent 的详细信息"""
    state = model.state
    if not state:
        return {"layer": None, "agent": None, "step": None}

    layer = _state_to_layer(state)
    parts = state.split('_')

    if state.startswith('coordinator'):
        return {"layer": layer, "agent": "主策划", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state.startswith('design_combat'):
        return {"layer": layer, "agent": "战斗策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('design_numerical'):
        return {"layer": layer, "agent": "数值策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('design_system'):
        return {"layer": layer, "agent": "系统策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('executor'):
        return {"layer": layer, "agent": "执行策划", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state.startswith('pipeline'):
        return {"layer": "L3", "agent": "QA", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state == 'completed':
        return {"layer": "completed", "agent": None, "step": None}
    else:
        return {"layer": state, "agent": None, "step": None}


def _save_state(model):
    """持久化当前状态到 task_state.json"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"state": model.state}, f, ensure_ascii=False, indent=2)


def _print_state_report(model, title="HFSM"):
    """输出当前状态报告"""
    agent_info = get_current_agent_info(model)
    knowledge = get_knowledge_files(model.state)

    print("=" * 50)
    print(f"  {title}")
    print("=" * 50)
    print(f"  当前状态: {model.state}")
    print(f"  当前层级: {agent_info['layer']}")
    print(f"  当前 Agent: {agent_info.get('agent', '-')}")
    print(f"  当前步骤: {agent_info.get('step', '-')}")
    print(f"  知识库: {[os.path.basename(f) for f in knowledge]}")

    # 输出当前可用触发器
    available = _get_available_triggers(model)
    if available:
        print(f"  可用触发器: {available}")
    print("=" * 50)

    return agent_info, knowledge


def _get_available_triggers(model):
    """获取当前状态可用的触发器列表"""
    current_state = model.state
    available = []

    for event_name in model.machine.events:
        if event_name.startswith('to_'):
            continue  # 跳过 pytransitions 自动生成的 to_xxx
        event = model.machine.events[event_name]
        for transitions in event.transitions.values():
            for t in transitions:
                # 检查 source 是否匹配当前状态
                if t.source == current_state:
                    available.append(event_name)
                    break

    return sorted(set(available))


# ══════════════════════════════════════════════════════════════
# 主功能：bootstrap / trigger / list
# ══════════════════════════════════════════════════════════════

def bootstrap(start_at=None):
    """启动或恢复 HFSM

    Args:
        start_at: 可选，直接从指定层级开始（如 'L1.combat'），跳过 L0。
                  用于 S_Express 快速模式。
    """
    model = build_hfsm()

    if start_at:
        # -- 快速模式：跳到指定层级 --
        if start_at not in START_MAP:
            print(f"[ERR] 未知的目标状态 '{start_at}'")
            print(f"  可选值: {list(START_MAP.keys())}")
            return None
        target_state = START_MAP[start_at]
        model.machine.set_state(target_state, model)
        _save_state(model)
        mode = f"快速模式（从 {start_at} 开始）"
    elif os.path.exists(STATE_FILE):
        # -- 恢复模式 --
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        saved_state = saved.get('state')
        if saved_state:
            model.machine.set_state(saved_state, model)
        mode = "恢复"
    else:
        # -- 首次启动（自动进入 coordinator 初始状态） --
        _save_state(model)
        mode = "首次启动"

    agent_info, knowledge = _print_state_report(model, f"HFSM {mode}")

    return {
        "mode": mode,
        "state": agent_info,
        "raw_state": model.state,
        "knowledge_files": [os.path.basename(f) for f in knowledge],
        "knowledge_paths": knowledge,
    }


def trigger(event_name):
    """触发状态转移

    Args:
        event_name: 触发器名称（如 'parse_done', 'user_confirmed'）

    Returns:
        dict: 转移结果，包含新旧状态
    """
    model = build_hfsm()

    # 恢复状态
    if not os.path.exists(STATE_FILE):
        print("[ERR] task_state.json not found, run bootstrap first")
        print("  -> python hfsm_bootstrap.py")
        return None

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        saved = json.load(f)
    old_state = saved.get('state')
    if not old_state:
        print("[ERR] task_state.json has no valid state")
        return None

    model.machine.set_state(old_state, model)

    # 检查触发器是否可用
    available = _get_available_triggers(model)
    if event_name not in available:
        # 检查触发器是否存在于状态机定义中
        all_events = [e for e in model.machine.events if not e.startswith('to_')]
        if event_name not in all_events:
            print(f"[ERR] 未知的触发器: '{event_name}'")
            print(f"  所有已注册触发器: {sorted(all_events)}")
        else:
            print(f"[ERR] 触发器 '{event_name}' 在当前状态 '{old_state}' 下不可用")
            if available:
                print(f"  当前可用触发器: {available}")
            else:
                print(f"  当前状态没有可用的触发器")
        return None

    # 尝试执行触发
    try:
        trigger_func = getattr(model, event_name, None)
        if trigger_func is None:
            print(f"[ERR] model 没有 '{event_name}' 方法")
            return None

        trigger_func()

    except Exception as e:
        # Guard 条件失败或其他异常
        error_msg = str(e)
        if 'Conditions' in error_msg or 'condition' in error_msg.lower():
            print(f"[ERR] Guard 条件不满足，触发器 '{event_name}' 无法执行")
            print(f"  当前状态: {old_state}")
            print(f"  错误详情: {error_msg}")
            # 尝试输出 Guard 函数名
            event = model.machine.events.get(event_name)
            if event:
                for transitions in event.transitions.values():
                    for t in transitions:
                        if t.source == old_state and t.conditions:
                            conditions_info = [c.func if hasattr(c, 'func') else str(c) for c in t.conditions]
                            print(f"  Guard 函数: {conditions_info}")
        else:
            print(f"[ERR] 触发器执行失败: {error_msg}")
        return None

    new_state = model.state

    # 检查状态是否变化
    if new_state == old_state:
        print(f"[WARN] 触发器 '{event_name}' 执行了但状态未变")
        print(f"  状态仍为: {old_state}")
        print(f"  可能原因: Guard 返回 False 但未抛异常")
        return None

    # 持久化新状态
    _save_state(model)

    # 输出状态变更报告
    _print_state_report(model,
        f"状态转移: {old_state} -> {new_state}")

    return {
        "old_state": old_state,
        "new_state": new_state,
        "trigger": event_name,
    }


def list_triggers():
    """列出当前状态可用的触发器"""
    model = build_hfsm()

    if not os.path.exists(STATE_FILE):
        print("[ERR] task_state.json not found, run bootstrap first")
        return None

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        saved = json.load(f)
    old_state = saved.get('state')
    if old_state:
        model.machine.set_state(old_state, model)

    available = _get_available_triggers(model)
    agent_info = get_current_agent_info(model)

    print("=" * 50)
    print(f"  当前状态: {model.state}")
    print(f"  当前 Agent: {agent_info.get('agent', '-')}")
    print(f"  当前步骤: {agent_info.get('step', '-')}")
    print("=" * 50)

    if available:
        print(f"\n  可用触发器 ({len(available)}):")
        for t in available:
            # 查找目标状态
            event = model.machine.events.get(t)
            dest = '?'
            conditions = []
            if event:
                for transitions in event.transitions.values():
                    for tr in transitions:
                        if tr.source == model.state:
                            dest = tr.dest
                            conditions = [c.func if hasattr(c, 'func') else str(c) for c in (tr.conditions or [])]
                            break
            cond_str = f" [Guard: {', '.join(conditions)}]" if conditions else ""
            print(f"    -> {t}  (dest: {dest}){cond_str}")
    else:
        print("\n  [WARN] 当前状态没有可用的触发器")
        # 列出所有触发器供参考
        all_events = sorted([e for e in model.machine.events if not e.startswith('to_')])
        if all_events:
            print(f"  所有已注册触发器: {all_events}")

    return available


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='HFSM 启动/恢复/触发脚本')
    parser.add_argument('--start-at', type=str, default=None,
                        help='直接从指定层级开始，跳过 L0（如 L1.combat, L1.numerical）')
    parser.add_argument('--trigger', type=str, default=None,
                        help='触发状态转移（如 parse_done, user_confirmed）')
    parser.add_argument('--list-triggers', action='store_true',
                        help='列出当前状态可用的触发器')
    args = parser.parse_args()

    if args.list_triggers:
        list_triggers()
    elif args.trigger:
        trigger(args.trigger)
    else:
        bootstrap(start_at=args.start_at)

