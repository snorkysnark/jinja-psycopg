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

        def appendA(string: str):
            return string + "A"

        def appendB(string: str):
            return string + "B"

        self.env.globals["appendA"] = appendA
        self.env.filters["appendB"] = appendB


def test_function(conn: Connection):
    query = "VALUES ( {{ appendA('bar') }} )"
    expected = "VALUES ( 'barA' )"

    assert CustomRenderer().render(query).as_string(conn) == expected


def test_function_order(conn: Connection):
    query = "VALUES ( {{ foo }}, {{ appendA('bar') }} )"
    expected = "VALUES ( 'foo', 'barA' )"
    params = {"foo": "foo"}

    assert CustomRenderer().render(query, params).as_string(conn) == expected


def test_filter(conn: Connection):
    query = "VALUES ( {{ 'bar' | appendB }} )"
    expected = "VALUES ( 'barB' )"

    assert CustomRenderer().render(query).as_string(conn) == expected


def test_filter_order(conn: Connection):
    query = "VALUES ( {{ foo }}, {{ 'bar' | appendB }} )"
    expected = "VALUES ( 'foo', 'barB' )"
    params = {"foo": "foo"}

    assert CustomRenderer().render(query, params).as_string(conn) == expected


def test_manual_psycopg(conn: Connection):
    query = "SELECT * FROM {{ table | psycopg('table') }}"
    expected = 'SELECT * FROM "jsons"'
    params = {"table": sql.Identifier("jsons")}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


def test_partial_psycopg(conn: Connection):
    query = "SELECT * FROM {{ table | psycopg }}"
    expected = 'SELECT * FROM "jsons"'
    params = {"table": sql.Identifier("jsons")}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected
