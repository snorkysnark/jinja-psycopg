from textwrap import dedent

import pytest
import psycopg
from psycopg import Connection, sql

from jinja_psycopg import JinjaPsycopg


@pytest.fixture
def renderer():
    return JinjaPsycopg()


@pytest.fixture
def conn():
    connection = psycopg.connect()
    yield connection
    connection.close()


def test_args(renderer: JinjaPsycopg, conn: Connection):
    query = "SELECT * FROM {{ table }} WHERE id = {{ id }}"
    expected = 'SELECT * FROM "sources" WHERE id = 5'

    assert (
        renderer.render(query, {"table": sql.Identifier("sources"), "id": 5}).as_string(
            conn
        )
        == expected
    )


def test_no_args(renderer: JinjaPsycopg, conn: Connection):
    query = "SELECT * FROM aaa"

    assert renderer.render(query, {}).as_string(conn) == query


def test_string(renderer: JinjaPsycopg, conn: Connection):
    query = "{{ 'foo' }}"
    expected = "'foo'"

    assert renderer.render(query, {}).as_string(conn) == expected


def test_string_order(renderer: JinjaPsycopg, conn: Connection):
    query = "{{ foo }}, {{ 'bar' }}"
    expected = "'foo', 'bar'"

    assert renderer.render(query, {"foo": "foo"}).as_string(conn) == expected
