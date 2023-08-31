from typing import Optional, Iterable, Protocol, Union, runtime_checkable
from psycopg.sql import SQL, Composable


@runtime_checkable
class IntoSql(Protocol):
    """Type that has a SQL representation"""

    def __sql__(self) -> Composable:
        """
        Returns:
            SQL representation
        """
        ...


SqlLike = Union[Composable, IntoSql]
"""
SQL or a type convertible to SQL
"""


def sql_filter(value: str) -> SQL:
    """Jinja filter for converting a string to raw SQL

    Usage: `{{ 'text' | sql }}`
    """
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
    """
    Similar to jinja's [join](https://jinja.palletsprojects.com/en/3.0.x/templates/#jinja-filters.join)
        filter, but for SQL

    Args:
        value: sequence to join
        delimiter: join delimiter
        attribute: extract objects' attribute,

            like `{{ users|join(', ', attribute='username') }}`
    """
    return SQL(delimiter).join(_preprocess_before_join(value, attribute))
