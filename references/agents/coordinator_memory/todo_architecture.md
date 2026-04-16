# 架构 TODO

> 所有架构/系统级待办在此维护。完成项归档到 done.md。
> 每次对话开始先读此文件，结束时更新。

---

## Phase 5: Skill 架构重构（2026-04-16 规划）

> 详细方案见 implementation_plan.md

### Phase 0: 抽象引擎 + 重命名 ✅（2026-04-16）

- [x] `hfsm_registry.py` → `workflow_engine.py`（通用工作流引擎）
- [x] `hfsm_bootstrap.py` → `workflow_runner.py`（启动/恢复脚本）
- [x] `build_hfsm()` → `build_workflow(config)`（声明式配置构建）
- [x] 所有 workflow .md 引用更新
- [ ] CLAUDE.md 引用更新

### Phase 1: `/doc` Skill（出设计文档）✅（2026-04-16）

- [x] 新建 `.agents/workflows/doc.md`
- [x] L0 coordinator: 新增 `plan`+`sync`+`run_next` hooks
- [x] L1 数值: 新建 `numerical_doc_workflow.py`（draft → review → done）
- [x] L1 战斗: 新建 `combat_doc_workflow.py`（draft → review → done）
- [x] L1 系统: 复用已有 workflow（不变）
- [x] 各 agent `on_enter_draft` + `on_enter_done` hook 实现
- [x] `_build_doc_pipeline` 状态机构建实现
- [x] --skill doc 和 --skill design 双向测试通过

### Phase 2: `/excel` Skill（填配表，原 /design）✅（2026-04-16）

- [x] 新建 `.agents/workflows/excel.md`
- [x] L1 数值: 新建 `numerical_excel_workflow.py`（复用现有填表状态）
- [x] L1 战斗: 新建 `combat_excel_workflow.py`（复用现有填表状态）
- [x] 前置检查: draft.md 必须存在
- [x] `_build_excel_pipeline` 实现 + 测试通过

### 后续

- [ ] 重构 `/quick` — 明确与状态机的交互方式
- [ ] 重构 `/consult` — 明确知识加载和回答流程

### 已完成（本轮测试修复）

- [x] `on_enter_locate/categorize/output` fallback: 自动从 `split_result.json` 复制
- [x] `preflight_check()` 全局启动检查（所有 workflow 覆盖）

---

## Phase 3: Stitch MCP 接入（wireframe 状态）✅ 已完成（2026-04-13）

### 实现细节

- 接入方式：Stitch MCP JSON-RPC 2.0（`https://stitch.googleapis.com/mcp`）
- 认证：`X-Goog-Api-Key: STITCH_API_KEY`（存于 `.env`）
- 每个界面约 75-90 秒生成，PNG 下载至 `data/wireframes/`
- 支持复用现有项目（`ui_sections.json.stitch_project_id`）跳过预热

### 已验证

- `赢家岛通吃` 游戏主界面：78.9s，87.9KB PNG ✅

### 子任务（全部完成）

- [x] 研究 Stitch MCP server 的接口和认证方式
- [x] 实现 wireframe hooks：ui_sections.json → Stitch → PNG
- [x] 测试：生成 1 个界面线框图
- [x] 推送到 GitHub

---

## [SHELVED] Phase 4: Wireframe 自动生成（2026-04-13 ~ 04-14，已搁置）

> 尝试了多种方案，均不满足项目需求，暂停。

- 方案1: LLM Vision → SVG 线框图 — 组件风格不统一
- 方案2: 组件规范 + SVG 拼装 — 还原度不够
- 方案3: LLM Vision → HTML 线框 — 手写还原度有限
- 方案4: screenshot-to-code（开源工具） — 已部署测试，效果不理想
- 结论：当前 LLM 生图/转码还原度不足以满足游戏 UI 线框需求

### 保留文件（仅参考）

- `knowledge/wireframes/` — 测试生成的 SVG/HTML 线框
- `references/tools/screenshot-to-code/` — 开源工具（可删）
- `references/scripts/tools/generate_wireframes.py` — 批量生成脚本

---

## 已完成（归档见 done.md）

- System Designer L1 Agent 完整实现（2026-04-10）
- HFSM L1.system 注册（2026-04-10）
- 全量代码 review + 14 项修复（2026-04-13）
- 推送 GitHub `85bbcb4`（2026-04-13）
