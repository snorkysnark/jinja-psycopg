# Injection-safe SQL templating engine, Powered by Jinja+Psycopg

## Why [jinja](https://jinja.palletsprojects.com/en/3.1.x/) templates are not enough

```python
env = Environment()
template = env.from_string(
    """
    select * from {{ table }}
    {% if name is not None %}
    where name = {{ name }}
    {% endif %}
    """
)
template.render(
    table="foo",
    name="R'lyeh" # This will fail
)
```

Pros:
- if blocks, loops, filters, custom code, etc

Cons:
- just a string templating engine, doesn't do any escaping

## Psycopg's built-in string composition

Similarly, [psycopg3](https://www.psycopg.org/psycopg3/docs/api/sql.html)
has its own way of building queries, based on python's string formatting syntax

```python
composed = SQL(
    """
    select * from {table}
    where name = {name}
    """
).format(table=Identifier("foo"), name="R'lyeh")

with psycopg.connect() as conn:
    # db connection is needed to actually render the query
    query = composed.as_string(conn)
```

Pros:
- Can differentiate between identifiers, literals and plain SQL
- Native escaping using libpq

Cons:
- Limited templating functionality

## JinjaPsycopg, best of both worlds

```python
from jinja_psycopg import JinjaPsycopg
from psycopg.sql import Identifier

query = """\
select * from {{ table }}
{% if name is not None %}
where name = {{ name }}
{% endif %}"""

renderer = JinjaPsycopg()
template = renderer.from_string(query)
composed = template.render(table=Identifier("foo"), name="R'lyeh")

with psycopg.connect() as conn, conn.cursor() as cursor:
    # Render to string
    query = composed.as_string(cursor)
    # Execute
    cursor.execute(composed)
```
or, as a shortcut:

```python
composed = renderer.render(query, { "table": Identifier("foo"), "name": "R'lyeh" })
```

[make_module](https://jinja.palletsprojects.com/en/3.1.x/api/?highlight=make_module#jinja2.Template.make_module)
is also supported, allowing you to extract configuration values from your template

```python
sqlmodule = renderer.from_string(
    """
    {% set config = { 'option': True } %}
    select field from {{ table }}
    """
).make_module({ "table": Identifier("foo") })

assert getattr(sqlmodule.module, "config")['option'] == True

# Render to SQL
composed = sqlmodule.render()
```

### Custom SQL Objects

```python
@dataclass
class Table:
    schema: str
    name: str

    def __sql__(self):
        return SQL("{}.{}").format(
            Identifier(self.schema), Identifier(self.name)
        )

renderer.render("select * from {{ table }}", { "table": Table("public", "foo") })
```

### Filters

#### psycopg

This filter is applied **automatically** to all jinja blocks:

`{{ value }}` is equivalent to `{{ (value) | psycopg }}`

It stores the actual value inside a ContextVar,
replacing `{{value}}` with a placeholder like `{dictionary_key}`
to later be passed to SQL.format

#### sql

Treat a string value as plain SQL, not as a literal

`ALTER TABLE foo {{ 'ADD COLUMN html TEXT' | sql }}`

#### sqljoin

Same as jinja's
[join](https://jinja.palletsprojects.com/en/3.1.x/templates/?highlight=join#jinja-filters.join) filter,
but operates on SQL objects

`{{ [Identifier("foo"), Identifier("bar")] | sqljoin(',') }}`
