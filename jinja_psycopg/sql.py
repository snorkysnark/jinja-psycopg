from typing import Protocol, runtime_checkable
from psycopg.sql import SQL, Composable


def sql_filter(value: str) -> SQL:
    """Jinja filter for including a sql string as is
    Usage: `{{ 'text' | sql }}`"""
    return SQL(value)


@runtime_checkable
class IntoSql(Protocol):
    def __sql__(self) -> Composable:
        ...
