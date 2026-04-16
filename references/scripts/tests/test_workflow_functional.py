# -*- coding: utf-8 -*-
"""
Skill 架构 -- 功能测试

测试状态机的实际行为：状态转移、hook 回调、状态保存/恢复、知识加载。
与 test_workflow.py（结构测试）互补。

运行方式:
    cd g:/op_design
    python references/scripts/tests/test_workflow_functional.py
"""

import os
import sys
import json
import shutil

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
AGENTS_DIR = os.path.join(os.path.dirname(SCRIPTS_DIR), 'agents')
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, 'output')
STATE_FILE = os.path.join(OUTPUT_DIR, 'task_state.json')

sys.path.insert(0, CORE_DIR)

from workflow_engine import build_workflow
import workflow_runner as wr

_pass = 0
_fail = 0


def check(name, condition, detail=""):
    global _pass, _fail
    if condition:
        _pass += 1
        print(f"  [PASS] {name}")
    else:
        _fail += 1
        print(f"  [FAIL] {name}  {detail}")


def _backup_state():
    if os.path.exists(STATE_FILE):
        shutil.copy2(STATE_FILE, STATE_FILE + '.bak')
        return True
    return False


def _restore_state(had_backup):
    if had_backup and os.path.exists(STATE_FILE + '.bak'):
        shutil.move(STATE_FILE + '.bak', STATE_FILE)
    elif os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


# ============================================================
# F1. /excel coordinator 内部状态转移
#   coordinator_workflow.py triggers:
#     parse_done, split_done, user_confirmed, dispatched
# ============================================================
print("=" * 60)
print("F1. /excel coordinator 内部状态转移")
print("=" * 60)

model = build_workflow('excel')
check("initial = coordinator_parse", model.state == 'coordinator_parse')

model.parse_done()
check("parse_done -> coordinator_split_modules",
      model.state == 'coordinator_split_modules',
      f"got '{model.state}'")

model.split_done()
check("split_done -> coordinator_user_confirm",
      model.state == 'coordinator_user_confirm',
      f"got '{model.state}'")

model.user_confirmed()
check("user_confirmed -> coordinator_dispatch",
      model.state == 'coordinator_dispatch',
      f"got '{model.state}'")


# ============================================================
# F2. /excel 层间跳转 coordinator -> design -> L1
#   dispatch 调用 _auto_route_design，读 output.json dispatch 键
#   我们直接手动设 design_combat 避免依赖文件
# ============================================================
print()
print("=" * 60)
print("F2. /excel 手动路由 design_router -> design_combat")
print("=" * 60)

model2 = build_workflow('excel')
model2.machine.set_state('design_router', model2)
model2.route_to_combat()
check("route_to_combat -> design_combat_*",
      model2.state.startswith('design_combat'),
      f"got '{model2.state}'")

model2b = build_workflow('excel')
model2b.machine.set_state('design_router', model2b)
model2b.route_to_numerical()
check("route_to_numerical -> design_numerical_*",
      model2b.state.startswith('design_numerical'),
      f"got '{model2b.state}'")

model2c = build_workflow('excel')
model2c.machine.set_state('design_router', model2c)
model2c.route_to_system()
check("route_to_system -> design_system_*",
      model2c.state.startswith('design_system'),
      f"got '{model2c.state}'")


# ============================================================
# F3. /excel L1 combat 完整内部转移
#   combat_workflow.py triggers:
#     match_done, split_done, confirmed, categorize_done,
#     translate_done, output_done
# ============================================================
print()
print("=" * 60)
print("F3. /excel L1 combat 完整内部转移")
print("=" * 60)

model3 = build_workflow('excel')
model3.machine.set_state('design_combat_match', model3)
check("start at design_combat_match", model3.state == 'design_combat_match')

steps = [
    ("match_done",      "design_combat_split"),
    ("split_done",      "design_combat_confirm"),
    ("confirmed",       "design_combat_categorize"),
    ("categorize_done", "design_combat_translate"),
    ("translate_done",  "design_combat_output"),
    ("output_done",     "design_combat_review"),
]
for trigger, expected in steps:
    getattr(model3, trigger)()
    check(f"{trigger} -> {expected}",
          model3.state == expected,
          f"got '{model3.state}'")


