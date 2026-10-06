"""Generate what follows mechanically from the Turtle: the JSON-LD form of the ontology, which the
procedure bundles point at, and the SHACL shapes for each class.

    python -m xbpei.build_model
"""
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

from . import MODEL_JSONLD, SHAPES, XBPEI
from .ontology import graph, members

XBSH = Namespace("https://w3id.org/xb-pei/shapes#")
FACETS = {XSD.pattern: SH.pattern, XSD.minInclusive: SH.minInclusive, XSD.maxInclusive: SH.maxInclusive}


def build_jsonld() -> None:
    g = graph()
    context = {prefix: str(ns) for prefix, ns in g.namespaces() if prefix in
               ("xbpei", "owl", "rdfs", "xsd", "skos", "dcterms", "dcat", "prov", "time", "vann")}
    g.serialize(MODEL_JSONLD, format="json-ld", context=context, indent=2)


def datatype_constraints(g: Graph, shapes: Graph, prop_shape: BNode, rng) -> None:
    """Translate an attribute's range: a plain datatype, a list of allowed values, or a restricted datatype."""
    if isinstance(rng, URIRef) and str(rng).startswith(str(XSD)):
        shapes.add((prop_shape, SH.datatype, rng))
        return
    allowed = g.value(rng, OWL.oneOf)
    if allowed:
        Collection(shapes, values := BNode(), list(Collection(g, allowed)))
        shapes.add((prop_shape, SH["in"], values))
        return
    restricted = g.value(rng, OWL.equivalentClass) if isinstance(rng, URIRef) else rng
    if restricted is None:
        return
    shapes.add((prop_shape, SH.datatype, g.value(restricted, OWL.onDatatype)))
    for facet_node in Collection(g, g.value(restricted, OWL.withRestrictions)):
        for facet, value in g.predicate_objects(facet_node):
            anchored = Literal(f"^{value}$") if facet == XSD.pattern else value
            shapes.add((prop_shape, FACETS[facet], anchored))


def build_shapes() -> int:
    g, shapes = graph(), Graph()
    shapes.bind("sh", SH)
    shapes.bind("xbpei", XBPEI)
    shapes.bind("xbsh", XBSH)
    classes = sorted(c for c in g.subjects(RDF.type, OWL.Class) if str(c).startswith(str(XBPEI)))
    for cls in classes:
        shape = XBSH[str(cls)[len(str(XBPEI)):] + "Shape"]
        shapes.add((shape, RDF.type, SH.NodeShape))
        shapes.add((shape, SH.targetClass, cls))
        for prop in sorted(p for p in g.subjects(RDFS.domain) if cls in members(g.value(p, RDFS.domain))):
            prop_shape = BNode()
            shapes.add((shape, SH.property, prop_shape))
            shapes.add((prop_shape, SH.path, prop))
            if (prop, RDF.type, OWL.FunctionalProperty) in g:
                shapes.add((prop_shape, SH.maxCount, Literal(1)))
            rng = g.value(prop, RDFS.range)
            if (prop, RDF.type, OWL.DatatypeProperty) in g:
                datatype_constraints(g, shapes, prop_shape, rng)
            elif isinstance(rng, URIRef) and str(rng).startswith(str(XBPEI)):
                shapes.add((prop_shape, SH["class"], rng))
    header = "# Generated from model/xb-pei-model.ttl by xbpei/build_model.py. Do not edit.\n\n"
    (SHAPES / "generated.ttl").write_text(header + shapes.serialize(format="turtle"))
    return len(classes)


if __name__ == "__main__":
    build_jsonld()
    print(f"Wrote {MODEL_JSONLD.name} and shapes for {build_shapes()} classes.")
