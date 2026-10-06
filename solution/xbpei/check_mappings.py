"""Check the mapping files against the ontology and the database.

A mapping file describes one source system:

    source, steward      schema name and the team that owns the mapping
    party_identity       how a party in this system is matched to the same party elsewhere
    mappings             one entry per place where instances of a term live:
        term, table, key     the term, the table holding its instances and the key column(s)
        where                restriction on the rows, as SQL
        system_of_record     true, false or partial; yields_to names the source that prevails
        also_when            further classes an instance belongs to, each with its SQL condition
        properties           attribute -> column
        links, inverse_links relationship -> column(s), and the table.column it references
        codes                relationship -> column holding a code, with the code's meaning
        constants            property -> a value every row has
        derived              property -> how its value follows from other records, in words
        link_tables          relationship -> a separate table holding the link
        interval             the period property with its start and end columns
        scope, warnings, gaps   what a reader must know before using the rows
    unmapped_columns, unmapped_tables   what has no term, and why

    python -m xbpei.check_mappings
"""
import re
import sys

import psycopg

from . import DSN
from .ontology import kind, mapping_files, to_iri


def terms_in(node):
    """Every xbpei: name used as a key or a value anywhere in a mapping entry."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in ("scope", "warnings", "gaps", "derived", "where", "also_when"):
                yield from terms_in(v)
            if isinstance(k, str) and k.startswith("xbpei:"):
                yield k
        for slot in ("derived", "also_when"):
            yield from (k for k in node.get(slot, {}) if k.startswith("xbpei:"))
    elif isinstance(node, list):
        for v in node:
            yield from terms_in(v)
    elif isinstance(node, str) and node.startswith("xbpei:"):
        yield node


def as_list(value) -> list:
    return value if isinstance(value, list) else [value]


def columns_in(source: str, m: dict):
    """(schema.table, column) for every column an entry names."""
    table = f'{source}.{m["table"]}'
    names = as_list(m["key"]) + list(m.get("properties", {}).values())
    for slot in ("links", "inverse_links", "codes"):
        for binding in m.get(slot, {}).values():
            names += as_list(binding.get("column", [])) + binding.get("columns", [])
            if "references" in binding:
                ref_table, ref_column = binding["references"].rsplit(".", 1)
                yield ref_table, ref_column
    names += [m["interval"][k] for k in ("start", "end") if "interval" in m]
    yield from ((table, n) for n in names)
    yield from ((table, n) for n in condition_columns([m.get("where", ""), *m.get("also_when", {}).values()]))
    for binding in m.get("link_tables", {}).values():
        link_table = f'{source}.{binding["table"]}'
        yield from ((link_table, n) for n in as_list(binding["from"]) + as_list(binding["to"]))
        yield from ((link_table, n) for n in condition_columns([binding.get("where", "")]))


def condition_columns(conditions: list[str]) -> list[str]:
    """Column names in SQL conditions of the form `column = ...` or `column IN ...`."""
    return [c for condition in conditions for c in re.findall(r"(\w+)\s*(?:=|IN\b)", condition)]


def check() -> list[str]:
    with psycopg.connect(DSN) as conn:
        existing = {(f"{s}.{t}", c) for s, t, c in conn.execute(
            "SELECT table_schema, table_name, column_name FROM information_schema.columns")}
    problems, mapped = [], set()
    if not mapping_files():
        return ["No mapping files found."]
    for file in mapping_files():
        source = file["source"]
        identity = file.get("party_identity", {})
        if "table" in identity:
            mapped |= {(f'{source}.{identity["table"]}', c) for c in [identity["key"], *identity["match_on"]]}
        for m in file["mappings"]:
            where = f'{source}.{m["table"]} ({m["term"]})'
            problems += [f"{where}: {t} is not in the ontology" for t in set(terms_in(m)) if kind(to_iri(t)) is None]
            for table, column in columns_in(source, m):
                mapped.add((table, column))
                if (table, column) not in existing:
                    problems.append(f"{where}: no column {table}.{column}")
        declared = {tuple(f"{source}.{k}".rsplit(".", 1)) for k in file.get("unmapped_columns", {})}
        skipped = {f"{source}.{t}" for t in file.get("unmapped_tables", {})}
        for table, column in sorted(existing):
            if table.startswith(source + ".") and table not in skipped and (table, column) not in mapped | declared:
                problems.append(f"{table}.{column} is neither mapped nor declared unmapped")
    return problems


if __name__ == "__main__":
    found = check()
    print("\n".join(found) if found else "Mappings agree with the ontology and the database.")
    sys.exit(1 if found else 0)
