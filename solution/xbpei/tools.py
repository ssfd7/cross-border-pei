"""The tools described in the bundle's tools/ folder: the only ways an agent writes.

Each tool checks its input, adds rows to the Clearance schema and records the step in the run log.
A refused call writes nothing and returns the reasons, so the caller can correct and try again.
"""
from datetime import date
from decimal import Decimal

import psycopg
from pyshacl import validate
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from . import DOCUMENTS, DSN, SHAPES, XBPEI, bundle
from .execute import log_step
from .ontology import mapping_files

AGENT = "agent:xbpei-clearance"


def refused(run_id, concept_id: str, parameters: dict, reasons: list[str]) -> dict:
    log_step(run_id, "tool", concept_id, bundle.concept(concept_id).meta.get("writes"), parameters, verdict="Refused: " + " ".join(reasons))
    return {"written": False, "reasons": reasons}


def done(run_id, concept_id: str, parameters: dict, result: dict) -> dict:
    log_step(run_id, "tool", concept_id, bundle.concept(concept_id).meta.get("writes"), parameters, result=result, verdict="Written.")
    return {"written": True, **result}


def next_id(conn, table: str, column: str, prefix: str) -> str:
    count = conn.execute(f"SELECT count(*) FROM clearance.{table} WHERE {column} LIKE %s", (prefix + "%",)).fetchone()[0]
    return f"{prefix}{count + 1:03d}"


def source_row(conn, source_ref: str) -> dict | None:
    """The row a schema.table:key reference names, found by the key the mappings declare. None if it does not resolve."""
    try:
        table, key = source_ref.split(":", 1)
        source, name = table.split(".")
        columns = next(m["key"] for f in mapping_files() if f["source"] == source for m in f["mappings"] if m["table"] == name)
    except (ValueError, StopIteration):
        return None
    columns = columns if isinstance(columns, list) else [columns]
    values = key.split("/", len(columns) - 1) if len(columns) > 1 else [key]
    if len(values) != len(columns):
        return None
    where = " AND ".join(f"{c}::text = %s" for c in columns)
    cursor = conn.execute(f"SELECT * FROM {table} WHERE {where}", values)
    row = cursor.fetchone()
    return None if row is None else dict(zip([d.name for d in cursor.description], row)) if not isinstance(row, dict) else row


def resolves(conn, source_ref: str) -> bool:
    return source_row(conn, source_ref) is not None


def read_document(doc_ref: str, run_id: str | None = None) -> dict:
    with psycopg.connect(DSN) as conn:
        row = conn.execute("SELECT title, doc_type, doc_dt, file_path FROM documents.document WHERE doc_ref = %s", (doc_ref,)).fetchone()
    if row is None:
        result = {"found": False, "message": f"No document {doc_ref} in the index."}
    elif row[3] is None:
        result = {"found": True, "title": row[0], "digitised": False, "message": "The document is indexed but not digitised; its content is unknown."}
    else:
        result = {"found": True, "title": row[0], "digitised": True, "text": (DOCUMENTS / row[3]).read_text(),
                  "source_ref": f"documents.document:{doc_ref}"}
    log_step(run_id, "tool", "tools/read-document", parameters={"doc_ref": doc_ref}, result={k: v for k, v in result.items() if k != "text"})
    return result


def open_case(case_kind: str, concerns_party: str | None = None, concerns_distribution: str | None = None, run_id: str | None = None) -> dict:
    parameters = {"case_kind": case_kind, "concerns_party": concerns_party, "concerns_distribution": concerns_distribution}
    if case_kind not in ("onboarding", "renewal", "change", "distribution"):
        return refused(run_id, "tools/open-case", parameters, ["case_kind must be onboarding, renewal, change or distribution."])
    with psycopg.connect(DSN) as conn:
        case_id = next_id(conn, "case", "case_id", "K-R")
        conn.execute("INSERT INTO clearance.case (case_id, case_kind, concerns_party, concerns_distribution, opened_on) VALUES (%s, %s, %s, %s, %s)",
                     (case_id, case_kind, concerns_party, concerns_distribution, date.today()))
    return done(run_id, "tools/open-case", parameters, {"case": case_id})


