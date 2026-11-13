"""execution & reconciliation：migration_batches / migration_receipts / actual_bills + 计划项结算列

Revision ID: 0002_execution_recon
Revises: 0001_initial
Create Date: 2026-11-13

说明：demo 环境由 `scripts/bootstrap_db.py` 的 `create_all` 建表（已含本批新表）；
本迁移面向正式环境，全部 DDL 幂等（IF NOT EXISTS），与 bootstrap 共存不冲突。
"""
from __future__ import annotations

from alembic import op

from src.config.settings import settings

revision = "0002_execution_recon"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

SCHEMA = settings.db_schema

STATEMENTS = [
    # 计划项结算列（回执 / 账单对账后回写）
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" ADD COLUMN IF NOT EXISTS "actual_save_month" NUMERIC(12, 2)',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" ADD COLUMN IF NOT EXISTS "actual_migrate_cost" NUMERIC(12, 2)',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" ADD COLUMN IF NOT EXISTS "last_receipt_no" VARCHAR(64) NOT NULL DEFAULT \'\'',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" ADD COLUMN IF NOT EXISTS "settled_at" TIMESTAMPTZ',
    # 执行批次（batch_no 幂等：整批重跑不重复计费）
    f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA}"."migration_batches" (
        "id" UUID NOT NULL,
        "plan_id" UUID NOT NULL REFERENCES "{SCHEMA}"."migration_plans"("id") ON DELETE CASCADE,
        "batch_no" VARCHAR(48) NOT NULL,
        "note" TEXT NOT NULL DEFAULT '',
        "created_by" VARCHAR(120) NOT NULL DEFAULT '',
        "created_at" TIMESTAMPTZ NOT NULL,
        "updated_at" TIMESTAMPTZ NOT NULL,
        CONSTRAINT "pk_migration_batches" PRIMARY KEY ("id"),
        CONSTRAINT "uq_migration_batches_batch_no" UNIQUE ("batch_no")
    )
    """,
    f'CREATE INDEX IF NOT EXISTS "ix_migration_batches_plan_id" ON "{SCHEMA}"."migration_batches" ("plan_id")',
    f'CREATE INDEX IF NOT EXISTS "ix_migration_batches_batch_no" ON "{SCHEMA}"."migration_batches" ("batch_no")',
    # 逐表回执（receipt_no 幂等：同一回执重试不重复计费）
    f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA}"."migration_receipts" (
        "id" UUID NOT NULL,
        "plan_id" UUID NOT NULL REFERENCES "{SCHEMA}"."migration_plans"("id") ON DELETE CASCADE,
        "item_id" UUID NOT NULL REFERENCES "{SCHEMA}"."migration_plan_items"("id") ON DELETE CASCADE,
        "batch_id" UUID REFERENCES "{SCHEMA}"."migration_batches"("id") ON DELETE SET NULL,
        "receipt_no" VARCHAR(64) NOT NULL,
        "result" VARCHAR(10) NOT NULL DEFAULT 'success',
        "applied" BOOLEAN NOT NULL DEFAULT TRUE,
        "actual_size_gb" NUMERIC(12, 2),
        "actual_migrate_cost" NUMERIC(12, 2),
        "message" TEXT NOT NULL DEFAULT '',
        "received_at" TIMESTAMPTZ,
        "created_at" TIMESTAMPTZ NOT NULL,
        "updated_at" TIMESTAMPTZ NOT NULL,
        CONSTRAINT "pk_migration_receipts" PRIMARY KEY ("id"),
        CONSTRAINT "uq_migration_receipts_receipt_no" UNIQUE ("receipt_no")
    )
    """,
    f'CREATE INDEX IF NOT EXISTS "ix_migration_receipts_plan_id" ON "{SCHEMA}"."migration_receipts" ("plan_id")',
    f'CREATE INDEX IF NOT EXISTS "ix_migration_receipts_item_id" ON "{SCHEMA}"."migration_receipts" ("item_id")',
    f'CREATE INDEX IF NOT EXISTS "ix_migration_receipts_receipt_no" ON "{SCHEMA}"."migration_receipts" ("receipt_no")',
    # 实际账单（bill_no 幂等；每表至多一张生效账单）
    f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA}"."actual_bills" (
        "id" UUID NOT NULL,
        "plan_id" UUID NOT NULL REFERENCES "{SCHEMA}"."migration_plans"("id") ON DELETE CASCADE,
        "item_id" UUID NOT NULL REFERENCES "{SCHEMA}"."migration_plan_items"("id") ON DELETE CASCADE,
        "bill_no" VARCHAR(64) NOT NULL,
        "bill_month" VARCHAR(7) NOT NULL DEFAULT '',
        "actual_save_month" NUMERIC(12, 2) NOT NULL DEFAULT 0,
        "note" TEXT NOT NULL DEFAULT '',
        "created_at" TIMESTAMPTZ NOT NULL,
        "updated_at" TIMESTAMPTZ NOT NULL,
        CONSTRAINT "pk_actual_bills" PRIMARY KEY ("id"),
        CONSTRAINT "uq_actual_bills_bill_no" UNIQUE ("bill_no"),
        CONSTRAINT "uq_actual_bills_item" UNIQUE ("item_id")
    )
    """,
    f'CREATE INDEX IF NOT EXISTS "ix_actual_bills_plan_id" ON "{SCHEMA}"."actual_bills" ("plan_id")',
    f'CREATE INDEX IF NOT EXISTS "ix_actual_bills_item_id" ON "{SCHEMA}"."actual_bills" ("item_id")',
    f'CREATE INDEX IF NOT EXISTS "ix_actual_bills_bill_no" ON "{SCHEMA}"."actual_bills" ("bill_no")',
]

DROPS = [
    f'DROP TABLE IF EXISTS "{SCHEMA}"."actual_bills" CASCADE',
    f'DROP TABLE IF EXISTS "{SCHEMA}"."migration_receipts" CASCADE',
    f'DROP TABLE IF EXISTS "{SCHEMA}"."migration_batches" CASCADE',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" DROP COLUMN IF EXISTS "actual_save_month"',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" DROP COLUMN IF EXISTS "actual_migrate_cost"',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" DROP COLUMN IF EXISTS "last_receipt_no"',
    f'ALTER TABLE "{SCHEMA}"."migration_plan_items" DROP COLUMN IF EXISTS "settled_at"',
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DROPS:
        op.execute(statement)
