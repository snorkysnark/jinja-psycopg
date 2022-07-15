from typing import Any, Optional

from jinja2 import Environment
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension
from .context import ContextDict

CONTEXT = ContextDict("format_args")


def psycopg_filter(value: Any, key: str):
    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    # Save the value in thread-local context (if exists)
    CONTEXT.write_safe(key, value)
    return f"{{{key}}}"


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        self.env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self.env.add_extension(PsycopgExtension)
        self.env.filters["psycopg"] = psycopg_filter

    def render(self, source: str, params: dict[str, Any] = {}) -> Composed:
        recorder = CONTEXT.recorder()
        with recorder:
            template = self.env.from_string(source)
            sql = SQL(template.render(params))

        return sql.format(**recorder.unwrap())
