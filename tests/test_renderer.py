from dataclasses import dataclass
from textwrap import dedent
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

        self._env.globals["appendA"] = appendA
        self._env.filters["appendB"] = appendB


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
    query = "SELECT * FROM {{ table | psycopg }}"
    expected = 'SELECT * FROM "jsons"'
    params = {"table": sql.Identifier("jsons")}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


@pytest.mark.parametrize(
    "flag,expected",
    [
        (False, "SELECT * FROM sources"),
        (True, "SELECT * FROM sources WHERE id = 5"),
    ],
)
def test_if(conn: Connection, flag: bool, expected: str):
    query = "SELECT * FROM sources{% if flag %} WHERE id = {{ id }}{% endif %}"
    params = {"flag": flag, "id": 5}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


def test_for(conn: Connection):
    query = dedent(
        """\
        {% for column in columns -%}
        ADD COLUMN {{ column }} TEXT{% if not loop.last %},
        {% endif %}{% endfor %}\
        """
    )
    expected = dedent(
        """\
        ADD COLUMN "id" TEXT,
        ADD COLUMN "source" TEXT,
        ADD COLUMN "html" TEXT\
        """
    )
    params = {
        "columns": [
            sql.Identifier("id"),
            sql.Identifier("source"),
            sql.Identifier("html"),
        ]
    }

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


def test_for_static(conn: Connection):
    query = dedent(
        """\
        {% for ident in idents -%}
        {{ 'text' }} {{ ident }}{% if not loop.last %},
        {% endif %}{% endfor %}\
        """
    )
    expected = dedent(
        """\
        'text' "foo",
        'text' "bar",
        'text' "fluff"\
        """
    )
    params = {
        "idents": [
            sql.Identifier("foo"),
            sql.Identifier("bar"),
            sql.Identifier("fluff"),
        ]
    }

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


def test_module(conn: Connection):
    query = dedent(
        """\
        {% set val = 1 -%}
        SELECT * FROM {{ table }}"""
    )
    expected = 'SELECT * FROM "sources"'
    params = {"table": sql.Identifier("sources")}

    sql_module = JinjaPsycopg().from_string(query).make_module(params)
    rendered = sql_module.render().as_string(conn)

    assert rendered == expected
    assert sql_module._module.val == 1  # type:ignore


def test_module_static(conn: Connection):
    query = dedent(
        """\
        {% set val = 1 -%}
        {{ 'text' }} {{ table }}"""
    )
    expected = "'text' \"sources\""
    params = {"table": sql.Identifier("sources")}

    sql_module = JinjaPsycopg().from_string(query).make_module(params)
    rendered = sql_module.render().as_string(conn)

    assert rendered == expected
    assert sql_module._module.val == 1  # type:ignore


def test_sql_filter(conn: Connection):
    query = "SELECT * FROM {{ 'foo' | sql }}"
    expected = "SELECT * FROM foo"

    assert JinjaPsycopg().render(query).as_string(conn) == expected


@dataclass
class Table:
    schema: str
    name: str

    def __sql__(self):
        return sql.SQL("{}.{}").format(
            sql.Identifier(self.schema), sql.Identifier(self.name)
        )


def test_into_sql(conn: Connection):
    query = "SELECT * FROM {{ table }}"
    expected = 'SELECT * FROM "public"."items"'
    params = {"table": Table("public", "items")}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


def test_join(conn: Connection):
    query = "{{ values | sqljoin(',\n') }}"
    expected = dedent(
        """\
        "foo",
        "sources"."bar\""""
    )
    params = {"values": [sql.Identifier("foo"), Table("sources", "bar")]}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected


@dataclass
class Column:
    name: str
    type: str

    @property
    def add_column(self):
        return sql.SQL("ADD COLUMN {} {}").format(
            sql.Identifier(self.name), sql.SQL(self.type)
        )


def test_join_attribute(conn: Connection):
    query = "{{ columns | sqljoin(',\n', attribute='add_column') }}"
    expected = dedent(
        """\
        ADD COLUMN "id" SERIAL PRIMARY KEY,
        ADD COLUMN "name" TEXT"""
    )
    params = {"columns": [Column("id", "SERIAL PRIMARY KEY"), Column("name", "TEXT")]}

    assert JinjaPsycopg().render(query, params).as_string(conn) == expected
