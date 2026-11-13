# coldtier · 数仓存储冷热分层与迁移收益测算台

> 一句话：给数仓每一张表按「90 天访问热度」量体温，再用净收益与风险闸门算出「谁该迁到冷区、迁了能省多少、什么时候回本」。

## 1. 真实场景（模拟客户）

| 项 | 内容 |
|---|---|
| 客户 | 青禾零售 · 数据平台组（9 人），维护 42 张数仓表、约 42 TB 明细，月度存储费约 ¥3.8 万 |
| 现有工作流 | 每季度凭印象挑「半年没人查」的表归档到对象存储冷区；用 Excel 按单价拍脑袋估省；迁移前没有闸门 |
| 三个痛点 | ① 查询热度没有口径，谁热谁冷靠猜；② 迁移能省多少钱算不清（还漏了一次性迁移成本）；③ 误迁风险没有闸门 —— 去年误迁 2 张月报底表，回迁花 2 天 |
| 上游 | 表元数据（大小 / 分区 / 压缩 / 最近写入）+ 按天聚合的查询日志（本仓库 seed 生成 3,600 行日访问） |
| 本系统替代 | 「凭印象挑表 + Excel 估省」→「热度口径统一 + 净收益测算 + 风险闸门 + 工单导出」 |
| 下游 | 季度存储预算评审（财务）、迁移工单（平台组执行）、报表 owner 的确认回执 |
| 一天的工作剧本 | 09:10 陈可欣（admin）在「策略与试算」确认本季单价 热 1.05 / 温 0.85 / 冷 0.55 ¥/GB·月；09:35 林哲（analyst）把阈值调到 20 试算，命中 12 张，预估月省 ¥6,840；10:05 勾选前 8 张建计划 `MP-2026Q4-00x`；10:20 风险复检，`ads.monthly_finance_report_base`、`dws.store_daily_gmv` 近 7 天仍被访问 → 阻断；10:32 逐张移除阻断项；10:40 提交 6 张，净年省 ¥51,300、平均回收期 1.8 月；10:45 导出工单 CSV 交平台组排期；11:00 赵敏（viewer）在只读视图核对收益与风险。 |

## 2. 角色与权限（后端 RBAC 真实返回 403）

| 角色 | 账号 | 主要页面 | 权限 | 典型动作 |
|---|---|---|---|---|
| `admin` 平台负责人 | `admin@coldtier.io` | 全部 | `policies:write`、`audit:read`、`tables:recompute`、`trial:run`、`plans:*` | 改单价与冷区条件（升版）、看审计台账、重算热度 |
| `analyst` 数据开发 | `analyst@coldtier.io` | 概览 / 表热度 / 策略与试算 / 迁移计划 | `trial:run`、`plans:write`、`plans:submit`、`plans:export`、`tables:recompute` | 试算、建计划、风险复检、提交、导出工单 CSV |
| `viewer` 财务与报表 owner | `viewer@coldtier.io` | 概览 / 表热度（只读） | 只读 | 核对收益与风险；建计划/试算/导出/改策略一律 403 |

演示密码统一 `Demo@2026`，域名 `coldtier.io`。

## 3. 主要功能（5 页 + 4 实体贯穿）

1. **登录**（`/login`）：三角色演示账号一键填充，失败态可重试。
2. **存储概览**（`/overview`）：三档货架（体积 / 单价 / 月成本）、分层 × 温区体积树图（squarified，自绘 SVG）、42 张表货架清单（温区/分层/搜索/排序）、候选温度计、最热表与最大降冷机会、审计尾行。
3. **表热度详情**（`/tables/:id`）：90 天访问序列 + 衰减权重图（自绘 SVG）、温度计、风险闸门逐项结论、收益测算、表元数据、同层邻表。
4. **策略与试算**（`/policies`）：阈值滑杆 + 试算（命中数 / 月省 / 年省 / 净年省 / 回收期）、逐表勾选、以选中项建计划；admin 可编辑三档单价与冷区前置条件（保存即升版 v+1，旧版归档）。
5. **迁移计划**（`/plans`）：计划台账（左）+ 计划工位（右）：风险复检 → 移除阻断项 → 提交 → 导出工单 CSV；admin 额外可见审计台账。

