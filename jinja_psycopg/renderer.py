from typing import Any, Mapping, Optional, Union

from jinja2 import Environment, Template
from jinja2.environment import TemplateModule
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension
from .context import FormatArgsContext
from .sql import IntoSql, sql_filter, sql_join_filter

CONTEXT = FormatArgsContext("format_args")


def psycopg_filter(value: Any):
    """Jinja filter that saves the value inside a dictionary in ContextVar
    and returns a psycopg format placeholder such as `{key}`"""
    if isinstance(value, IntoSql):
        value = value.__sql__()

    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    key = CONTEXT.save_value(value)
    return f"{{{key}}}"


class SqlTemplate:
    """Wrapper for jinja2.Template that stores static format arguments
    such as `{{ 'text' }}`"""

    def __init__(self, template: Template, static_args: dict[str, Any]) -> None:
        self._template = template
        self._static_args = static_args

    def render(self, *args, **kwargs) -> Composed:
        """Same as jinja2.Template.render, but returns a psycopg.sql.Composed object"""
        recorder = CONTEXT.recorder("dynamic")
        with recorder:
            sql = SQL(self._template.render(*args, **kwargs))
        dynamic_args = recorder.unwrap()

        return sql.format(**self._static_args, **dynamic_args)

    def make_module(
        self,
        vars: Optional[dict[str, Any]] = None,
        shared: bool = False,
        locals: Optional[Mapping[str, Any]] = None,
    ):
        """Same as jinja2.Template.make_module, but returns a wrapper that remembers all the format arguments"""
        recorder = CONTEXT.recorder("dynamic")
        with recorder:
            module = self._template.make_module(vars, shared, locals)
        dynamic_args = recorder.unwrap()

        return SqlTemplateModule(module, {**self._static_args, **dynamic_args})


class SqlTemplateModule:
    """Wrapper over jinja2.environment.TemplateModule that stores all the format arguments
    for use in SQL.format"""

    def __init__(self, module: TemplateModule, args: dict[str, Any]) -> None:
        self._module = module
        self._args = args

    def render(self):
        """Returns a formatted SQL statement"""
        return SQL(str(self._module)).format(**self._args)

    @property
    def module(self):
        return self._module


class JinjaPsycopg:
    """Wrapper over jinja2.Environment that generates `SqlTemplate`s"""

    def __init__(self, env: Optional[Environment] = None) -> None:
        self._env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self._env.add_extension(PsycopgExtension)
        self._env.filters["psycopg"] = psycopg_filter
        self._env.filters["sql"] = sql_filter
        self._env.filters["sqljoin"] = sql_join_filter

    def from_string(self, source: str) -> SqlTemplate:
        # Jinja2 processes its blocks in two iterations:
        # static values like {{ 'text' }} are processed during from_string,
        # and dynamic ones during Template.render or make_module
        recorder = CONTEXT.recorder("static")
        with recorder:
            template = self._env.from_string(source)

        return SqlTemplate(template, recorder.unwrap())

    def render(
        self, template: Union[str, SqlTemplate], params: dict[str, Any] = {}
    ) -> Composed:
        if isinstance(template, str):
            template = self.from_string(template)

        return template.render(params)
