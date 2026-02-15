"""Super migration (compact): make mission_events.event_type TEXT + composite index + optional length check.

Revision ID: 20250902_evt_type_idx
Revises: 0b5107e8283d
Create Date: 2025-09-02 18:10:00
"""

from __future__ import annotations

from contextlib import suppress

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# معرفات Alembic
# ---------------------------------------------------------------------------
revision = "20250902_evt_type_idx"
down_revision = "0b5107e8283d"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# إعدادات قابلة للضبط
# ---------------------------------------------------------------------------
ADD_LENGTH_CHECK = True  # اجعلها False لتعطيل إنشاء CHECK
LENGTH_LIMIT = 128  # الحد الأقصى لطول event_type (تحكم منطقي فقط، وليس مطلوباً إذا أردت حرية كاملة)
CHECK_NAME = "ck_mission_events_event_type_len"
COMPOSITE_INDEX_NAME = "ix_mission_events_mission_created_type"
LEGACY_SINGLE_INDEX = "ix_mission_events_event_type"


# ---------------------------------------------------------------------------
# أدوات داخلية
# ---------------------------------------------------------------------------
def _bind():
    return op.get_bind()


def _dialect():
    return _bind().dialect.name.lower()


def _is_postgres():
    return _dialect() == "postgresql"


def _is_sqlite():
    return _dialect() == "sqlite"


def _column_is_text():
    insp = sa.inspect(_bind())
    for col in insp.get_columns("mission_events"):
        if col["name"] == "event_type":
            # مثال: TEXT / VARCHAR / STRING …
            ctype = col["type"].__class__.__name__.lower()
            if "text" in ctype:
                return True
    return False


def _print_stats(stage: str):
    with suppress(Exception):
        res = (
            _bind()
            .execute(
                sa.text(
                    "SELECT MAX(char_length(event_type)) AS max_len, COUNT(*) AS total_rows FROM mission_events"
                )
            )
            .first()
        )
        if res:
            print(
                f"[event_type migration] {stage}: max_len={res.max_len}, total_rows={res.total_rows}"
            )


def _index_exists(index_name: str) -> bool:
    # PostgreSQL فقط - لبساطة (يمكن توسيعها لاحقاً لغيره)
    if not _is_postgres():
        return False
    with suppress(Exception):
        q = sa.text("SELECT 1 FROM pg_class WHERE relkind='i' AND relname=:idx LIMIT 1")
        row = _bind().execute(q.bindparams(idx=index_name)).first()
        return bool(row)
    return False


def _check_constraint_exists(name: str) -> bool:
    if not _is_postgres():
        return False
    with suppress(Exception):
        q = sa.text(
            """
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname='mission_events'
              AND c.contype='c'
              AND c.conname=:name
            LIMIT 1
        """
        )
        row = _bind().execute(q.bindparams(name=name)).first()
        return bool(row)
    return False


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------
def upgrade():
    print("[event_type migration] START upgrade")
    print(f"[event_type migration] Dialect = {_dialect()}")
    _print_stats("before")

    # 1) تحويل العمود إلى TEXT إن لم يكن بالفعل TEXT
    if not _column_is_text():
        if _is_sqlite():
            # SQLite يحتاج batch_alter_table لتغيير النوع بدون تعقيدات
            with op.batch_alter_table("mission_events") as batch_op:
                batch_op.alter_column(
                    "event_type",
                    type_=sa.Text(),
                    existing_type=sa.String(length=17),
                    existing_nullable=False,
                )
        else:
            op.alter_column(
                "mission_events",
                "event_type",
                type_=sa.Text(),
                existing_type=sa.String(length=17),
                existing_nullable=False,
            )
        print("[event_type migration] Column 'event_type' altered to TEXT.")
    else:
        print("[event_type migration] NOTE: 'event_type' already TEXT -> skipping alter.")

    # 2) إضافة CHECK (اختياري) في PostgreSQL فقط
    if ADD_LENGTH_CHECK and _is_postgres():
        if _check_constraint_exists(CHECK_NAME):
            print(f"[event_type migration] CHECK {CHECK_NAME} already exists -> skip.")
        else:
            op.execute(
                sa.text(
                    f"ALTER TABLE mission_events "
                    f"ADD CONSTRAINT {CHECK_NAME} CHECK (char_length(event_type) <= :limit)"
                ).bindparams(limit=LENGTH_LIMIT)
            )
            print(f"[event_type migration] Added CHECK {CHECK_NAME} (<= {LENGTH_LIMIT}).")
    elif ADD_LENGTH_CHECK:
        print("[event_type migration] Length CHECK skipped (non-PostgreSQL dialect).")

    # 3) إسقاط الفهرس القديم (إن وجد)
    with suppress(Exception):
        op.drop_index(LEGACY_SINGLE_INDEX, table_name="mission_events")
        print(f"[event_type migration] Dropped legacy index {LEGACY_SINGLE_INDEX} (if existed).")

    # 4) إنشاء فهرس مركب (mission_id, created_at, event_type)
    # نتجنب التكرار في PostgreSQL عبر فحص وجوده (اختياري).
    create_index = True
    if _is_postgres() and _index_exists(COMPOSITE_INDEX_NAME):
        create_index = False
        print(
            f"[event_type migration] Composite index {COMPOSITE_INDEX_NAME} already exists -> skip."
        )
    if create_index:
        with suppress(Exception):
            op.create_index(
                COMPOSITE_INDEX_NAME,
                "mission_events",
                ["mission_id", "created_at", "event_type"],
                unique=False,
            )
            print(f"[event_type migration] Created composite index {COMPOSITE_INDEX_NAME}.")

    _print_stats("after")
    print("[event_type migration] DONE upgrade")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------
def downgrade():
    print("[event_type migration] START downgrade")
    print(f"[event_type migration] Dialect = {_dialect()}")

    # 1) حذف الفهرس المركب
    with suppress(Exception):
        op.drop_index(COMPOSITE_INDEX_NAME, table_name="mission_events")
        print(f"[event_type migration] Dropped composite index {COMPOSITE_INDEX_NAME}.")

    # 2) حذف CHECK (إن وُجد وكان PostgreSQL)
    if ADD_LENGTH_CHECK and _is_postgres():
        if _check_constraint_exists(CHECK_NAME):
            with suppress(Exception):
                op.execute(sa.text(f"ALTER TABLE mission_events DROP CONSTRAINT {CHECK_NAME}"))
                print(f"[event_type migration] Dropped CHECK constraint {CHECK_NAME}.")

    # 3) إعادة الفهرس القديم الأحادي (اختياري – نفعلها تماشياً مع ما كان)
    with suppress(Exception):
        op.create_index(LEGACY_SINGLE_INDEX, "mission_events", ["event_type"], unique=False)
        print(f"[event_type migration] Re-created legacy index {LEGACY_SINGLE_INDEX}.")

    # 4) إعادة العمود إلى VARCHAR(64) (أو الطول السابق، عدّله إذا احتجت)
    if _is_sqlite():
        with op.batch_alter_table("mission_events") as batch_op:
            batch_op.alter_column(
                "event_type",
                type_=sa.String(length=64),
                existing_type=sa.Text(),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "mission_events",
            "event_type",
            type_=sa.String(length=64),
            existing_type=sa.Text(),
            existing_nullable=False,
        )
    print("[event_type migration] Downgraded 'event_type' back to VARCHAR(64).")
    print("[event_type migration] DONE downgrade")
