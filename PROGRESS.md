# Love Cup 2026 · 开发进度

> 这份文件记录每一步做了什么、为什么这么做，方便你回顾和学习。
> 每完成一步我都会更新这里。✅ = 已完成，🔄 = 进行中，⬜ = 待办。

对应文档：`PRD v1.1`（规则 v0.5）。

---

## 技术栈（已确定）

| 层 | 选型 | 说明 |
|---|---|---|
| 前端 | React + TypeScript + Vite + Tailwind（手写组件） | 响应式 Web App，手机浏览器可用 |
| 后端 | Python FastAPI + SQLAlchemy 2.x + Pydantic 2 | 计分用 `Decimal` 定点小数，绝不用 float |
| 数据库 | SQLite（单文件） | 2 人场景足够；可一键导出 JSON/CSV 留念 |
| 锁定 | 服务端时间校验 + APScheduler 定时兜底 | 按场锁定：每场开赛前 1 小时（北京时间）|
| 测试 | pytest | 覆盖 PRD §6 的 11 个验收用例 |

**决策记录：**
- 产品形态：响应式 Web App（非微信小程序）
- 管理员：两名玩家都是管理员，所有改期/改分/赔率录入进 AuditLog 互相留痕
- 部署：先只做开发版，逻辑跑通后再部署（架构已为部署预留：配置走环境变量、前后端分离）
- 数据：单届用完即弃，但提供导出功能

---

## 进度总览

- ✅ **步骤 1：项目骨架与进度文件**
- ✅ **步骤 2：后端数据模型与计分核心**
- ✅ **步骤 3：计分核心单元测试（20 个全绿）**
- ✅ **步骤 4：后端 API 与业务流程（29 个测试全绿，服务可启动）**
- ✅ **步骤 5：前端 6 个页面与联调（浏览器端到端跑通，计分与 PRD 用例一致）**
- ✅ **步骤 6：锁定规则改为「按场锁定」**
- ✅ **步骤 7：2026 世界杯赛程、自动赛果与部署**
- ✅ **步骤 8：房间管理与 PIN 权限**
- ✅ **步骤 9：赔率绑定与赔率修改限制**
- ✅ **步骤 10：比赛结果展示与历史页优化**
- ✅ **步骤 11：小组赛轮次修复**
- ✅ **步骤 12：比赛筛选**
- ✅ **步骤 13：预测隐私保护**
- ✅ **步骤 14：预测改为只填比分**

🎉 **核心逻辑、部署、自动赛程/赛果、权限与主要交互修复都已完成。**

---

## 步骤详情

### 🔄 步骤 1：项目骨架与进度文件

**目标**：建立目录结构，确立前后端分离的工程骨架。

**目录结构**：

```
LoveCup/
├── PROGRESS.md          # 本文件
├── backend/
│   ├── app/
│   │   ├── models/      # SQLAlchemy 数据模型
│   │   ├── core/        # 计分核心（纯函数，可独立测试）
│   │   ├── api/         # FastAPI 路由
│   │   └── schemas/     # Pydantic 请求/响应模型
│   └── tests/           # pytest 单元测试
└── frontend/            # React 应用（待 Node 环境就绪后初始化）
```

**为什么这样分层**：
- `core/` 是纯计分逻辑，不依赖数据库和框架，所以能被单测直接调用 → 满足 PRD "可复核"要求。
- `models/`（数据库表结构）和 `schemas/`（API 出入参）分开，是后端常见做法：数据库结构和对外接口可以各自演进，互不绑死。

---

### ✅ 步骤 2：后端数据模型与计分核心

**计分核心**（`backend/app/core/`，纯函数、不碰数据库）：
- `stages.py`：阶段基础分值表（PRD §4.1）、阶段→轮次映射、轮次权重（7/15/16/18/20/24%）。
- `scoring.py`：`score_normal` / `score_double` / `match_score`，逐字对应 PRD §5 伪代码。
  - 关键设计：WDL 与 净胜球/精确比分 分开判定 —— 淘汰赛胜负看晋级方（含点球），
    净胜球/比分看加时结束比分（不含点球），对应 PRD §4.5。
  - `Prediction.from_raw()` 自动保证「填了精确比分就同时给出净胜球」（PRD §5 约定）。
