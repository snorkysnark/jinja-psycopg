from typing import Any, Optional

from jinja2 import Environment
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension
from .context import ContextWriter

CONTEXT = ContextWriter("format_args")


def psycopg_filter(value: Any):
    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    # Save the value in thread-local context (if exists)
    key = CONTEXT.save_value(value)
    return f"{{{key}}}"


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        self.env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self.env.add_extension(PsycopgExtension)
        self.env.filters["psycopg"] = psycopg_filter

    def render(self, source: str, params: dict[str, Any] = {}) -> Composed:
        static_recorder = CONTEXT.recorder("static")
        with static_recorder:
            template = self.env.from_string(source)
        static_args = static_recorder.unwrap()

        dynamic_recorder = CONTEXT.recorder("dynamic")
        with dynamic_recorder:
            sql = SQL(template.render(params))
        dynamic_args = dynamic_recorder.unwrap()

        return sql.format(**static_args, **dynamic_args)
