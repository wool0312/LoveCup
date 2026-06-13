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
- ✅ **步骤 4：后端 API 与业务流程（24 个测试全绿，服务可启动）**
- ✅ **步骤 5：前端 6 个页面与联调（浏览器端到端跑通，计分与 PRD 用例一致）**

🎉 **核心逻辑全部完成。** 后续部署为独立阶段，待你确认后再开始。

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
