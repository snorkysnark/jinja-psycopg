# Jinja-Psycopg

Jinja-Psycopg is a bridge between the [jinja](https://jinja.palletsprojects.com/en/3.1.x/) templating engine
and psycopg3's [type-aware formatting](https://www.psycopg.org/psycopg3/docs/api/sql.html).

## Basic Usage

```py
from jinja_psycopg import JinjaPsycopg
from psycopg.sql import Identifier

query = """\
{% set sep = joiner('\nAND ') -%}

SELECT * FROM {{ table }}
WHERE
{% for column, value in where %}
{{- sep() | sql -}}
{{ column }} = {{ value }}
{%- endfor %};
"""

renderer = JinjaPsycopg()
renderer.render(
    query,
    {
        "table": Identifier("people"),
        "where": [
            (Identifier("name"), "Simon"),
            (Identifier("year"), 2015),
            (Identifier("subject"), Placeholder("subject")),
        ],
    },
)
```

This script renders the following SQL.

Strings will be automatically escaped,
Identifiers quoted and Placeholders wrapped with the placeholder syntax

```sql
SELECT * FROM "people"
WHERE
"name" = 'Simon'
AND "year" = 2015
AND "subject" = %(subject)s;
```

## The Composed object

Ok, that's not the whole story.

The render() method returns a [psycopg.sql.Composed][],
which needs to be turned into a string by the backend:

```py
psycopg.connect("dbame=test") as conn:
    # Render to string
    print(composed.as_string(conn))
     # Or execute directly
    conn.execute(composed, {"subject": "Math"})
```

## SqlTemplate and SqlTemplateModule

Like in jinja, you can save your templates

```py linenums="1"
template = renderer.from_string(
    """\
    {% set config = { 'option': True } %}
    select field from {{ table }};"""
)
```

And turn them into python modules

```py linenums="6"
module = template.make_module({ "table": Identifier("foo") })
assert getattr(sqlmodule.module, "config")['option'] == True

# Render to SQL
composed = sqlmodule.render()
```

## Custom SQL Objects

```py
@dataclass
class Table:
    schema: str
    name: str

    def __sql__(self):
        return Identifier(self.name, self.schema)

renderer.render(
    "select * from {{ table }}",
    {"table": Table("public", "foo")}
)
```

## Custom Environments

To add your own global variables and filters
to the jinja Environment, you can subclass JinjaPsycopg

```py
class CustomRenderer(JinjaPsycopg):
    def _prepare_environment(self):
        super()._prepare_environment()

        self._env.globals["foo"] = my_global_variable
        self._env.filters["bar"] = my_filter
```

## Filters

### psycopg

This filter is applied **automatically** to all jinja blocks:

`{{ value }}` is equivalent to `{{ (value) | psycopg }}`

It stores the actual value inside a ContextVar,
replacing `{{value}}` with a placeholder like `{dictionary_key}`
to later be passed to SQL.format

### sql

Treat a string value as plain SQL, not as a literal

`ALTER TABLE foo {{ 'ADD COLUMN html TEXT' | sql }}`

### sqljoin

Same as jinja's
[join](https://jinja.palletsprojects.com/en/3.1.x/templates/?highlight=join#jinja-filters.join) filter,
but operates on SQL objects

`{{ [Identifier("foo"), Identifier("bar")] | sqljoin(',') }}`
