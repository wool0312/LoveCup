"""数据库基础设施：引擎、会话、Base，以及精确小数类型。"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, String, TypeDecorator, create_engine
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