实体贯穿：`TableProfile` / `AccessStat` / `TierPolicy` / `MigrationPlan`（含子聚合 `MigrationPlanItem`）
表 → `backend/src/models/*` → `schemas/*` → `services/*` → `controllers/*` + `routes/*` → 前端 `api/*` → `stores/*` → `pages` + `components/domain/*`。

## 4. 两个后端真算算法（Python，前端不含任何结果常量）

**算法 1 热度评分**（`backend/src/services/heat_service.py`）

```
w(d)      = 0.5 ^ (d / 14)                       # d = 距今天数，半衰期 14 天，窗口 90 天
W         = Σ_{d=0..89} access_count(d) × w(d)   # 指数衰减加权访问量
S_decay   = 100 × W / max(W over all tables)      # 归一化 0-100
B         = min(20, 8 × report_refs)              # 报表引用加成，+8/条，上限 20
S         = min(100, S_decay + B)
分层建议    S ≥ 60 → hot ｜ 20 ≤ S < 60 → warm ｜ S < 20 且近 30 天访问 = 0 → cold
           S < 20 但近 30 天仍有访问 → warm（冷存前置条件不满足，保守留温区）
```

**算法 2 净收益与风险闸门**（`backend/src/services/cost_service.py`）

```
price_before  = 表当前所在层单价（热区候选即 hot_price）
cost_before   = size_GB × price_before
cost_after    = size_GB × cold_price
save_month    = cost_before − cost_after
migration_cost= size_GB × migrate_price + migrate_fixed     # 跨区重写流量 + 每表工单/校验人工
payback_months= migration_cost / save_month
net_save_year = save_month × 12 − migration_cost            # 首年净省
风险闸门      近 7 天有访问 → block ｜ 被报表引用 → warn（需 owner 确认）｜ 分区 < 3 → warn（无法灰度回迁）
计划汇总      avg_payback = Σ迁移成本 / Σ月省（按节省额加权）
```

复现条件：seed 固定 42 张表与 3,600 行日访问（确定性哈希抖动），阈值 20 时结果恒为
`命中 12 张 / 月省 6840 / 年省 82080`；勾选前 8 张并移除 2 张阻断项后
`6 张 / 净年省 51300 / 平均回收期 1.8 月 / 工单 CSV 6 行`。

## 5. 快速启动

```bash
cp .env.example .env          # 按需改端口/口令
docker compose config --quiet
docker compose up -d --build
docker compose ps             # 等 5/5 healthy（约 40-90s）
open http://localhost:18255   # 前端；后端直连 http://localhost:19255/api/health
```

seed 由后端容器首启自动执行一次（`SEED_DEMO=true`），也可手动重跑（幂等）：

```bash
docker compose exec backend python -m scripts.seed_demo
# 末行应逐字为：
# SEED_SUMMARY brand=coldtier tables=42 access_rows=3600 policies=3 plan_items=14 users=3
```

收尾：`docker compose down -v --remove-orphans`