# ============================================================
# F4. /excel agent_done -> router 循环
# ============================================================
print()
print("=" * 60)
print("F4. /excel agent_done -> router 循环")
print("=" * 60)

model4 = build_workflow('excel')

# combat review -> agent_done -> router
model4.machine.set_state('design_combat_review', model4)
model4.design_queue = ['numerical']  # 队列中还有 numerical
model4.agent_done()
check("combat agent_done -> design_router (with queue)",
      model4.state.startswith('design_numerical'),
      f"got '{model4.state}'")

# numerical output -> agent_done -> 队列空 -> design_complete -> executor
model4.machine.set_state('design_numerical_output', model4)
model4.design_queue = []
model4.design_output = True
model4.agent_done()
check("numerical agent_done (queue empty) -> executor",
      model4.state.startswith('executor'),
      f"got '{model4.state}'")


# ============================================================
# F5. /doc coordinator 内部转移
#   doc pipeline coordinator triggers:
#     parsed, planned, confirmed, synced, has_next, all_done
# ============================================================
print()
print("=" * 60)
print("F5. /doc coordinator 内部转移")
print("=" * 60)

model5 = build_workflow('doc')
check("/doc initial = coordinator_parse", model5.state == 'coordinator_parse')

model5.parsed()
check("parsed -> coordinator_plan",
      model5.state == 'coordinator_plan',
      f"got '{model5.state}'")

model5.planned()
check("planned -> coordinator_user_confirm",
      model5.state == 'coordinator_user_confirm',
      f"got '{model5.state}'")

model5.confirmed()
check("confirmed -> docwork_router",
      model5.state == 'docwork_router',
      f"got '{model5.state}'")


# ============================================================
# F6. /doc docwork 路由
# ============================================================
print()
print("=" * 60)
print("F6. /doc docwork 路由")
print("=" * 60)

model5.route_to_combat()
check("route_to_combat -> docwork_combat_*",
      model5.state.startswith('docwork_combat'),
      f"got '{model5.state}'")


# ============================================================
# F7. /doc L1 combat_doc 内部转移
#   combat_doc_workflow triggers: drafted, approved, rejected
# ============================================================
print()
print("=" * 60)
print("F7. /doc L1 combat_doc 内部转移")
print("=" * 60)

model7 = build_workflow('doc')
model7.machine.set_state('docwork_combat_draft', model7)
check("start at docwork_combat_draft", model7.state == 'docwork_combat_draft')

model7.drafted()
check("drafted -> docwork_combat_review",
      model7.state == 'docwork_combat_review',
      f"got '{model7.state}'")

# rejected -> 打回
model7.rejected()
check("rejected -> docwork_combat_draft (revise)",
      model7.state == 'docwork_combat_draft',
      f"got '{model7.state}'")

# 再次 drafted -> approved -> done
model7.drafted()
model7.approved()
check("approved -> docwork_combat_done",
      model7.state == 'docwork_combat_done',
      f"got '{model7.state}'")

# agent_done -> coordinator_sync
model7.agent_done()
check("agent_done -> coordinator_sync",
      model7.state == 'coordinator_sync',
      f"got '{model7.state}'")


# ============================================================
# F8. Hook 回调
# ============================================================
print()
print("=" * 60)
print("F8. Hook 回调")
print("=" * 60)

model8 = build_workflow('excel')
hook_fn = getattr(model8, 'on_enter_coordinator_parse', None)
check("on_enter_coordinator_parse bound", hook_fn is not None)

if hook_fn:
    result = hook_fn()
    check("hook returns dict", isinstance(result, dict), f"got {type(result)}")
    if isinstance(result, dict):
        check("hook has 'knowledge'", 'knowledge' in result)
        check("hook has 'instruction'", 'instruction' in result)

hook_combat = getattr(model8, 'on_enter_design_combat_match', None)
check("on_enter_design_combat_match bound", hook_combat is not None)

# /doc coordinator hooks
model8d = build_workflow('doc')
hook_plan = getattr(model8d, 'on_enter_coordinator_plan', None)
check("/doc on_enter_coordinator_plan bound", hook_plan is not None)
hook_sync = getattr(model8d, 'on_enter_coordinator_sync', None)
check("/doc on_enter_coordinator_sync bound", hook_sync is not None)


