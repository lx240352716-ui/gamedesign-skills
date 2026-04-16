# -*- coding: utf-8 -*-
"""
Skill 架构重构 — 测试用例

覆盖本次重构的所有变更：
  - Phase 0: 引擎抽象 + 重命名
  - Phase 1: /doc Skill
  - Phase 2: /excel = /design 重命名
  - 清理: 旧文件删除 + 引用更新 + review 修复

运行方式:
    cd g:/op_design
    python references/scripts/tests/test_workflow.py
"""

import os
import sys
import importlib

# 路径设置
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
AGENTS_DIR = os.path.join(os.path.dirname(SCRIPTS_DIR), 'agents')
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, 'output')

sys.path.insert(0, CORE_DIR)

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


# ============================================================
# 1. 文件存在性检查
# ============================================================
print("=" * 60)
print("1. 文件存在性")
print("=" * 60)

# 新文件必须存在
new_files = {
    "workflow_engine.py": os.path.join(CORE_DIR, 'workflow_engine.py'),
    "workflow_runner.py": os.path.join(CORE_DIR, 'workflow_runner.py'),
    "numerical_doc_workflow.py": os.path.join(AGENTS_DIR, 'numerical_memory', 'process', 'numerical_doc_workflow.py'),
    "combat_doc_workflow.py": os.path.join(AGENTS_DIR, 'combat_memory', 'process', 'combat_doc_workflow.py'),
    "numerical_excel_workflow.py": os.path.join(AGENTS_DIR, 'numerical_memory', 'process', 'numerical_excel_workflow.py'),
    "combat_excel_workflow.py": os.path.join(AGENTS_DIR, 'combat_memory', 'process', 'combat_excel_workflow.py'),
}
for name, path in new_files.items():
    check(f"[NEW] {name} exists", os.path.exists(path))

# 旧文件必须已删除
old_files = {
    "hfsm_registry.py": os.path.join(CORE_DIR, 'hfsm_registry.py'),
    "hfsm_bootstrap.py": os.path.join(CORE_DIR, 'hfsm_bootstrap.py'),
    "test_hfsm.py": os.path.join(SCRIPTS_DIR, 'tests', 'test_hfsm.py'),
}
for name, path in old_files.items():
    check(f"[DEL] {name} removed", not os.path.exists(path))


# ============================================================
# 2. 引擎导入 + SKILL_CONFIGS 检查
# ============================================================
print()
print("=" * 60)
print("2. 引擎导入 + SKILL_CONFIGS")
print("=" * 60)

import workflow_engine as we

check("workflow_engine imports OK", True)
check("build_workflow() exists", hasattr(we, 'build_workflow'))
check("SKILL_CONFIGS has 'excel'", 'excel' in we.SKILL_CONFIGS)
check("SKILL_CONFIGS has 'doc'", 'doc' in we.SKILL_CONFIGS)
check("SKILL_CONFIGS has 'design'", 'design' in we.SKILL_CONFIGS)

# excel 使用 full_pipeline
check("/excel uses full_pipeline", we.SKILL_CONFIGS['excel']['structure'] == 'full_pipeline')
# design 标记 DEPRECATED
check("/design is DEPRECATED", 'DEPRECATED' in we.SKILL_CONFIGS['design']['description'])
# doc 使用 doc_pipeline
check("/doc uses doc_pipeline", we.SKILL_CONFIGS['doc']['structure'] == 'doc_pipeline')


# ============================================================
# 3. 默认值一致性
# ============================================================
print()
print("=" * 60)
print("3. 默认值一致性")
print("=" * 60)

import inspect

sig_bw = inspect.signature(we.build_workflow)
default_bw = sig_bw.parameters['skill_name'].default
check("build_workflow default = 'excel'", default_bw == 'excel', f"got '{default_bw}'")

import workflow_runner as wr
sig_bs = inspect.signature(wr.bootstrap)
default_bs = sig_bs.parameters['skill'].default
check("bootstrap default = 'excel'", default_bs == 'excel', f"got '{default_bs}'")


# ============================================================
# 4. 日志文件名检查
# ============================================================
print()
print("=" * 60)
print("4. 日志文件名")
print("=" * 60)

check("log file = workflow_debug.log",
      we._LOG_FILE.endswith('workflow_debug.log'),
      f"got '{os.path.basename(we._LOG_FILE)}'")


# ============================================================
# 5. 旧引用残留检查
# ============================================================
print()
print("=" * 60)
print("5. 旧引用残留")
print("=" * 60)

# 读取核心文件检查是否还有 hfsm_registry/hfsm_bootstrap 的代码引用
scan_files = [
    os.path.join(CORE_DIR, 'workflow_engine.py'),
    os.path.join(CORE_DIR, 'workflow_runner.py'),
    os.path.join(AGENTS_DIR, 'coordinator_memory', 'process', 'coordinator_workflow.py'),
    os.path.join(AGENTS_DIR, 'combat_memory', 'process', 'combat_workflow.py'),
]
for fpath in scan_files:
    basename = os.path.basename(fpath)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    # 注释和文档中的历史记录不算，只查 import/from 语句
    lines = content.split('\n')
    bad_imports = [l.strip() for l in lines
                   if ('from hfsm_registry' in l or 'import hfsm_registry' in l
                       or 'from hfsm_bootstrap' in l or 'import hfsm_bootstrap' in l)
                   and not l.strip().startswith('#')]
    check(f"{basename}: no hfsm imports", len(bad_imports) == 0,
          f"found: {bad_imports}")


