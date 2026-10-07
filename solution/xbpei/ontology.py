"""Lookup tools over the ontology and the mappings.

The ontology says what a term means and who stewards it. The mappings say where its instances
live. Neither is a query: callers write the SQL or Cypher themselves from what these return.

    python -m xbpei.ontology find "beneficial owner"
    python -m xbpei.ontology describe xbpei:OwnershipInterest
    python -m xbpei.ontology mappings xbpei:vintageYear
"""
import json
import sys
from functools import lru_cache

import yaml
from rdflib import BNode, Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from . import GOVERNANCE, MAPPINGS, MODEL, XBPEI

KINDS = {OWL.Class: "class", OWL.ObjectProperty: "relationship", OWL.DatatypeProperty: "attribute",
         OWL.AnnotationProperty: "annotation", RDFS.Datatype: "datatype"}
# Places in a mapping entry where a property of the term can be bound to the source.
PROPERTY_SLOTS = ("properties", "links", "inverse_links", "codes", "constants", "derived", "link_tables")


@lru_cache
def graph() -> Graph:
    g = Graph()
    g.parse(MODEL)
    g.parse(GOVERNANCE)
    return g


@lru_cache
def mapping_files() -> list[dict]:
    return [yaml.safe_load(p.read_text()) for p in sorted(MAPPINGS.glob("*.yaml"))]


def version() -> str:
    """The version of the ontology as loaded."""
    return str(graph().value(graph().value(predicate=RDF.type, object=OWL.Ontology), OWL.versionInfo))


def curie(iri) -> str:
    return "xbpei:" + str(iri)[len(str(XBPEI)):] if str(iri).startswith(str(XBPEI)) else str(iri)


def to_iri(term: str) -> URIRef:
    return XBPEI[term.split(":", 1)[1]] if term.startswith("xbpei:") else URIRef(term)


def members(node) -> list:
    """A named class, or the classes of an owl:unionOf."""
    if isinstance(node, BNode):
        union = graph().value(node, OWL.unionOf)
        return list(Collection(graph(), union)) if union else []
    return [node]


def kind(iri) -> str | None:
    types = set(graph().objects(iri, RDF.type))
    for owl_type, name in KINDS.items():
        if owl_type in types:
            return name
    return "code" if types else None


def find_term(text: str) -> list[dict]:
    """Terms whose label, name or definition contains every word of the text, best match first."""
    g, words, hits = graph(), text.lower().split(), []
    for iri in {s for s in g.subjects() if str(s).startswith(str(XBPEI))}:
        label = str(g.value(iri, RDFS.label) or g.value(iri, SKOS.prefLabel) or "")
        definition = str(g.value(iri, SKOS.definition) or "")
        name = f"{label} {curie(iri)}".lower()
        if all(w in name for w in words):
            rank = 0 if label.lower() == text.lower() else 1
        elif all(w in f"{name} {definition.lower()}" for w in words):
            rank = 2
        else:
            continue
        hits.append((rank, curie(iri), {"term": curie(iri), "label": label, "kind": kind(iri), "definition": definition}))
    return [h[2] for h in sorted(hits, key=lambda h: h[:2])]


def describe_term(term: str) -> dict | None:
    """Meaning, steward and status of a term, with its place in the model. None if it is not a term."""
    g, iri = graph(), to_iri(term)
    if kind(iri) is None:
        return None
    out = {
        "term": curie(iri),
        "label": str(g.value(iri, RDFS.label) or g.value(iri, SKOS.prefLabel) or ""),
        "kind": kind(iri),
        "definition": str(g.value(iri, SKOS.definition) or ""),
        "scope_note": str(g.value(iri, SKOS.scopeNote) or "") or None,
        "steward": str(g.value(iri, XBPEI.steward) or "") or None,
        "status": str(g.value(iri, XBPEI.termStatus) or "") or None,
    }
    if out["kind"] == "class":
        out["kinds_of"] = [curie(c) for c in g.objects(iri, RDFS.subClassOf) if isinstance(c, URIRef)]
        ancestors = {iri} | set(g.transitive_objects(iri, RDFS.subClassOf))
        out["properties"] = sorted(curie(p) for p in g.subjects(RDFS.domain) if ancestors & set(members(g.value(p, RDFS.domain))))
    elif out["kind"] in ("relationship", "attribute"):
        out["of"] = [curie(c) for c in members(g.value(iri, RDFS.domain))]
        rng = g.value(iri, RDFS.range)
        values = g.value(rng, OWL.oneOf) if isinstance(rng, BNode) else None
        out["range"] = [str(v) for v in Collection(g, values)] if values else curie(rng) if isinstance(rng, URIRef) else None
        out["single_valued"] = (iri, RDF.type, OWL.FunctionalProperty) in g
    return {k: v for k, v in out.items() if v is not None}


def mappings_for(term: str) -> dict:
    """Where instances of a term live. An unmapped term is reported as such, never guessed."""
    iri = to_iri(term)
    term = curie(iri)
    if kind(iri) is None:
        return {"term": term, "known": False, "mapped": False,
                "message": f"{term} is not a term of the ontology. It is out of scope; do not answer from the data."}
    found = []
    for file in mapping_files():
        for m in file["mappings"]:
            base = {"source": file["source"], "table": f'{file["source"]}.{m["table"]}', "key": m["key"],
                    "system_of_record": m["system_of_record"]}
            if m["term"] == term or term in m.get("also_when", {}):
                entry = dict(m, **base)
                if term in m.get("also_when", {}):
                    entry["when"] = m["also_when"][term]
                found.append(entry)
                continue
            bound = {slot: m[slot][term] for slot in PROPERTY_SLOTS if term in m.get(slot, {})}
            if m.get("interval", {}).get("property") == term:
                bound["interval"] = m["interval"]
            if bound:
                extra = {k: m[k] for k in ("where", "yields_to", "scope", "warnings", "gaps") if k in m}
                found.append(dict(base, of=m["term"], **bound, **extra))
    if not found:
        return {"term": term, "known": True, "mapped": False,
                "message": f"No source system holds {term}. Say so; do not answer from another column."}
    return {"term": term, "known": True, "mapped": True, "mappings": found}


if __name__ == "__main__":
    command, argument = sys.argv[1], " ".join(sys.argv[2:])
    result = {"find": find_term, "describe": describe_term, "mappings": mappings_for}[command](argument)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