# ============================================================
# F9. 知识加载
# ============================================================
print()
print("=" * 60)
print("F9. 知识加载")
print("=" * 60)

knowledge = wr.get_knowledge_files('coordinator_parse')
check("coordinator_parse has knowledge files", len(knowledge) > 0)
for kf in knowledge:
    check(f"  exists: {os.path.basename(kf)}", os.path.exists(kf))

knowledge_combat = wr.get_knowledge_files('design_combat_match')
check("design_combat_match has knowledge files", len(knowledge_combat) > 0)


# ============================================================
# F10. 状态保存与恢复
# ============================================================
print()
print("=" * 60)
print("F10. 状态保存与恢复")
print("=" * 60)

had_backup = _backup_state()
try:
    wr._save_state('design_combat_match', 'excel')
    check("state file created", os.path.exists(STATE_FILE))

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        saved = json.load(f)
    check("saved state correct", saved.get('state') == 'design_combat_match')
    check("saved skill correct", saved.get('skill') == 'excel')

    result = wr.bootstrap(skill='excel')
    check("bootstrap resumes OK", result is not None)
    if result:
        check("mode = resume", result.get('mode') == '恢复')
        check("restored state correct",
              result.get('raw_state', '').startswith('design_combat'))
finally:
    _restore_state(had_backup)


# ============================================================
# F11. 快速模式 (--start-at)
# ============================================================
print()
print("=" * 60)
print("F11. 快速模式 (start_at)")
print("=" * 60)

had_backup = _backup_state()
try:
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    result = wr.bootstrap(skill='excel', start_at='L1.combat')
    check("start_at L1.combat OK", result is not None)
    if result:
        check("state starts with design_combat",
              result.get('raw_state', '').startswith('design_combat'))
        check("mode is fast", '快速' in result.get('mode', ''))
finally:
    _restore_state(had_backup)


# ============================================================
# F12. 错误处理
# ============================================================
print()
print("=" * 60)
print("F12. 错误处理")
print("=" * 60)

try:
    build_workflow('nonexistent')
    check("invalid skill raises ValueError", False, "no exception")
except ValueError as e:
    check("invalid skill raises ValueError", True)
    check("error msg lists available skills", 'excel' in str(e))

had_backup = _backup_state()
try:
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    result = wr.bootstrap(skill='excel', start_at='L99.invalid')
    check("invalid start_at returns None", result is None)
finally:
    _restore_state(had_backup)


# ============================================================
# F13. /design 向后兼容
# ============================================================
print()
print("=" * 60)
print("F13. /design 向后兼容")
print("=" * 60)

model13 = build_workflow('design')
check("/design initial = coordinator_parse",
      model13.state == 'coordinator_parse')

model13.parse_done()
check("/design parse_done works",
      model13.state == 'coordinator_split_modules')


# ============================================================
# F14. escalate: design -> coordinator
# ============================================================
print()
print("=" * 60)
print("F14. escalate (超出范围回退)")
print("=" * 60)

model14 = build_workflow('excel')
model14.machine.set_state('design_combat_match', model14)
model14.out_of_scope = True
try:
    model14.escalate()
    check("escalate -> coordinator",
          model14.state.startswith('coordinator'),
          f"got '{model14.state}'")
except Exception as e:
    check("escalate -> coordinator", False, str(e))


# ============================================================
# F15. 工作流日志
# ============================================================
print()
print("=" * 60)
print("F15. 工作流日志")
print("=" * 60)

LOG_FILE = os.path.join(OUTPUT_DIR, 'workflow_debug.log')
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    check("log has [BUILD]", '[BUILD]' in content)
    check("log has [HOOK]", '[HOOK]' in content)
else:
    check("workflow_debug.log exists", False, "not found")


# ============================================================
# Result
# ============================================================
print()
print("=" * 60)
total = _pass + _fail
print(f"Result: {_pass}/{total} passed, {_fail} failed")
if _fail == 0:
    print("[OK] All functional tests passed!")
else:
    print(f"[WARN] {_fail} test(s) failed")
print("=" * 60)

sys.exit(0 if _fail == 0 else 1)
