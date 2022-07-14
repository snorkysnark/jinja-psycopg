from typing import Any, Iterable, Optional
from contextvars import ContextVar

from jinja2 import Environment
from jinja2.ext import Extension
from jinja2.lexer import TokenStream, Token
from psycopg.sql import SQL

format_args = ContextVar("format_args")


class PsycopgExtension(Extension):
    def filter_stream(self, stream: TokenStream) -> Iterable[Token]:
        while not stream.eos:
            token = next(stream)
            if token.test("variable_begin"):
                var_expr: list[Token] = []
                while not token.test("variable_end"):
                    var_expr.append(token)
                    token = next(stream)
                variable_end = token

                last_token = var_expr[-1]
                lineno = last_token.lineno

                if not last_token.test("name") or last_token.value != "psycopg":
                    var_expr.insert(1, Token(lineno, "lparen", u"("))
                    var_expr.append(Token(lineno, "rparen", u")"))
                    var_expr.append(Token(lineno, "pipe", u"|"))
                    var_expr.append(Token(lineno, "name", u"psycopg"))

                var_expr.append(variable_end)
                yield from var_expr
            else:
                yield token


def psycopg_filter(value):
    if isinstance(value, SQL):
        return value.as_string(None)

    format_args.get().append(value)
    return "{}"


class JinjaPsycopg:
    def __init__(self, env: Optional[Environment] = None) -> None:
        self.env = env or Environment()
        self._prepare_environment()

    def _prepare_environment(self):
        self.env.add_extension(PsycopgExtension)
        self.env.filters["psycopg"] = psycopg_filter

    def render(self, source: str, params: dict[str, Any]):
        format_args.set([])
        try:
            sql = SQL(self.env.from_string(source).render(params))
            return sql.format(*format_args.get())
        finally:
            format_args.set(None)
