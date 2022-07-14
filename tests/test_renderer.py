import pytest
import psycopg
from psycopg import Connection, sql

from jinja_psycopg import JinjaPsycopg


@pytest.fixture
def conn():
    connection = psycopg.connect()
    yield connection
    connection.close()


def test_args(conn: Connection):
    query = "SELECT * FROM {{ table }} WHERE id = {{ id }}"
    expected = 'SELECT * FROM "sources" WHERE id = 5'

    assert (
        JinjaPsycopg()
        .render(query, {"table": sql.Identifier("sources"), "id": 5})
        .as_string(conn)
        == expected
    )


def test_no_args(conn: Connection):
    query = "SELECT * FROM aaa"

    assert JinjaPsycopg().render(query, {}).as_string(conn) == query


def test_string(conn: Connection):
    query = "{{ 'foo' }}"
    expected = "'foo'"

    assert JinjaPsycopg().render(query, {}).as_string(conn) == expected


def test_string_order(conn: Connection):
    query = "{{ foo }}, {{ 'bar' }}"
    expected = "'foo', 'bar'"

    assert JinjaPsycopg().render(query, {"foo": "foo"}).as_string(conn) == expected


class CustomRenderer(JinjaPsycopg):
    def _prepare_environment(self):
        super()._prepare_environment()

        def uppercase(string: str):
            return string.upper()

        self.env.globals["uppercase"] = uppercase


def test_function(conn: Connection):
    query = "{{ uppercase('bar') }}"
    expected = "'BAR'"

    assert CustomRenderer().render(query, {}).as_string(conn) == expected


def test_function_order(conn: Connection):
    query = "{{ foo }}, {{ uppercase('bar') }}"
    expected = "'foo', 'BAR'"

    assert CustomRenderer().render(query, {"foo": "foo"}).as_string(conn) == expected