- `settlement.py`：轮次净积分、最终加权积分、冠军同分规则（PRD §4.7 三级比较）、
  大胜认定（分差比例 ≥25% 且冠军积分 >0，PRD §4.8）。

**数据模型**（`backend/app/models/`）：
- `base.py`：引擎/会话 + **`DecimalText` 自定义类型**。
  - ⚠️ 重要精度坑：SQLite 没有真 decimal 类型，SQLAlchemy 默认按 float 存，会丢精度。
    我们把 Decimal 以「文本」存储，读出还原为 Decimal，保证 `7.30` 不会变成 `7.2999…`。
    （已写脚本验证通过。）
  - 数据库地址走环境变量 `LOVECUP_DATABASE_URL`，将来部署只改 .env。
- `entities.py`：8 张表 —— Game / Match / OddsSnapshot / Prediction / MatchScore /
  RoundSummary / FinalResult / AuditLog，枚举值直接用 PRD 中文术语便于对照和导出。

### ✅ 步骤 3：计分核心单元测试

- `tests/test_scoring.py`：PRD §6 的 **11 个验收用例**逐一落成测试 + 2 个分支补充。
- `tests/test_settlement.py`：轮次加权、冠军判定、三级同分比较、大胜阈值共 7 例。
- **结果：20 passed**。运行命令：`cd backend && .venv/bin/python -m pytest -q`

**你可以这样验证**（学习用）：
```bash
cd backend
.venv/bin/python -m pytest -v        # 看每个用例的名字和 PRD 编号对照
```

### ✅ 步骤 4：后端 API 与业务流程

**时间口径**（`app/core/timeutil.py`）：北京时间 UTC+8；比赛日 = 当日12:00→次日12:00；
存 UTC、展示转北京。`match_day_of()` 按开赛北京时间是否 ≥12:00 决定归属哪个比赛日。

**结算服务**（`app/services/settlement.py`）：把数据库数据喂给计分核心，写 MatchScore
（含 breakdown 明细 JSON）、RoundSummary、FinalResult。淘汰赛点球口径已处理。

**API 路由**（`app/api/routes.py`，前缀 `/api`，共 22 个端点）：
- 开局设置 / 创建比赛 / 比赛日列表
- 预测提交（锁定后只读、决赛禁 Double、每日至多一场 Double、缺赔率禁 Double，全部已校验）
- 赔率录入（≥1.00、锁定后不可改）
- 统一锁定（手动 + 定时兜底）
- 赛果录入与自动结算
- 异常处理：作废 / 延期 / 人工改分（全部写 AuditLog 留痕）
- 实时积分 / 历史明细 / 操作留痕 / 导出（JSON + CSV）

**自动锁定**（`app/scheduler.py`）：APScheduler 每分钟扫描，把过了 12:00 的待预测比赛
自动推进为已锁定 —— 不依赖任何人手动操作。

**验证**：
- `cd backend && .venv/bin/python -m pytest -q` → **24 passed**（含完整 e2e：开局→赔率→预测→赛果→积分）
- 服务启动：`./backend/run.sh`，健康检查 `GET /api/health`
- 种子数据：`cd backend && .venv/bin/python -m scripts.seed`（建 demo 对局 + 3 场带赔率比赛）

**为部署预留**：数据库地址、CORS 来源都走环境变量（见 `backend/.env.example`）。

### ✅ 步骤 5：前端 6 个页面与联调

**技术选型**：React + TypeScript + Vite + Tailwind v3，路由用 `HashRouter`（无需服务端
配置即可在静态托管/本地直接跑）。组件手写（Card/Button/Pill/Field/Input/Banner），
没引 shadcn/ui —— 2 人的小应用，手写更轻、依赖更少。

**6 个页面**（对应 PRD §7）：
- `Setup`：开局/载入对局，玩家切换。
- `MatchDay`：按比赛日展示比赛，提交预测（WDL + 可选精确比分 + 可选 Double）。
- `Odds`：赔率录入与赛果结算（两名玩家都可操作）。
- `Standings`：实时加权积分、各轮净积分表、大胜预警。
- `History`：已结算比赛的完整计分明细（含 breakdown），导出 JSON/CSV。
- `Final`：颁奖页 —— 冠军、奖励、大胜追加环节、颁奖仪式流程。

