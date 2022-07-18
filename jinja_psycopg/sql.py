from psycopg.sql import SQL


def sql_filter(value: str) -> SQL:
    """Jinja filter for including a sql string as is
    Usage: `{{ 'text' | sql }}`"""
    return SQL(value)
