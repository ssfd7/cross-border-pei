"""Read the OKF bundle: its concepts, and their frontmatter as linked data alongside the ontology.

    python -m xbpei.bundle check
    python -m xbpei.bundle affected xbpei:holdingCapacity
"""
import json
import re
import sys
from dataclasses import dataclass
from functools import lru_cache

import yaml
from rdflib import Graph, Namespace, URIRef

from . import BUNDLE
from .ontology import curie, kind, to_iri

OKF = Namespace("https://w3id.org/xb-pei/okf#")
BASE = "urn:xbpei:bundle:"
RESERVED = {"index.md", "log.md"}


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


@lru_cache
def graph() -> Graph:
    """Every concept's frontmatter as RDF, read with the bundle's JSON-LD context."""
    context = json.loads((BUNDLE / "context.jsonld").read_text())["@context"]
    g = Graph()
    for c in concepts().values():
        doc = {k: v for k, v in c.meta.items() if k not in ("@context", "steps")}
        doc["steps"] = [dict(s, uses=[BASE + resolve(u, c.id) for u in s.get("uses", [])]) for s in c.meta.get("steps", [])]
        doc.update({"@context": context, "@id": BASE + c.id})
        g.parse(data=json.dumps(doc, default=str), format="json-ld")
    return g


def affected_by(term: str) -> dict:
    """The computations and tools that read or write a term, and the procedure steps that use them."""
    g, iri = graph(), to_iri(term)
    direct = {str(s)[len(BASE):] for p in (OKF.reads, OKF.writes) for s in g.subjects(p, iri)}
    steps = []
    for proc in concepts().values():
        for step in proc.meta.get("steps", []):
            used = sorted(direct & {resolve(u, proc.id) for u in step.get("uses", [])})
            if used:
                steps.append({"procedure": proc.id, "step": step["id"], "title": step["title"], "through": used})
    return {"term": curie(iri), "concepts": sorted(direct), "steps": steps}


def terms_used() -> dict[str, set[str]]:
    """Ontology terms each concept reads or writes."""
    g = graph()
    return {c: {curie(o) for p in (OKF.reads, OKF.writes) for o in g.objects(URIRef(BASE + c), p)} for c in concepts()}


def check() -> list[str]:
    problems = []
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
    return problems


if __name__ == "__main__":
    if sys.argv[1] == "check":
        found = check()
        print("\n".join(found) if found else f"Bundle is consistent: {len(concepts())} concepts.")
        sys.exit(1 if found else 0)
    print(json.dumps(affected_by(sys.argv[2]), indent=2))
