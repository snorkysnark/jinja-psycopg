from typing import Iterable
from jinja2.ext import Extension
from jinja2.lexer import TokenStream, Token


class PsycopgExtension(Extension):
    """Wraps all expressions with the psycopg filter,
    so
    `{{ variable | filter1 | filter2 }}`
    becomes
    `{{ (variable | filter1 | filter2) | psycopg }}`
    """

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
