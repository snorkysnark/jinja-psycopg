from typing import Optional, Iterable, Protocol, Union, runtime_checkable
from psycopg.sql import SQL, Composable


@runtime_checkable
class IntoSql(Protocol):
    def __sql__(self) -> Composable:
        ...


SqlLike = Union[Composable, IntoSql]


def sql_filter(value: str) -> SQL:
    """Jinja filter for including a sql string as is
    Usage: `{{ 'text' | sql }}`"""
    return SQL(value)


def _preprocess_before_join(items: Iterable[SqlLike], attribute: Optional[str] = None):
    for item in items:
        if attribute is not None:
            item = getattr(item, attribute)

        if isinstance(item, IntoSql):
            item = item.__sql__()

        yield item


def sql_join_filter(
    value: Iterable[SqlLike], delimiter: str, attribute: Optional[str] = None
):
    return SQL(delimiter).join(_preprocess_before_join(value, attribute))