### 本地开发（不用 Docker）

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
python -m scripts.bootstrap_db && python -m scripts.seed_demo
uvicorn src.main:app --reload --port 8000
# frontend
cd frontend && npm install --registry=https://registry.npmmirror.com && npm run dev  # 18255，/api 代理到 19255
```

## 6. 访问地址

| 用途 | 地址 |
|---|---|
| 前端 | http://localhost:18255 |
| 后端 OpenAPI | http://localhost:19255/api/docs |
| 健康检查 | http://localhost:19255/api/health ／ http://localhost:18255/healthz |
| PostgreSQL | `localhost:17755`（库/用户 `coldtier`） |

## 7. 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3.4 + TypeScript + Vite 5 + Pinia + vue-router + axios；图表全部 SVG 自绘（树图 / 折线 / 温度计 / 条形），无联网 CDN |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + PyJWT + passlib(bcrypt) |
| 任务 | Celery 5.4 + Redis 7（beat 心跳 30s；每 6h 热度重算；`tables/heat/recompute` 接口投递） |
| 存储 | PostgreSQL 16（schema `coldtier`），命名卷 `coldtier_db_data` / `coldtier_redis_data` |
| 边缘 | Nginx 1.27（托管 dist + `/api/` 反代 backend:8000 + SPA 回落） |
| 视觉 | 仓储「货架与温区」：冷蓝灰 + 木棕，货架编号 / 温度计刻度 / 分区吊牌；双字体 `Noto Sans SC` + `JetBrains Mono`；`oklch()` 色板，禁纯黑纯白 / 紫蓝渐变 / 玻璃拟态 |

## 8. 目录

```
gb-582/
├── docker-compose.yml          # 5 服务：frontend / backend / worker / db / redis，全部 healthcheck
├── .env / .env.example
├── backend/
│   ├── Dockerfile  entrypoint.sh  requirements.txt  alembic.ini
│   ├── migrations/             # env.py + versions/0001_initial.py
│   ├── scripts/                # bootstrap_db.py / fixtures.py / seed_demo.py
│   └── src/
│       ├── config/             # settings / database / celery_app / app(create_app)
│       ├── constants/          # enums(共享枚举) / roles / error_codes / limits / log_templates
│       ├── models/             # table_profile / access_stat / tier_policy / migration_plan(+item) / audit_log / user
│       ├── schemas/            # common / auth / table / policy / plan / overview
│       ├── services/           # heat_service(算法1) / cost_service(算法2) / trial / plan / policy / table / overview / export / audit / auth
│       ├── controllers/        # health / auth / overview / table / policy / plan / audit
│       ├── routes/             # 统一 /api 前缀
│       ├── middlewares/        # auth(JWT) / rbac(403) / rate_limit(Redis) / audit_logger / error_handler
│       ├── utils/              # jwt / password / redis_client / numeric / errors / logger
│       └── main.py
├── worker/
│   ├── Dockerfile  healthcheck.sh
│   └── src/{config/{settings,celery_app},tasks/{heat_task,heartbeat_task}}
└── frontend/
    ├── Dockerfile  nginx.conf  index.html  vite.config.ts  tsconfig.json
    └── src/
        ├── api/                # http / auth / overview / tables / policies / plans
        ├── stores/             # auth / table / policy / plan
        ├── types/              # user / domain / api
        ├── components/common/  # AppShell / PageHeader / MetricTile / TierBadge / RiskBadge / EmptyState / ErrorNotice
        ├── components/domain/  # ShelfTable / TierThermometer / TreemapBoard / AccessTrendChart / CostLadder / PolicyEditor / TrialBoard / PlanWorkbench
        ├── hooks/              # useAsync / useTableFilter
        ├── pages/              # Login / Overview / TableHeat / PolicyTrial / MigrationPlan
        ├── router/  utils/  constants/  styles/
        └── main.ts  App.vue
