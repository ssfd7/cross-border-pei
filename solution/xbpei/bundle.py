"""Read the OKF bundle: its concepts, and the ontology terms their frontmatter refers to.

    python -m xbpei.bundle check
    python -m xbpei.bundle affected xbpei:holdingCapacity
    python -m xbpei.bundle glossary computations/effective-holding
    python -m xbpei.bundle glossary                                  (every concept that reads or writes terms)
"""
import json
import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache

import yaml

from . import BUNDLE, GRAPH_MAPPING, MAPPINGS, MODEL, XBPEI
from .ontology import curie, describe_term, graph_mapping, kind, mappings_for, to_iri, version

RESERVED = {"index.md", "log.md"}
GLOSSARY = "\n# Glossary\n"


@dataclass
class Concept:
    id: str
    meta: dict
    body: str

    @property
    def computation(self) -> str:
        """The single fenced block under `# Computation`."""
        section = self.body.split("# Computation", 1)[1]
        return re.search(r"```\w*\n(.*?)\n```", section, re.S).group(1)


def resolve(path: str, from_id: str = "") -> str:
    """Concept ID or bundle-relative file path for a bundle-relative or relative path."""
    if path.startswith("/"):
        target = BUNDLE / path[1:]
    else:
        target = (BUNDLE / from_id).parent / path
    return str(target.resolve().relative_to(BUNDLE.resolve())).removesuffix(".md")


@lru_cache
def concepts() -> dict[str, Concept]:
    found = {}
    for path in sorted(BUNDLE.rglob("*.md")):
        if path.name in RESERVED:
            continue
        _, front, body = path.read_text().split("---\n", 2)
        concept_id = str(path.relative_to(BUNDLE)).removesuffix(".md")
        found[concept_id] = Concept(concept_id, yaml.safe_load(front), body)
    return found


def concept(concept_id: str) -> Concept:
    return concepts()[concept_id.strip("/").removesuffix(".md")]


def terms_used() -> dict[str, set[str]]:
    """Ontology terms each concept reads or writes."""
    return {c.id: {curie(to_iri(t)) for t in c.meta.get("reads", []) + c.meta.get("writes", [])} for c in concepts().values()}


def affected_by(term: str) -> dict:
    """The computations and tools that read or write a term, and the procedure steps that use them."""
    term = curie(to_iri(term))
    direct = {c for c, terms in terms_used().items() if term in terms}
    steps = []
    for proc in concepts().values():
        for step in proc.meta.get("steps", []):
            used = sorted(direct & {resolve(u, proc.id) for u in step.get("uses", [])})
            if used:
                steps.append({"procedure": proc.id, "step": step["id"], "title": step["title"], "through": used})
    return {"term": term, "concepts": sorted(direct), "steps": steps}


def in_graph(term: str) -> list[str]:
    """Where a term lives in the graph, from the graph mapping."""
    found = []
    for m in graph_mapping()["mappings"]:
        table, is_edge = m.get("node") or m["edge"], "edge" in m
        what = f'a `{table}` edge from `{m["from"]}` to `{m["to"]}`' if is_edge else f"a `{table}` node"
        if m["term"] == term:
            found.append(what)
        if term in m.get("also_when", {}):
            found.append(f'{what} where `{m["also_when"][term]}`')
        if term in m.get("properties", {}):
            found.append(f'`{table}.{m["properties"][term]}`')
        for slot in ("links", "codes"):
            binding = m.get(slot, {}).get(term)
            if isinstance(binding, dict):
                found.append(f'`{table}.{binding["property"]}`')
            elif binding:
                found.append(f'the {"start" if binding == "from" else "end"} of the `{table}` edge, a `{m[binding]}` node')
        for binding in m.get("codes", {}).values():
            found += [f"`{table}.{binding['property']}` = '{code}'" for code, value in binding["values"].items() if value == term]
        if m.get("interval", {}).get("property") == term:
            found.append(f'`{table}.{m["interval"]["start"]}` to `{table}.{m["interval"]["end"]}`')
        if term in m.get("derived", {}):
            found.append(m["derived"][term])
    return found


def in_tables(term: str, c: Concept) -> list[str]:
    """Where a term lives in Postgres, from the source-system mappings: the tables the concept works on, or all of them."""
    entries = mappings_for(term).get("mappings", [])
    if c.meta["type"] == "Tool":  # tools write to the Clearance schema only
        entries = [e for e in entries if e["source"] == "clearance"]
    else:
        entries = [e for e in entries if e["table"] in c.body] or entries
    found = []
    for e in entries:
        table, columns = e["table"], lambda b: [b["column"]] if "column" in b else b.get("columns", [])
        if "term" in e:
            condition = e.get("when") or e.get("where")
            found.append(f"`{table}`" + (f" where `{' '.join(condition.split())}`" if condition else ""))
            continue  # the entry for the class itself: its property bindings belong to other terms
        if "properties" in e:
            found.append(f'`{table}.{e["properties"]}`')
        for slot in ("links", "inverse_links", "codes"):
            found += [f"`{table}.{column}`" for column in columns(e.get(slot, {}))]
        if "constants" in e:
            found.append(f'`{e["constants"]}` for every row of `{table}`')
        if "derived" in e:
            found.append(f'derived in `{table}`: {e["derived"]}')
        if "link_tables" in e:
            found.append(f'`{e["source"]}.{e["link_tables"]["table"]}`')
        if "interval" in e:
            found.append(f'`{table}.{e["interval"]["start"]}` to `{table}.{e["interval"]["end"]}`')
        for prop, binding in e.get("value_of", {}).items():
            codes = [code for code, value in binding["values"].items() if value == term] if isinstance(binding, dict) else []
            found += [f"`{table}.{binding['column']}` = '{code}'" for code in codes] or [f"the `{prop}` of every `{e['of']}` in `{table}`"]
    return list(dict.fromkeys(found))


