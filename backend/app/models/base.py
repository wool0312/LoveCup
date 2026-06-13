"""数据库基础设施：引擎、会话、Base，以及精确小数类型。"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, String, TypeDecorator, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class DecimalText(TypeDecorator):
    """SQLite 用 TEXT 存 Decimal（避免浮点精度损失），PostgreSQL 用原生 Numeric。"""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Numeric(precision=20, scale=4))
        return dialect.type_descriptor(String())

    def process_bind_param(self, value: Optional[Decimal], dialect) -> Optional[str]:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(Decimal(value))

    def process_result_value(self, value, dialect) -> Optional[Decimal]:
        if value is None:
            return None
        return Decimal(str(value))


DATABASE_URL = os.getenv("LOVECUP_DATABASE_URL", "sqlite:///./lovecup.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """建表（dev 用；将来生产可换 Alembic 迁移）。"""
    from . import entities  # noqa: F401  确保模型已注册到 Base.metadata

    Base.metadata.create_all(bind=engine)
    _ensure_lightweight_migrations()


def _ensure_lightweight_migrations() -> None:
    """给已部署的 SQLite/PostgreSQL 老库补新增列。

    这个项目目前还没引入 Alembic；这些列都是 nullable，直接补列足够安全。
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "games" in tables:
        _add_column_if_missing("games", "admin_pin_hash", "VARCHAR")
    if "predictions" in tables:
        _add_column_if_missing("predictions", "bound_home_odds", _decimal_column_type())
        _add_column_if_missing("predictions", "bound_draw_odds", _decimal_column_type())
        _add_column_if_missing("predictions", "bound_away_odds", _decimal_column_type())
        _add_column_if_missing("predictions", "bound_odds_source", "VARCHAR")


def _decimal_column_type() -> str:
    return "NUMERIC(20, 4)" if engine.dialect.name == "postgresql" else "VARCHAR"


def _add_column_if_missing(table: str, column: str, column_type: str) -> None:
    existing = {c["name"] for c in inspect(engine).get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {column_type}'))
