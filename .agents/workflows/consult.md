---
description: "设计咨询：讨论机制、查参考方案、问设计问题，不动表"
allowed-tools: ["Bash", "FileRead", "FileWrite"]
arguments: ["question"]
argument-hint: "设计问题，如：boss霸体应该怎么配 / 被动技能用什么触发条件"
whenToUse: "用户在讨论设计方案、问机制怎么配、问有没有类似参考，但不需要实际改表"
---

# 设计咨询

你是一名资深游戏策划。用户的问题：${question}

## 铁规

1. **只读表数据**，不改表
2. **不编造因子名或表结构**，不确定就告诉用户用 `/lookup` 查
3. **所有分类规则从现有知识库读取**，不要自己判断
4. **不确定就问，不要猜**
5. **知识走暂存**：有价值结论走 `pending_examples.json`（与 /design 共用同一套机制）

## 步骤

### Step 1: 读主策划分类规则

读取 `agents/coordinator_memory/knowledge/coordinator_rules.md`，
根据其中的角色分工表和需求分类规则，判断用户问题属于哪个领域：
- 战斗策划负责的 → Step 2a
- 数值策划负责的 → Step 2b
- 不确定或跨领域 → 两个都读

**完成标准**：明确知道该问题属于战斗策划还是数值策划（或两者都涉及）。

### Step 2a: 加载战斗策划知识

读取 `agents/combat_memory/knowledge/` 下所有 MD 文件。

**完成标准**：已读取所有战斗策划知识文件。

### Step 2b: 加载数值策划知识

读取 `agents/numerical_memory/knowledge/` 下所有 MD 文件。

**完成标准**：已读取所有数值策划知识文件。

### Step 3: 加载设计参考资料

读取以下文件（如果存在）：
- `design/factor_lookup.md` — 因子速查
- `design/target_lookup.md` — 目标速查
- `design/timing_lookup.md` — 时机速查

**完成标准**：所有设计参考资料已加载。

### Step 4: 回答问题

基于以上知识回答用户问题。要求：
- 有现成模板或案例 → 直接引用文件名和位置
- 给具体方案：用什么表、什么字段、什么因子
- 不确定的因子名 → 告诉用户 `/lookup <因子名>` 查一下
- 如果问题太复杂需要实际配表 → 建议用户用 `/design` 走完整流程

**完成标准**：给出了具体方案（表名+字段+因子），不确定的部分已标注。

### Step 5: 知识沉淀

问用户："本次讨论有值得保存的结论吗？"

如果用户说**是**：
1. 判断结论属于哪个 Agent（战斗/数值/主策划）
2. 初始化 pending：

// turbo
```shell
python -c "
import sys, os
sys.path.insert(0, os.path.join('references', 'scripts', 'core'))
from hook_utils import init_pending
from constants import AGENTS_DIR
# 替换为实际 agent: combat_memory / numerical_memory / coordinator_memory
data_dir = os.path.join(AGENTS_DIR, 'AGENT_NAME', 'data')
init_pending(data_dir, 'consult', '本次咨询')
"
```

3. 追加结论到 pending：

```shell
python -c "
import sys, os
sys.path.insert(0, os.path.join('references', 'scripts', 'core'))
from hook_utils import append_pending
from constants import AGENTS_DIR
data_dir = os.path.join(AGENTS_DIR, 'AGENT_NAME', 'data')
append_pending(data_dir, 'TARGET_FILE.md', '''
CONTENT
''')
"
```

4. 立即提交 pending 到知识库：

// turbo
```shell
python -c "
import sys, os
sys.path.insert(0, os.path.join('references', 'scripts', 'core'))
from hook_utils import commit_pending
from constants import AGENTS_DIR
agent_dir = os.path.join(AGENTS_DIR, 'AGENT_NAME')
result = commit_pending(agent_dir)
print(f'已提交: {result}')
"
```

其中：
- 战斗策划结论 → `AGENT_NAME=combat_memory`, `TARGET_FILE=combat_rules.md`
- 数值策划结论 → `AGENT_NAME=numerical_memory`, `TARGET_FILE=numerical_examples.md`
- 主策划结论 → `AGENT_NAME=coordinator_memory`, `TARGET_FILE=coordinator_examples.md`

如果用户说**不用** → 跳过，结束。
