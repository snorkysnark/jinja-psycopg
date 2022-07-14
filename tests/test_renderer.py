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
    params = {"table": sql.Identifier("sources"), "id": 5}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


def test_no_args(conn: Connection):
    query = "SELECT * FROM aaa"

    assert JinjaPsycopg().render(query).as_string(conn) == query


def test_string(conn: Connection):
    query = "WHERE name = {{ 'foo' }}"
    expected = "WHERE name = 'foo'"

    assert JinjaPsycopg().render(query).as_string(conn) == expected


def test_string_order(conn: Connection):
    query = "WHERE name = {{ foo }}, value = {{ 'bar' }}"
    expected = "WHERE name = 'foo', value = 'bar'"
    params = {"foo": "foo"}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


class CustomRenderer(JinjaPsycopg):
    def _prepare_environment(self):
        super()._prepare_environment()

        def uppercase(string: str):
            return string.upper()

        self.env.globals["uppercase"] = uppercase


def test_function(conn: Connection):
    query = "VALUES ( {{ uppercase('bar') }} )"
    expected = "VALUES ( 'BAR' )"

    assert CustomRenderer().render(query).as_string(conn) == expected


def test_function_order(conn: Connection):
    query = "VALUES ( {{ foo }}, {{ uppercase('bar') }} )"
    expected = "VALUES ( 'foo', 'BAR' )"
    params = {"foo": "foo"}

    assert CustomRenderer().render(query, params).as_string(conn) == expected
