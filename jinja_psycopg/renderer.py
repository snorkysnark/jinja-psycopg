from dataclasses import dataclass
from typing import Any, Optional, Union

from jinja2 import Environment, Template
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension
from .context import FormatArgsContext

CONTEXT = FormatArgsContext("format_args")


def psycopg_filter(value: Any):
    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    # Save the value in thread-local context (if exists)
    key = CONTEXT.save_value(value)
    return f"{{{key}}}"


@dataclass
class SqlTemplate:
    template: Template
    static_args: dict[str, Any]

    def render(self, *args, **kwargs) -> Composed:
        recorder = CONTEXT.recorder("dynamic")
        with recorder:
            sql = SQL(self.template.render(*args, **kwargs))
        dynamic_args = recorder.unwrap()

        return sql.format(**self.static_args, **dynamic_args)


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        self.env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self.env.add_extension(PsycopgExtension)
        self.env.filters["psycopg"] = psycopg_filter

    def from_string(self, source: str) -> SqlTemplate:
        recorder = CONTEXT.recorder("static")
        with recorder:
            template = self.env.from_string(source)

        return SqlTemplate(template, recorder.unwrap())

    def render(
        self, template: Union[str, SqlTemplate], params: dict[str, Any] = {}
    ) -> Composed:
        if isinstance(template, str):
            template = self.from_string(template)

        return template.render(params)
