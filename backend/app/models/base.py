"""Declarative base configuration shared by all ORM models."""

from __future__ import annotations

import re
from typing import ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _to_snake_case(name: str) -> str:
    """Convert a CamelCase class name to snake_case table name."""

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    metadata: ClassVar[MetaData] = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        return _to_snake_case(cls.__name__)


__all__ = ["Base", "metadata", "NAMING_CONVENTION"]
