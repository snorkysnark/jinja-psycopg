from typing import Any, Optional
from contextvars import ContextVar

from jinja2 import Environment
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension

context = ContextVar[Optional[dict[str, Any]]]("format_args")


def psycopg_filter(value: Any, key: str):
    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    # Save the value in thread-local context (if exists)
    format_args = context.get()
    if format_args is not None:
        format_args[key] = value

    return f"{{{key}}}"


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        self.env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self.env.add_extension(PsycopgExtension)
        self.env.filters["psycopg"] = psycopg_filter

    def render(self, source: str, params: dict[str, Any]) -> Composed:
        context.set({})
        try:
            template = self.env.from_string(source)
            sql = SQL(template.render(params))
            format_args: dict[str, Any] = context.get()  # type:ignore

            return sql.format(**format_args)
        finally:
            context.set(None)