**状态管理**：用 `useSyncExternalStore` + localStorage 记住「当前对局」和「当前玩家」，
不引额外状态库。API 基址走 `VITE_API_BASE` 环境变量，便于将来部署切换。

**端到端验证**（浏览器实跑，复现 PRD §6 用例 #5）：
- 巴西 vs 韩国，赔率 1.30/5.00/5.00；wool 预测「客胜 + 精确比分 0:1 + Double」。
- 录入赛果 0:1 并结算 → wool 单场得分 **7.00**
  （`1×(5.00−1) 命中 + 净胜球 1 + 精确比分 2 = 7`，与 PRD 完全一致）。
- 积分页：wool 第1轮 7.00 → 加权 7.00×7% = **0.49**，👑领先，大胜预警出现。
- 历史页：breakdown 明细完整可复核（base 4.00 / gd_bonus 1 / score_bonus 2 / total 7.00）。
- 颁奖页：总冠军 wool、分差比例 100%、大胜追加环节、主持人 = mei（积分较低者）。

**如何本地运行**（学习用）：
```bash
# 后端
cd backend && ./run.sh                      # 起在 :8000
cd backend && .venv/bin/python -m scripts.seed   # 灌入 demo 数据（首次）
# 前端
cd frontend && export PATH="/opt/homebrew/opt/node@22/bin:$PATH" && npm run dev
```

---

## 待办与注意事项

- 计分全程 `Decimal`，展示时才四舍五入到 2 位小数；排名比较用未舍入值（PRD §10）。
- Node 由 Homebrew 安装，且为 keg-only：前端命令前需
  `export PATH="/opt/homebrew/opt/node@22/bin:$PATH"`。
- **部署**：架构已为部署预留（配置全走环境变量、前后端分离）。待你确认后作为独立阶段进行。

---

## 步骤 6：锁定规则改为「按场锁定」✅

**改动原因**：原先是「按比赛日统一锁定」——同一比赛日（北京 12:00→次日 12:00）的所有
比赛在当天 12:00 一起锁。问题是同一天里有的比赛凌晨开赛、有的深夜开赛，统一锁会让
晚开赛的比赛过早锁死。改为**按场锁定**：每场比赛各自在「开赛前 1 小时」截止预测与赔率。

**核心改动**（`backend/app/core/timeutil.py`）：
- 新增 `LOCK_LEAD_HOURS`（默认 1，可用环境变量 `LOVECUP_LOCK_LEAD_HOURS` 调整）。
- 新增 `lock_time_for_match(kickoff) = 开赛时间 − LOCK_LEAD_HOURS`。
- 锁定判定 `is_match_locked(kickoff)` 改为按单场 kickoff 计算，不再看比赛日。
- 删除旧的按日锁定函数（`lock_time_utc` / `is_locked` / `odds_window_*`）。
- 比赛日（noon→noon）概念**保留**，但只用于：界面分组、「每个比赛日至多一次 Double」规则。

**连带改动**：
- `scheduler.py` 兜底任务改用 `is_match_locked(m.kickoff_at)` 逐场判断。
- `routes.py`：`_match_dict` 返回每场自己的 `lock_time_beijing`/`locked`；提交预测/赔率
  的拦截改为按场锁定；`list_match_days` 的 `locked` = 该日所有比赛都已锁。
- 前端 `Odds.tsx` 提示文案、`types.ts` 的 `MatchDay` 接口同步更新。

**验证**：
- 24 个 pytest 用例全部通过（kickoff 设在未来，`locked` 仍为 False，符合新规则）。
- 数据修正：3 场曾被旧规则误锁的 6/13 比赛回退为「待预测」并清空 `locked_at`。
- 浏览器实跑确认：卡塔尔 vs 瑞士 开赛 06/14 03:00 → 锁定 06/14 02:00；
  巴西 vs 摩洛哥 06:00 → 05:00；海地 vs 苏格兰 09:00 → 08:00，预测表单均已开放，
  06-13 日期标签不再显示 🔒。

---

## 步骤 7：2026 世界杯赛程、自动赛果与部署 ✅

**改动原因**：创建房间后比赛日为空，无法直接用于正式竞猜；同时希望比赛结束后自动更新比分并结算。