def glossary(concept_id: str) -> str:
    """Meaning of each term a concept reads or writes, from the ontology, and where the term lives in the data the
    concept works on, from the mappings. The body of the concept's `# Glossary` section."""
    c, lines = concept(concept_id), []
    on_graph = c.meta.get("runtime") == "ladybug"
    for term in dict.fromkeys(c.meta.get("reads", []) + c.meta.get("writes", [])):
        d = describe_term(term)
        meaning = [d["definition"], d.get("scope_note", "")]
        meaning += [f"Kind of `{parent}`." for parent in d.get("kinds_of", [])]
        if "of" in d:
            meaning.append("Of " + ", ".join(f"`{owner}`" for owner in d["of"]) + ".")
            rng = d.get("range")
            meaning.append(f"Allowed: {', '.join(rng)}." if isinstance(rng, list)
                           else f"Value: `{rng.replace('http://www.w3.org/2001/XMLSchema#', 'xsd:')}`." if rng else "")
        facts = [d["kind"], d.get("status"), f'steward: {d["steward"]}' if d.get("steward") else None]
        places = in_graph(term) if on_graph else in_tables(term, c)
        lines += [f'- **`{term}`** ({"; ".join(f for f in facts if f)})',
                  f'  - Meaning: {" ".join(m for m in meaning if m) or "No definition in the ontology."}',
                  f'  - {"In the graph" if on_graph else "In Postgres"}: {("; ".join(places) or "not held").rstrip(".")}.']
    here = (BUNDLE / c.id).parent
    mapping = GRAPH_MAPPING if on_graph else MAPPINGS
    head = (f"Meanings from ontology version {version()}, [{MODEL.name}]({os.path.relpath(MODEL, here)}). "
            f'Locations from the {"graph mapping" if on_graph else "mapping files"}, '
            f"[{mapping.name}]({os.path.relpath(mapping, here)}). "
            "For the terms in `reads` and `writes`. Generated by `xbpei/bundle.py`; do not edit.")
    return "\n".join([head, ""] + lines)


def write_glossary(concept_id: str) -> None:
    """Add or refresh the `# Glossary` section, the last section of the concept's file."""
    path = BUNDLE / f"{concept(concept_id).id}.md"
    body = path.read_text().split(GLOSSARY)[0].rstrip("\n")
    path.write_text(f"{body}\n{GLOSSARY}\n{glossary(concept_id)}\n")


def check() -> list[str]:
    problems = []
    declared = yaml.safe_load((BUNDLE / "index.md").read_text().split("---\n", 2)[1]).get("ontology", {})
    if declared.get("prefix") != "xbpei" or declared.get("namespace") != str(XBPEI):
        problems.append(f"index: the ontology prefix and namespace declared are not xbpei and {XBPEI}")
    if not (BUNDLE / declared.get("resource", "missing")).exists():
        problems.append("index: the ontology resource declared does not exist")
    for c in concepts().values():
        if not c.meta.get("type"):
            problems.append(f"{c.id}: no type")
        for term in c.meta.get("reads", []) + c.meta.get("writes", []):
            if kind(to_iri(term)) is None:
                problems.append(f"{c.id}: {term} is not in the ontology")
        paths = [u for s in c.meta.get("steps", []) for u in s.get("uses", [])]
        paths += [c.meta[k]["resource"] for k in ("executor", "attester") if k in c.meta]
        paths += re.findall(r"\]\((/[^)]+)\)", c.body)
        for path in paths:
            if not (BUNDLE / resolve(path, c.id)).exists() and resolve(path, c.id) not in concepts():
                problems.append(f"{c.id}: {path} does not resolve")
        if c.meta.get("type") == "Attested Computation":
            declared = {p["name"] for p in c.meta["parameters"]}
            used = set(re.findall(r"%\((\w+)\)s|\$(\w+)", c.computation))
            used = {a or b for a, b in used}
            if used != declared:
                problems.append(f"{c.id}: computation binds {sorted(used)}, declares {sorted(declared)}")
        if GLOSSARY in c.body and c.body.split(GLOSSARY)[1].strip() != glossary(c.id):
            problems.append(f"{c.id}: glossary is out of date with the ontology or the mappings")
    return problems


if __name__ == "__main__":
    if sys.argv[1] == "check":
        found = check()
        print("\n".join(found) if found else f"Bundle is consistent: {len(concepts())} concepts.")
        sys.exit(1 if found else 0)
    if sys.argv[1] == "glossary":
        for concept_id in sys.argv[2:] or [c.id for c in concepts().values() if c.meta.get("reads") or c.meta.get("writes")]:
            write_glossary(concept_id)
        sys.exit(0)
    print(json.dumps(affected_by(sys.argv[2]), indent=2))