```

## 9. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `coldtier` | 容器名前缀 |
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | `18255` / `19255` / `17755` | 宿主端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `coldtier` / `coldtier` / `coldtier_pw_2026` | PostgreSQL |
| `DB_SCHEMA` | `coldtier` | 业务表 schema |
| `JWT_SECRET` | 见 `.env.example` | JWT 签名密钥（生产必改） |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker / backend、限流、心跳 |
| `SEED_DEMO` | `true` | 首启自动 seed（幂等） |
| `RATE_LIMIT_TRIAL_PER_MINUTE` | `20` | 试算限流 |
| `RATE_LIMIT_PLAN_PER_MINUTE` | `14` | 建计划/复检/提交/导出限流 |

## 10. Docker 说明

- 恰好 5 个服务，5 个都有 `healthcheck`：`db`(pg_isready) / `redis`(redis-cli ping) / `backend`(`/api/health`) / `worker`(Redis 心跳 + celery ping 兜底) / `frontend`(wget `/`)。
- `backend`、`worker` 依赖 `db`/`redis` 的 `service_healthy`；`frontend` 依赖 `backend` healthy。
- worker 构建上下文是项目根目录：同时拷贝 `backend/`（模型与算法复用，只有一份实现）与 `worker/src`（`worker_src`）。
- 前端构建用 `node:20-alpine`，npm registry 默认 `registry.npmmirror.com`（`--build-arg NPM_REGISTRY=` 可覆盖）；pip 用清华源。
- 卷：`coldtier_db_data`、`coldtier_redis_data`（`docker compose down -v` 清理）。

## 11. 共享枚举出现位置

**`storage_tier`（hot / warm / cold）**

| 端 | 位置 |
|---|---|
| 后端 | `src/constants/enums.py`(StorageTier, TIER_LABELS) · `models/table_profile.py`(tier) · `models/tier_policy.py`(tier) · `models/migration_plan_item.py`(from_tier/suggested_tier) · `services/heat_service.py`(建议温区) · `services/cost_service.py`(price_for) · `services/trial_service.py` · `services/table_service.py` · `services/overview_service.py` · `services/export_service.py` · `services/plan_service.py` · `schemas/table.py` · `schemas/policy.py` · `schemas/plan.py` · `schemas/overview.py` · `scripts/fixtures.py` |
| 前端 | `types/domain.ts`(StorageTier) · `constants/enums.ts`(STORAGE_TIERS / TIER_LABELS / TIER_CODES / TIER_HINT) · `components/common/TierBadge.vue` · `components/domain/ShelfTable.vue` · `TierThermometer.vue` · `CostLadder.vue` · `TrialBoard.vue` · `PolicyEditor.vue` · `PlanWorkbench.vue` · `pages/OverviewPage.vue` · `TableHeatPage.vue` · `PolicyTrialPage.vue` · `LoginPage.vue` |

**`risk_level`（block / warn / ok）**

| 端 | 位置 |
|---|---|
| 后端 | `src/constants/enums.py`(RiskLevel, RISK_LABELS) · `services/cost_service.py`(assess_risk) · `services/plan_service.py` · `services/trial_service.py` · `services/export_service.py` · `models/migration_plan_item.py`(risk) · `schemas/table.py`(risk) · `schemas/policy.py`(risk) · `schemas/plan.py`(risk/risk_block_count/risk_warn_count) |
| 前端 | `types/domain.ts`(RiskLevel) · `constants/enums.ts`(RISK_LEVELS / RISK_LABELS) · `components/common/RiskBadge.vue` · `components/domain/ShelfTable.vue` · `TrialBoard.vue` · `PlanWorkbench.vue` · `pages/TableHeatPage.vue` |

**`dw_layer`（ods / dwd / dws / ads）**：`src/constants/enums.py`(DwLayer, LAYER_LABELS) · `models/table_profile.py` · `scripts/fixtures.py` · `schemas/overview.py`(LayerCell) · 前端 `types/domain.ts`(DwLayer) · `constants/enums.ts`(DW_LAYERS / LAYER_LABELS) · `hooks/useTableFilter.ts` · `components/domain/TreemapBoard.vue` · `ShelfTable.vue` · `pages/OverviewPage.vue` · `TableHeatPage.vue`

**`plan_status`（draft / submitted / approved / cancelled）**：`src/constants/enums.py`(PlanStatus, PLAN_STATUS_LABELS) · `models/migration_plan.py`(status) · `services/plan_service.py` · 前端 `types/domain.ts`(PlanStatus) · `constants/enums.ts`(PLAN_STATUS_LABELS) · `components/domain/PlanWorkbench.vue` · `pages/MigrationPlanPage.vue`

**`compression`（zstd / lz4 / snappy / none）**：`src/constants/enums.py`(Compression) · `models/table_profile.py` · `scripts/fixtures.py` · 前端 `constants/enums.ts`(COMPRESSION_LABELS) · `pages/TableHeatPage.vue` · `components/domain/ShelfTable.vue`

**角色枚举**：`backend/src/constants/roles.py`(ROLE_*/PERMISSIONS/ROLE_LABELS) ↔ `frontend/src/constants/roles.ts`(ROLES/ROLE_LABELS/ROLE_SCOPE/DEMO_ACCOUNTS)；`middlewares/rbac.py` 用它返回 403。

## 12. 演示账号

| 邮箱 | 密码 | 角色 |
|---|---|---|
| `admin@coldtier.io` | `Demo@2026` | admin 平台负责人 |
| `analyst@coldtier.io` | `Demo@2026` | analyst 数据开发 |
| `viewer@coldtier.io` | `Demo@2026` | viewer 财务与报表 owner（只读） |

## 13. License

MIT（仅用于内部评审演示；演示数据为脚本生成，不含真实客户数据）。