# ============================================================
# 6. 状态机构建测试
# ============================================================
print()
print("=" * 60)
print("6. 状态机构建")
print("=" * 60)

# /excel (= full_pipeline)
try:
    model_excel = we.build_workflow('excel')
    check("/excel build OK", True)
    check("/excel initial = coordinator_parse",
          model_excel.state == 'coordinator_parse',
          f"got '{model_excel.state}'")
    check("/excel skill_name = 'excel'",
          model_excel.skill_name == 'excel',
          f"got '{model_excel.skill_name}'")
except Exception as e:
    check("/excel build OK", False, str(e))

# /doc
try:
    model_doc = we.build_workflow('doc')
    check("/doc build OK", True)
    check("/doc initial = coordinator_parse",
          model_doc.state == 'coordinator_parse',
          f"got '{model_doc.state}'")
    check("/doc skill_name = 'doc'",
          model_doc.skill_name == 'doc',
          f"got '{model_doc.skill_name}'")
except Exception as e:
    check("/doc build OK", False, str(e))

# /design (deprecated but still works)
try:
    model_design = we.build_workflow('design')
    check("/design build OK (backward compat)", True)
    check("/design initial = coordinator_parse",
          model_design.state == 'coordinator_parse',
          f"got '{model_design.state}'")
except Exception as e:
    check("/design build OK (backward compat)", False, str(e))


# ============================================================
# 7. workflow_runner 状态解析
# ============================================================
print()
print("=" * 60)
print("7. 状态解析 (_state_to_layer)")
print("=" * 60)

layer_tests = [
    ("coordinator_parse", "L0"),
    ("design_combat_match", "L1.combat"),
    ("design_numerical_match", "L1.numerical"),
    ("design_system_research", "L1.system"),
    ("docwork_combat_draft", "L1.combat"),
    ("docwork_numerical_draft", "L1.numerical"),
    ("docwork_system_draft", "L1.system"),
    ("excelwork_combat_match", "L1.combat"),
    ("excelwork_numerical_match", "L1.numerical"),
    ("executor_read", "L2"),
    ("deliver", "deliver"),
    ("completed", "completed"),
]
for state, expected in layer_tests:
    result = wr._state_to_layer(state)
    check(f"_state_to_layer('{state}') = '{expected}'",
          result == expected, f"got '{result}'")


# ============================================================
# 8. agent info 解析
# ============================================================
print()
print("=" * 60)
print("8. Agent info (get_current_agent_info)")
print("=" * 60)

class FakeModel:
    pass

agent_tests = [
    ("coordinator_parse", "L0", "主策划"),
    ("design_combat_match", "L1.combat", "战斗策划"),
    ("docwork_numerical_draft", "L1.numerical", "数值策划"),
    ("excelwork_combat_match", "L1.combat", "战斗策划"),
    ("excelwork_router", "L1", "路由"),
    ("docwork_router", "L1", "路由"),
]
for state, exp_layer, exp_agent in agent_tests:
    m = FakeModel()
    m.state = state
    info = wr.get_current_agent_info(m)
    check(f"agent_info('{state}').layer = '{exp_layer}'",
          info['layer'] == exp_layer, f"got '{info['layer']}'")
    check(f"agent_info('{state}').agent = '{exp_agent}'",
          info['agent'] == exp_agent, f"got '{info['agent']}'")


# ============================================================
# 9. Workflow 文件内容验证
# ============================================================
print()
print("=" * 60)
print("9. Workflow 内容验证")
print("=" * 60)

# doc workflows
num_doc = importlib.import_module('numerical_doc_workflow',
    package=None) if False else None
sys.path.insert(0, os.path.join(AGENTS_DIR, 'numerical_memory', 'process'))
import numerical_doc_workflow as ndw
check("numerical_doc initial = 'draft'", ndw.initial == 'draft')
check("numerical_doc name = 'numerical_doc'", ndw.name == 'numerical_doc')
check("numerical_doc has 3 states", len(ndw.states) == 3)

sys.path.insert(0, os.path.join(AGENTS_DIR, 'combat_memory', 'process'))
import combat_doc_workflow as cdw
check("combat_doc initial = 'draft'", cdw.initial == 'draft')
check("combat_doc name = 'combat_doc'", cdw.name == 'combat_doc')
check("combat_doc has 3 states", len(cdw.states) == 3)


# ============================================================
# 10. Preflight 检查
# ============================================================
print()
print("=" * 60)
print("10. Preflight")
print("=" * 60)

result = wr.preflight_check()
check("preflight_check() passes", result is True)


# ============================================================
# Result
# ============================================================
print()
print("=" * 60)
total = _pass + _fail
print(f"Result: {_pass}/{total} passed, {_fail} failed")
if _fail == 0:
    print("[OK] All tests passed!")
else:
    print(f"[WARN] {_fail} test(s) failed")
print("=" * 60)

sys.exit(0 if _fail == 0 else 1)