**赛程同步**：
- 新增/完善 `backend/app/services/match_sync.py`：从 `football-data.org` 拉取世界杯赛程。
- 新房间创建时自动填充比赛：
  - 优先使用 API 赛程；
  - API 不可用时回退到 `backend/app/core/fixtures.py` 的 72 场小组赛硬编码赛程。
- 后续淘汰赛阶段：当 API 给出真实对阵后，会自动新增/更新时间。也就是说淘汰赛赛程确定后，网页可以同步更新。

**自动赛果与结算**：
- 新增/完善 `backend/app/services/auto_result.py`。
- 定时轮询已完赛比赛，写入比分并调用结算服务。
- 比赛列表接口也会触发轻量刷新，避免后台定时任务错过后页面仍旧不更新。
- 环境变量：`FOOTBALL_DATA_API_TOKEN`。

**部署方式**：
- Render 单服务部署：FastAPI 后端同时托管前端静态文件。
- 前端构建产物复制到 `backend/static/`。
- 数据库使用 Neon PostgreSQL，生产环境通过 `LOVECUP_DATABASE_URL` 配置。
- `backend/app/models/base.py` 的 `DecimalText` 同时适配 SQLite 与 PostgreSQL：
  - SQLite：Decimal 以字符串保存；
  - PostgreSQL：Decimal 用 `NUMERIC(20, 4)`。

**关键经验**：
- 部署环境和本地环境不同：本地 SQLite，线上 PostgreSQL，所以所有迁移/类型都要考虑双环境。
- 自动结算必须幂等：重复拉取同一场赛果不应该重复加分，而是覆盖非人工分数后重算。

---

## 步骤 8：房间管理与 PIN 权限 ✅

**改动原因**：自用时只靠对局 ID 勉强够用，但一旦正式使用，需要避免别人随便改赔率、删房间或替别人提交预测。

**已完成**：
- 支持自定义对局 ID，避免系统生成 ID 太难记。
- 创建房间时设置：
  - 玩家 1 PIN
  - 玩家 2 PIN
  - 管理 PIN
- 提交预测时必须输入当前玩家 PIN。
- 修改赔率、删除对局、修改 PIN 需要管理 PIN。
- 顶部菜单新增：
  - 退出当前对局
  - 删除对局
  - PIN 设置/重置

**兼容旧数据**：
- 老对局如果没有管理 PIN，后端允许空 PIN 执行管理操作，避免用户被锁在旧房间外。
- 新正式对局应使用完整 PIN。

**涉及文件**：
- `backend/app/models/entities.py`
- `backend/app/models/base.py`
- `backend/app/api/routes.py`
- `backend/app/schemas/schemas.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/Setup.tsx`
- `frontend/src/pages/MatchDay.tsx`
- `frontend/src/pages/Odds.tsx`

---

## 步骤 9：赔率绑定与赔率修改限制 ✅

**改动原因**：如果预测提交后，赔率还能变化，Double 结算会产生争议。正确做法是：预测提交时绑定当时赔率。

**已完成**：
- `Prediction` 新增赔率快照字段：
  - `bound_home_odds`
  - `bound_draw_odds`
  - `bound_away_odds`
  - `bound_odds_source`
- 玩家提交预测时，后端把当前赔率绑定到这条预测上。
- 后续管理员修改赔率，不会影响已经提交的预测。
- 结算时优先使用预测绑定赔率；旧数据没有绑定赔率时才回退到当前赔率。
- 开赛前 1 小时锁定后，赔率不可修改。

**设计结论**：
- 赔率可以在锁定前手动更新。
- 但每条预测只使用提交瞬间的赔率，这是公平性的核心。

---

## 步骤 10：比赛结果展示与历史页优化 ✅

**改动原因**：完赛后比赛卡片曾经不稳定显示比分；历史页直接展示 `wdl_correct`、`gd_bonus` 等英文/字段名，不利于理解。

**已完成**：
- 比赛卡片中，已完赛/已结算比赛会显示实际比分。
- 历史页显示中文计分明细：
  - 胜平负：命中/未命中
  - 胜平负得分
  - 净胜球加分
  - 精确比分加分
  - Double 基础分
  - 使用赔率
  - 合计
- 分数展示从 `0.0000` 优化为 `0`、`1` 等自然格式。

