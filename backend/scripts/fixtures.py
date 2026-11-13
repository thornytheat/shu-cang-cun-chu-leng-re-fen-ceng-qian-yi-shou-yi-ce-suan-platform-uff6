"""演示数据定义（种子）：青禾零售数仓 42 张表 + 3 档策略 + 3 个账号 + 1 份 14 项草稿计划。

规模校验（seed 会断言后打印）：
  表 12 热区 + 18 温区 + 12 冷区 = 42；体积 13,680 + 25,620 + 3,708 = 43,008 GB = 42.0 TB
  访问统计 39 张表 × 90 天 + 2 张 × 40 天 + 1 张 × 10 天 = 3,600 行
  试算（阈值 20）命中热区 12 张，月省 ¥6,840 / 年省 ¥82,080
  勾选前 8 张 → 风险复检 2 阻断 + 1 需确认 → 移除 2 张后 6 张：净年省 ¥51,300，平均回收期 1.8 月
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEMO_PASSWORD = "Demo@2026"
BRAND = "coldtier"
DOMAIN = "coldtier.io"

DEMO_USERS: list[dict] = [
    {
        "email": "admin@coldtier.io",
        "display_name": "陈可欣",
        "role": "admin",
        "team": "数据平台组 · 负责人",
    },
    {
        "email": "analyst@coldtier.io",
        "display_name": "林哲",
        "role": "analyst",
        "team": "数据平台组 · 数仓开发",
    },
    {
        "email": "viewer@coldtier.io",
        "display_name": "赵敏",
        "role": "viewer",
        "team": "财务共享中心 · 报表 owner",
    },
]

# 三档策略（同一 version 构成一组；编辑时整组升版）
POLICY_VERSION = 3
POLICY_TIERS: list[dict] = [
    {
        "code": "POL-HOT",
        "tier": "hot",
        "title": "热区：在线高带宽存储",
        "score_min": 60,
        "unit_price": 1.05,
        "target_region": "hot-pool-a",
    },
    {
        "code": "POL-WARM",
        "tier": "warm",
        "title": "温区：低频标准存储",
        "score_min": 20,
        "unit_price": 0.85,
        "target_region": "warm-pool-b",
    },
    {
        "code": "POL-COLD",
        "tier": "cold",
        "title": "冷区：对象存储归档",
        "score_min": 0,
        "unit_price": 0.55,
        "target_region": "cold-oss-archive",
    },
]

POLICY_COLD_RULES = {
    "quiet_days": 30,
    "block_recent_days": 7,
    "min_partition": 3,
    "migrate_price": 0.75,
    "migrate_fixed": 270,
}

OWNERS = ["林哲", "周雨桐", "王皓", "何一帆", "郑舒", "刘星辰", "吴倩", "陈可欣", "赵敏"]


@dataclass
class TableSpec:
    full_name: str
    layer: str
    tier: str
    size_gb: float
    partition_count: int
    compression: str
    owner: str
    report_refs: int = 0
    report_names: list[str] = field(default_factory=list)
    access_base: int = 0
    access_days: int = 90
    spikes: list[tuple[int, int]] = field(default_factory=list)
    last_write_days: int = 1
    note: str = ""
    # 近端静默：offset < quiet_after 的日期访问恒为 0（降冷候选要求近 30 天零访问）
    quiet_after: int = 0

    @property
    def region(self) -> str:
        return {
            "hot": "hot-pool-a",
            "warm": "warm-pool-b",
            "cold": "cold-oss-archive",
        }[self.tier]


# 列顺序：full_name, layer, tier, size_gb, partition_count, compression, owner,
#         report_refs, report_names, access_base, access_days, spikes, last_write_days, note
# 关键字：quiet=30 表示"近 30 天零访问"（降冷候选的前置条件），在 TableSpec 里是 quiet_after 字段。
RAW_TABLES: list[TableSpec] = [
    # ---------------- 热区 12 张（季度巡检里"热度已经掉到 20 以下"的一批） ----------------
    TableSpec("dwd.trade_order_detail", "dwd", "hot", 4800, 36, "zstd", "林哲", 0, [], 68, 90, [], 52,
              "交易明细主表，按 dt 分区；近两月无查询", quiet_after=30),
    TableSpec("ods.click_stream", "ods", "hot", 1680, 24, "zstd", "周雨桐", 0, [], 55, 90, [], 44,
              "埋点点击流原样落地", quiet_after=30),
    TableSpec("dwd.inventory_move_detail", "dwd", "hot", 1260, 18, "lz4", "王皓", 0, [], 42, 90, [], 61,
              "库存移动明细，含调拨", quiet_after=30),
    TableSpec(
        "ads.monthly_finance_report_base",
        "ads",
        "hot",
        1200,
        12,
        "zstd",
        "赵敏",
        0,
        [],
        12,
        90,
        [(3, 9), (5, 6)],
        2,
        "月报底表，去年误迁过一次已回迁；月初跑数仍会访问",
    ),
    TableSpec("ods.order_item", "ods", "hot", 960, 30, "zstd", "周雨桐", 0, [], 34, 90, [], 47,
              "订单行原样落地", quiet_after=30),
    TableSpec("dws.store_daily_gmv", "dws", "hot", 900, 24, "zstd", "何一帆", 0, [], 18, 90, [(2, 7), (6, 5)], 1,
              "门店日销汇总；督导偶尔直接查"),
    TableSpec(
        "dwd.coupon_use_detail",
        "dwd",
        "hot",
        840,
        12,
        "lz4",
        "郑舒",
        2,
        ["促销效果周报", "渠道费用月报"],
        8,
        90,
        [],
        38,
        "优惠券核销明细，报表直接取数；近两月无交互查询",
        quiet_after=30,
    ),
    TableSpec("ods.payment_flow", "ods", "hot", 540, 6, "zstd", "刘星辰", 0, [], 26, 90, [], 41,
              "支付流水原样落地", quiet_after=30),
    TableSpec("ods.logistics_bill", "ods", "hot", 480, 36, "zstd", "吴倩", 0, [], 0, 90, [], 66,
              "物流账单原始件，季度对账才用", quiet_after=30),
    TableSpec("ods.crm_touch", "ods", "hot", 420, 6, "none", "吴倩", 0, [], 0, 90, [], 58,
              "CRM 触达记录，未压缩", quiet_after=30),
    TableSpec("dwd.sku_price_change", "dwd", "hot", 360, 12, "lz4", "郑舒", 0, [], 0, 90, [], 63,
              "价格变更流水", quiet_after=30),
    TableSpec("ads.bi_dashboard_cache", "ads", "hot", 240, 1, "none", "陈可欣", 0, [], 0, 90, [], 72,
              "看板缓存表，单分区，看板已下线", quiet_after=30),
    # ---------------- 温区 18 张 ----------------
    TableSpec("dwd.member_order_fact", "dwd", "warm", 4800, 36, "zstd", "林哲", 3,
              ["会员月报", "门店看板", "增长周会"], 420, 90, [], 0, "会员订单事实，全组最热"),
    TableSpec("dws.member_rfm_daily", "dws", "warm", 3600, 30, "zstd", "何一帆", 4,
              ["会员月报", "门店看板", "LTV 测算", "运营日报"], 372, 90, [], 0, "RFM 日汇总"),
    TableSpec("dws.store_sales_summary", "dws", "warm", 2880, 30, "zstd", "何一帆", 5,
              ["门店看板", "经营日报", "区域周报", "督导日报", "财务月报"], 330, 90, [], 0, "门店销售汇总"),
    TableSpec("dwd.trade_refund_detail", "dwd", "warm", 2400, 24, "zstd", "王皓", 1, ["售后周报"], 296, 90, [], 0, ""),
    TableSpec("dws.category_perf_daily", "dws", "warm", 1920, 24, "zstd", "郑舒", 3,
              ["品类周报", "选品会", "财务月报"], 262, 90, [], 1, ""),
    TableSpec("dws.channel_cost_daily", "dws", "warm", 1680, 12, "zstd", "吴倩", 2, ["投放日报", "财务月报"], 228, 90, [], 1, ""),
    TableSpec("dwd.member_consume_fact", "dwd", "warm", 1440, 18, "zstd", "林哲", 1, ["会员月报"], 204, 90, [], 0, ""),
    TableSpec("dws.promo_effect_weekly", "dws", "warm", 1200, 12, "zstd", "郑舒", 2, ["促销效果周报", "经营周会"], 180, 40, [], 2,
              "本季度新建"),
    TableSpec("dwd.order_delivery_fact", "dwd", "warm", 1080, 18, "lz4", "王皓", 0, [], 160, 90, [], 0, ""),
    TableSpec("dws.inventory_turnover_monthly", "dws", "warm", 960, 6, "zstd", "王皓", 1, ["库存月报"], 144, 90, [], 2, ""),
    TableSpec("ads.store_ranking_weekly", "ads", "warm", 840, 6, "zstd", "陈可欣", 2, ["门店排行", "督导周报"], 128, 90, [], 1, ""),
    TableSpec("dws.supplier_scorecard_monthly", "dws", "warm", 720, 6, "zstd", "吴倩", 1, ["供应商月报"], 116, 90, [], 3, ""),
    TableSpec("ads.marketing_roi_monthly", "ads", "warm", 600, 6, "zstd", "吴倩", 2, ["投放复盘", "财务月报"], 108, 40, [], 1,
              "本季度新建"),
    TableSpec("ads.member_growth_dashboard", "ads", "warm", 480, 3, "none", "何一帆", 0, [], 100, 90, [], 0, ""),
    TableSpec("dwd.campaign_exposure_detail", "dwd", "warm", 360, 12, "lz4", "郑舒", 0, [], 96, 90, [], 0, ""),
    TableSpec("ods.sku_master", "ods", "warm", 300, 1, "zstd", "刘星辰", 2, ["选品会", "商品中心"], 92, 90, [], 0,
              "维表，单分区全量刷新"),
    TableSpec("ods.member_profile", "ods", "warm", 240, 1, "zstd", "刘星辰", 1, ["会员月报"], 88, 90, [], 0, "维表"),
    TableSpec("ads.realtime_gmv_cache", "ads", "warm", 120, 3, "none", "陈可欣", 0, [], 280, 10, [], 0,
              "上周新建的实时看板缓存"),
    # ---------------- 冷区 12 张（上一轮已归档） ----------------
    TableSpec("ods.order_main_2024", "ods", "cold", 900, 12, "zstd", "周雨桐", 0, [], 0, 90, [], 260, "2024 归档"),
    TableSpec("dwd.trade_order_detail_2024", "dwd", "cold", 660, 12, "zstd", "林哲", 0, [], 0, 90, [], 260, "2024 归档"),
    TableSpec("ods.pos_txn_2024", "ods", "cold", 540, 12, "zstd", "周雨桐", 0, [], 0, 90, [], 270, "2024 归档"),
    TableSpec("dwd.refund_record_2024", "dwd", "cold", 420, 6, "lz4", "王皓", 0, [], 0, 90, [], 275, "2024 归档"),
    TableSpec("ods.inventory_snapshot_2024", "ods", "cold", 360, 12, "zstd", "王皓", 0, [], 0, 90, [], 280, "2024 归档"),
    TableSpec("dws.monthly_finance_2024", "dws", "cold", 300, 6, "zstd", "赵敏", 0, [], 0, 90, [], 300, "2024 归档"),
    TableSpec("ods.promo_coupon_2024", "ods", "cold", 240, 6, "lz4", "郑舒", 0, [], 0, 90, [], 310, "2024 归档"),
    TableSpec("dwd.sku_price_change_2024", "dwd", "cold", 120, 6, "lz4", "郑舒", 0, [], 0, 90, [], 320, "2024 归档"),
    TableSpec("ads.q3_review_pack", "ads", "cold", 80, 1, "zstd", "陈可欣", 0, [], 0, 90, [], 60, "季度复盘包，单文件"),
    TableSpec("ods.crm_touch_2024", "ods", "cold", 48, 3, "none", "吴倩", 0, [], 0, 90, [], 330, "2024 归档"),
    TableSpec("dws.supplier_settlement_2024", "dws", "cold", 24, 1, "zstd", "吴倩", 0, [], 0, 90, [], 340, "2024 归档"),
    TableSpec("ods.click_stream_2024_sample", "ods", "cold", 16, 1, "none", "周雨桐", 0, [], 0, 90, [], 350, "抽样留档"),
]

TABLES: list[TableSpec] = RAW_TABLES

# 种子计划：14 项 = 12 张降冷候选 + 2 张人工加塞的温区表
SEED_PLAN_CODE = "MP-2026Q4-001"
SEED_PLAN_TITLE = "2026-Q4 冷存降本计划（草稿）"
SEED_PLAN_EXTRA_TABLES = ["ads.store_ranking_weekly", "ads.member_growth_dashboard"]
SEED_PLAN_NOTE = "季度巡检基线：12 张热区表 + 2 张人工加塞，待复检后提交"

# 主流程验收脚本使用的 8 张表（试算结果按预估月省倒序，前 8 行即这 8 张）
PRIMARY_FLOW_SELECTION = [
    "dwd.trade_order_detail",
    "ods.click_stream",
    "dwd.inventory_move_detail",
    "ads.monthly_finance_report_base",
    "ods.order_item",
    "dws.store_daily_gmv",
    "dwd.coupon_use_detail",
    "ods.payment_flow",
]

EXPECTED_TIER_COUNT = {"hot": 12, "warm": 18, "cold": 12}
