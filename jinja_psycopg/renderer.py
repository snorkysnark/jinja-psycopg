from __future__ import annotations
import textwrap
from typing import Any, Mapping, Optional, Union

from jinja2 import Environment, Template
from jinja2.environment import TemplateModule
from psycopg.sql import SQL, Composed

from .extension import PsycopgExtension
from .context import FormatArgsContext
from .sql import IntoSql, sql_filter, sql_join_filter

CONTEXT = FormatArgsContext("format_args")
_NO_VALUE = object()


def psycopg_filter(value: Any) -> str:
    """Jinja filter that saves the value inside a dictionary in ContextVar
        and returns a psycopg format placeholder

    Args:
        value: value piped into the filter

    Returns:
        psycopg format placeholder such as `{key}`
    """
    if isinstance(value, IntoSql):
        value = value.__sql__()

    if isinstance(value, SQL):
        # No need to pass SQL to psycopg's formatter,
        # since it's included as is
        return value.as_string(None)

    key = CONTEXT.save_value(value)
    return f"{{{key}}}"


def escape_percents(composed: Composed) -> Composed:
    """
    Replace all occurences of '%' with '%%',
    so that psycopg doesn't mistake them for placeholders.
    Actual placeholders can still be created with [psycopg.sql.Placeholder][]

    Args:
        composed: input sql

    Returns:
        output sql
    """
    new_sequence = []
    for token in composed:
        if isinstance(token, SQL):
            token = SQL(token.as_string(None).replace("%", "%%"))
        new_sequence.append(token)

    return Composed(new_sequence)


class SqlTemplate:
    def __init__(self, template: Template, static_args: dict[str, Any]) -> None:
        """Wrapper for [jinja2.Template][] that stores static format arguments
            such as `{{ 'text' }}`

        Args:
            template: inner Template
            static_args: args recurded during template creation
        """

        self._template = template
        self._static_args = static_args

    def render(self, *args, **kwargs) -> Composed:
        """
        Same as [jinja2.Template.render][], but returns a [psycopg.sql.Composed][] object
        """
        recorder = CONTEXT.recorder("dynamic")
        with recorder:
            sql = SQL(self._template.render(*args, **kwargs))
        dynamic_args = recorder.unwrap()

        composed = sql.format(**self._static_args, **dynamic_args)
        return escape_percents(composed)

    def make_module(
        self,
        vars: Optional[dict[str, Any]] = None,
        shared: bool = False,
        locals: Optional[Mapping[str, Any]] = None,
    ) -> SqlTemplateModule:
        """
        Same as [jinja2.Template.make_module][], but returns a wrapper that remembers all the format arguments

        Returns:
            module wrapper
        """
        recorder = CONTEXT.recorder("dynamic")
        with recorder:
            module = self._template.make_module(vars, shared, locals)
        dynamic_args = recorder.unwrap()

        return SqlTemplateModule(module, {**self._static_args, **dynamic_args})


class SqlTemplateModule:
    def __init__(self, module: TemplateModule, args: dict[str, Any]) -> None:
        """Wrapper over jinja2.environment.TemplateModule that stores all the format arguments
        for use in [SQL.format][psycopg.sql.SQL.format]

        Args:
            module: inner module
            args: args recorded during module creation
        """

        self._module = module
        self._args = args

    def render(self) -> Composed:
        """
        Returns:
            a formatted SQL statement
        """
        composed = SQL(str(self._module)).format(**self._args)
        return escape_percents(composed)

    @property
    def inner(self) -> TemplateModule:
        """Get inner module"""
        return self._module

    def getattr(self, name: str, default: Any = _NO_VALUE) -> Any:
        """Get attribute of the inner module"""
        if default is _NO_VALUE:
            return getattr(self._module, name)
        else:
            return getattr(self._module, name, default)


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        """Wrapper over [jinja2.Environment][] that generates `SqlTemplate`s

        Args:
            env: base jinja environment
        """
        self._env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        """Override this to inject your own globals and filters"""

        self._env.add_extension(PsycopgExtension)
        self._env.filters["psycopg"] = psycopg_filter
        self._env.filters["sql"] = sql_filter
        self._env.filters["sqljoin"] = sql_join_filter

    def from_string(
        self, source: str, dedent: bool = True, strip: bool = True
    ) -> SqlTemplate:
        """
        Args:
            source: template string
            dedent: remove indentation from source
            strip: remove leading and trailing spaces

        Returns:
            parsed template
        """

        # Jinja2 processes its blocks in two iterations:
        # static values like {{ 'text' }} are processed during from_string,
        # and dynamic ones during Template.render or make_module
        if dedent:
            source = textwrap.dedent(source)
        if strip:
            source = source.strip()

        recorder = CONTEXT.recorder("static")
        with recorder:
            template = self._env.from_string(source)

        return SqlTemplate(template, recorder.unwrap())

    def render(
        self,
        template: Union[str, SqlTemplate],
        params: dict[str, Any] = {},
        dedent: bool = True,
        strip: bool = True,
    ) -> Composed:
        """Shorthand for rendering a template or template string

        Args:
            template: template or template string
            params: template arguments
            dedent: remove indentation from template string
            strip: remove leading and trailing spaces

        Returns:
            rendered SQL
        """

        if isinstance(template, str):
            template = self.from_string(template, dedent=dedent, strip=strip)

        return template.render(params)