**学习点**：
- 数据库存原始明细没问题，但展示层不应该直接暴露内部字段名。
- 历史页是“复盘页面”，要服务人的理解，而不是服务调试。

---

## 步骤 11：小组赛轮次修复 ✅

**问题**：所有小组赛都显示成“第1轮”，例如 6 月 27 日的小组第三轮也被标成第1轮。

**原因**：
- 原逻辑是 `round_of(Stage.GROUP)`，而 `Stage.GROUP` 只能映射到一个固定轮次。
- 但小组赛内部实际有第1/2/3轮，需要按同组 6 场赛程序号判断。

**修复**：
- `backend/app/core/fixtures.py` 新增 `group_round_for_teams()`。
- 新建房间、API 同步赛程、fallback 赛程都使用正确小组轮次。
- `backend/app/models/base.py` 启动时会修复旧房间里的错误轮次。

**验证**：
- 新增测试确认：
  - 墨西哥 vs 南非 = 第1轮
  - 捷克 vs 南非 = 第2轮
  - 捷克 vs 墨西哥 = 第3轮

---

## 步骤 12：比赛筛选 ✅

**改动原因**：小组赛 72 场太多，比赛日页面需要更容易浏览。

**已完成**（`frontend/src/pages/MatchDay.tsx`）：
- 新增筛选按钮：
  - 全部
  - 今日
  - 待预测
  - 我的未预测
  - 已结算
- “今日”按北京时间日期判断。
- “我的未预测”依赖顶部当前玩家选择，只显示该玩家还没提交预测的比赛。
- 保留原来的日期筛选按钮；状态筛选和日期筛选可以配合使用。

---

## 步骤 13：预测隐私保护 ✅

**问题**：一个人提交预测后，另一个人在比赛锁定前就能看到，存在偷看风险。

**目标规则**：
- 开赛前 1 小时锁定前：
  - 只能看到自己的预测；
  - 看不到对方具体预测。
- 锁定后：
  - 双方预测都公开显示。

**修复**：
- 后端 `GET /api/games/{game_id}/matches` 新增 `player_id` 参数。
- `_match_dict()` 根据当前查看者过滤预测：
  - 未锁定：只返回当前玩家自己的预测；
  - 锁定/结算后：返回双方预测。
- 前端请求比赛列表时带上当前玩家 ID。
- 修复前端原本“隐藏自己、显示对方”的反向过滤 bug。

**验证**：
- 新增测试：双方都提交后，未锁定前无 `player_id` 看不到预测；带玩家 ID 只看到自己；锁定后看到双方。

---

## 步骤 14：预测改为只填比分 ✅

**问题**：玩家可能填了比分 `2:1`，但误选了“客胜”，导致系统按客胜结算为 0 分。这个交互不合理。

**新规则**：
- 每场比赛只需要预测比分。
- 系统根据比分自动推导：
  - 胜平负
  - 净胜球
- 计分规则保持不变：
  - 胜平负命中：+1
  - 净胜球命中：+1
  - 精确比分命中：+2

**前端改动**：
- 删除“主胜/平/客胜”按钮。
- 删除“只猜胜平负 / +净胜球 / 精确比分”模式。
- 每场只保留两个比分输入框。
- 输入比分后页面提示系统自动判定的胜平负和净胜球。
- Double 仍保留，但跟随比分自动推导出的胜平负方向。

**后端改动**：
- `PredictionSubmit.wdl` 改为可选，后端不再依赖前端传入的胜平负。
- 如果提交了比分，后端强制用比分推导 `wdl` 和 `sgd`。
- 结算时也不信任旧数据里保存的 `wdl`：
  - 只要预测里有比分，就用比分重新推导胜平负。
- 历史页和积分页读取时，会自动复算已结算比赛的非人工分数。

**旧错分修复**：
- 瑞典 5:1 突尼斯，双方都预测 2:1：
  - 系统自动判定预测方向为主胜；
  - 胜平负命中；
  - 净胜球不命中；
  - 精确比分不命中；
  - 每人应得 1 分。
- 新测试已覆盖“数据库里旧数据 wdl 错了但比分正确”的情况，并确认会自动修成 1 分。

**验证**：
- `cd backend && .venv/bin/python -m pytest -q` → **29 passed**
- `cd frontend && npx tsc --noEmit` → 通过