def record_assessment(rule_id: str, version_label: str, subject_party: str, subject_event: str, assessment_result: str,
                      reasoning: str, facts: list[str], gaps: list[dict] | None = None, run_id: str | None = None) -> dict:
    gaps = gaps or []
    parameters = {"rule_id": rule_id, "version_label": version_label, "subject_party": subject_party, "subject_event": subject_event,
                  "assessment_result": assessment_result, "reasoning": reasoning, "facts": facts, "gaps": gaps}
    with psycopg.connect(DSN) as conn:
        reasons = []
        if assessment_result not in ("applicable", "notApplicable", "undetermined"):
            reasons.append("assessment_result must be applicable, notApplicable or undetermined.")
        if not resolves(conn, f"rulebook.rule_version:{rule_id}/{version_label}"):
            reasons.append(f"No rule version {rule_id} {version_label}.")
        if not resolves(conn, f"investor_register.investor:{subject_party}"):
            reasons.append(f"No party {subject_party}.")
        reasons += [f"Fact {ref} does not resolve to a row." for ref in facts if not resolves(conn, ref)]
        reasons += [f"No fact requirement {g.get('unmet_requirement')}." for g in gaps
                    if not resolves(conn, f"rulebook.fact_requirement:{g.get('unmet_requirement')}")]
        if assessment_result == "undetermined" and not gaps:
            reasons.append("An undetermined assessment must name at least one missing fact.")
        if not facts and not gaps:
            reasons.append("An assessment must cite the facts it used or the facts it lacks.")
        if reasons:
            return refused(run_id, "tools/record-assessment", parameters, reasons)
        assessment_id = next_id(conn, "obligation_assessment", "assessment_id", "A-R")
        conn.execute("""INSERT INTO clearance.obligation_assessment (assessment_id, evaluates_rule, evaluates_version, subject_party,
                        subject_event, assessed_on, assessment_result, reasoning) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                     (assessment_id, rule_id, version_label, subject_party, subject_event, date.today(), assessment_result, reasoning))
        for ref in dict.fromkeys(facts):
            conn.execute("INSERT INTO clearance.assessment_fact (assessment_id, source_ref) VALUES (%s, %s)", (assessment_id, ref))
        findings = []
        for gap in gaps:
            findings.append(next_id(conn, "missing_fact_finding", "finding_id", "MF-R"))
            conn.execute("""INSERT INTO clearance.missing_fact_finding (finding_id, assessment_id, unmet_requirement, about_party, description, recorded_on)
                            VALUES (%s, %s, %s, %s, %s, %s)""",
                         (findings[-1], assessment_id, gap["unmet_requirement"], gap.get("about_party"), gap["description"], date.today()))
    return done(run_id, "tools/record-assessment", parameters, {"assessment": assessment_id, "findings": findings})


def schedule_graph(schedule: str, distribution_id: str, determinations: list[dict]) -> Graph:
    """A draft schedule as instances of the ontology, for the shapes to test."""
    g, node = Graph(), lambda kind, key: URIRef(f"urn:xbpei:{kind}:{key}")
    s = node("schedule", schedule)
    g.add((s, RDF.type, XBPEI.WithholdingSchedule))
    g.add((s, XBPEI.scheduleStatus, Literal("draft")))
    for prop, target, cls in ((XBPEI.scheduleFor, node("distribution", distribution_id), XBPEI.DistributionEvent),
                              (XBPEI.preparedBy, node("actor", AGENT), XBPEI.Party)):
        g.add((s, prop, target))
        g.add((target, RDF.type, cls))
    links = {"determined_for": (XBPEI.determinedFor, "party", XBPEI.Party), "for_component": (XBPEI.forComponent, "component", XBPEI.DistributionComponent),
             "relies_on_clearance": (XBPEI.reliesOnClearance, "clearance", XBPEI.Clearance),
             "supported_by": (XBPEI.supportedBy, "assessment", XBPEI.ObligationAssessment)}
    numbers = {"gross_amount": XBPEI.grossAmount, "withholding_rate": XBPEI.withholdingRate, "tax_withheld": XBPEI.taxWithheld, "net_amount": XBPEI.netAmount}
    for i, d in enumerate(determinations):
        n = node("determination", f"{schedule}-{i + 1:02d}")
        g.add((s, XBPEI.includes, n))
        g.add((n, RDF.type, XBPEI.WithholdingDetermination))
        g.add((n, XBPEI.determinationOutcome, Literal(d.get("determination_outcome"))))
        if d.get("rate_basis"):
            g.add((n, XBPEI.rateBasis, Literal(d["rate_basis"])))
        for key, (prop, kind, cls) in links.items():
            if d.get(key):
                g.add((n, prop, node(kind, d[key])))
                g.add((node(kind, d[key]), RDF.type, cls))
        for key, prop in numbers.items():
            if d.get(key) is not None:
                g.add((n, prop, Literal(Decimal(str(d[key])), datatype=XSD.decimal)))
    return g


def shape_violations(g: Graph) -> list[str]:
    shapes = Graph().parse(SHAPES / "generated.ttl").parse(SHAPES / "controls.ttl")
    conforms, report, _ = validate(g, shacl_graph=shapes)
    if conforms:
        return []
    rows = report.query("""PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?focus ?path ?message WHERE { ?r a sh:ValidationResult ; sh:focusNode ?focus .
        OPTIONAL { ?r sh:resultPath ?path } OPTIONAL { ?r sh:resultMessage ?message } }""")
    return sorted(f"{str(r.focus).rsplit(':', 1)[-1]}{' ' + str(r.path).rsplit('#', 1)[-1] if r.path else ''}: {r.message}" for r in rows)


def draft_schedule(distribution_id: str, determinations: list[dict], run_id: str | None = None) -> dict:
    parameters = {"distribution_id": distribution_id, "determinations": determinations}
    with psycopg.connect(DSN) as conn:
        components = dict(conn.execute("SELECT comp_id, gross_amt FROM treasury.distribution_component WHERE dist_id = %s", (distribution_id,)).fetchall())
        if not components:
            return refused(run_id, "tools/draft-schedule", parameters, [f"No distribution {distribution_id}."])
        schedule_id = next_id(conn, "withholding_schedule", "schedule_id", "WS-R")
        reasons = shape_violations(schedule_graph(schedule_id, distribution_id, determinations))
        for d in determinations:
            line = f"{d.get('determined_for')} {d.get('for_component')}"
            if d.get("for_component") not in components:
                reasons.append(f"{line}: the component is not part of {distribution_id}.")
            for key, table in (("determined_for", "investor_register.investor"), ("relies_on_clearance", "clearance.clearance"),
                               ("supported_by", "clearance.obligation_assessment")):
                if d.get(key) and not resolves(conn, f"{table}:{d[key]}"):
                    reasons.append(f"{line}: {key} {d[key]} does not resolve to a row.")
            if not d.get("rate_basis"):
                reasons.append(f"{line}: no rate basis.")
        for component, gross in components.items():
            total = sum(Decimal(str(d.get("gross_amount") or 0)) for d in determinations if d.get("for_component") == component)
            if total != gross:
                reasons.append(f"{component}: gross amounts sum to {total}, the distribution gives {gross}. A recipient is missing, repeated or misstated.")
        if reasons:
            return refused(run_id, "tools/draft-schedule", parameters, reasons)
        conn.execute("INSERT INTO clearance.withholding_schedule (schedule_id, schedule_for, schedule_status, prepared_by) VALUES (%s, %s, 'draft', %s)",
                     (schedule_id, distribution_id, AGENT))
        for i, d in enumerate(determinations):
            conn.execute("""INSERT INTO clearance.withholding_determination (determination_id, schedule_id, determined_for, for_component,
                            determination_outcome, gross_amount, withholding_rate, tax_withheld, net_amount, rate_basis, relies_on_clearance,
                            supported_by, decided_on) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                         (f"{schedule_id}-{i + 1:02d}", schedule_id, d["determined_for"], d["for_component"], d["determination_outcome"],
                          d["gross_amount"], d.get("withholding_rate"), d.get("tax_withheld"), d.get("net_amount"), d["rate_basis"],
                          d.get("relies_on_clearance"), d.get("supported_by"), date.today()))
    return done(run_id, "tools/draft-schedule", parameters, {"schedule": schedule_id, "status": "draft", "determinations": len(determinations)})
