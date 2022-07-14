from typing import Any, Optional, Union
from contextvars import ContextVar

from jinja2 import Environment, Template
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension

format_args = ContextVar("format_args")


def psycopg_filter(value: Any):
    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    # Save the value in thread-local context (if exists)
    args_list = format_args.get()
    if args_list is not None:
        args_list.append(value)

    return "{}"


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        self.env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self.env.add_extension(PsycopgExtension)
        self.env.filters["psycopg"] = psycopg_filter

    def make_template(self, source: str) -> Template:
        return self.env.from_string(source)

    def render(
        self, template: Union[str, Template], params: dict[str, Any]
    ) -> Composed:
        if isinstance(template, str):
            template = self.env.from_string(template)

        format_args.set([])
        try:
            sql = SQL(template.render(params))
            return sql.format(*format_args.get())
        finally:
            format_args.set(None)
