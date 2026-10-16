"""Measures of what a reviewer or auditor gets from a run, beside the accuracy score.

evidence      Share of schedule lines backed by a recorded assessment whose cited facts all
              resolve to existing rows. Taken from the run log, so it holds for any recorded run.
bad drafts    Faulty drafts from the answer key, put to the checks of the write tool. One the
              checks accept would reach the reviewer. Nothing is written.
term impact   The concepts and procedure steps a change to a term reaches, against a hand-checked list.
term lookup   Whether a lookup answers, reports a missing mapping or reports an unknown term.
consistency   Over the successful runs of an arm: recipients on which every run gave the same rate and tax.

The last four need no agent run. The control arm has no write checks, no recorded evidence and no
links from terms to steps, so it has no result on the first four: that is what the measures show.

    python -m xbpei.measures
"""
import copy
import json

import psycopg
import yaml
from psycopg.rows import dict_row

from . import DSN, GOLD, bundle, ontology
from .score import COMPONENT
from .tools import draft_reasons, resolves


def key() -> dict:
    return yaml.safe_load(GOLD.read_text())


def accepted_draft(conn, run_id: str) -> dict | None:
    """The parameters of the last draft schedule the write tool accepted in a run."""
    row = conn.execute("""SELECT parameters FROM runlog.step WHERE run_id = %s AND concept = 'tools/draft-schedule' AND verdict = 'Written.'
                          ORDER BY seq DESC LIMIT 1""", (run_id,)).fetchone()
    return row and row["parameters"]


def run_lines(conn, run: dict) -> dict[str, dict]:
    """A run's lines for the dividend component, by recipient: from the control's output or the grounded run's accepted draft."""
    if run["arm"] == "control":
        try:
            lines = json.loads(run["final_text"])["lines"]
        except (TypeError, ValueError, KeyError):
            return {}
        return {l["recipient_no"]: l for l in lines if l["component"] == COMPONENT}
    draft = accepted_draft(conn, run["run_id"])
    return {d["determined_for"]: {"outcome": d["determination_outcome"], "withholding_rate": d.get("withholding_rate"), "tax_withheld": d.get("tax_withheld")}
            for d in (draft or {}).get("determinations", []) if d["for_component"] == COMPONENT}


def evidence(conn, run: dict) -> dict:
    """Lines of the whole schedule, and how many rest on an assessment whose facts all resolve."""
    if run["arm"] == "control":
        try:
            lines = len(json.loads(run["final_text"])["lines"])
        except (TypeError, ValueError, KeyError):
            lines = 0
        return {"lines": lines, "lines_with_evidence": 0, "assessments": 0, "facts_cited": 0, "facts_resolved": 0,
                "note": "The basis of each line is free text; nothing in it was checked against the data."}
    draft = accepted_draft(conn, run["run_id"])
    recorded = conn.execute("""SELECT parameters->'facts' AS facts, result->>'assessment' AS assessment FROM runlog.step
                               WHERE run_id = %s AND concept = 'tools/record-assessment' AND verdict = 'Written.'""", (run["run_id"],)).fetchall()
    facts = {r["assessment"]: r["facts"] or [] for r in recorded}
    known = {ref: resolves(conn, ref) for refs in facts.values() for ref in refs}
    backed = [d for d in (draft or {}).get("determinations", [])
              if facts.get(d.get("supported_by")) and all(known[ref] for ref in facts[d["supported_by"]])]
    return {"lines": len((draft or {}).get("determinations", [])), "lines_with_evidence": len(backed), "assessments": len(facts),
            "facts_cited": sum(len(refs) for refs in facts.values()), "facts_resolved": sum(known[ref] for refs in facts.values() for ref in refs)}


def faulty(determinations: list[dict], case: dict) -> list[dict]:
    """The accepted draft with one fault from the answer key put into it, on the dividend component."""
    lines = copy.deepcopy(determinations)
    of = lambda party: next(d for d in lines if d["determined_for"] == party and d["for_component"] == COMPONENT)
    if case["change"] == "duplicate":
        lines.append(dict(of(case["party"])))
    elif case["change"] == "drop":
        lines.remove(of(case["party"]))
    elif case["change"] == "set":
        of(case["party"]).update(case["values"])
    elif case["change"] == "borrow":
        of(case["party"])[case["field"]] = of(case["from"])[case["field"]]
    elif case["change"] == "merge":  # one line for the payee of record at the default rate, in place of the recipients behind it
        merged = [of(p) for p in case["parties"]]
        gross = sum(d["gross_amount"] for d in merged)
        for d in merged:
            lines.remove(d)
        lines.append({"determined_for": case["into"], "for_component": COMPONENT, "determination_outcome": "defaultRate", "gross_amount": gross,
                      "withholding_rate": 30, "tax_withheld": gross * 0.3, "net_amount": gross * 0.7, "rate_basis": "Statutory rate, payee of record"})
    return lines


def bad_drafts(conn) -> dict:
    """Each faulty draft put to the checks of the write tool. Starts from the latest accepted draft, which must itself pass the checks."""
    run = conn.execute("""SELECT s.run_id FROM runlog.step s JOIN runlog.run r ON r.run_id = s.run_id
                          WHERE s.concept = 'tools/draft-schedule' AND s.verdict = 'Written.' AND r.subject = 'D-001'
                          ORDER BY s.at DESC LIMIT 1""").fetchone()
    if run is None:
        return {"cases": [], "note": "No accepted draft is recorded to start from."}
    draft = accepted_draft(conn, run["run_id"])
    if draft_reasons(conn, "WS-TEST", draft["distribution_id"], draft["determinations"]):
        return {"cases": [], "note": f'The accepted draft of {run["run_id"]} does not pass the present checks, because its records have been removed '
                                     "or checks have been added since. A grounded run is needed to start from."}
    cases = []
    for case in key()["faulty_drafts"]:
        reasons = draft_reasons(conn, "WS-TEST", draft["distribution_id"], faulty(draft["determinations"], case))
        cases.append({"id": case["id"], "fault": case["fault"], "control": case["control"], "case": case.get("case"),
                      "caught": bool(reasons), "reasons": reasons})
    return {"from_run": run["run_id"], "cases": cases, "caught": sum(c["caught"] for c in cases), "total": len(cases)}


def term_impact() -> dict:
    cases = []
    for case in key()["term_impact"]:
        got = bundle.affected_by(case["term"])
        steps = sorted({s["step"] for s in got["steps"]})
        cases.append({"term": case["term"], "concepts": got["concepts"], "steps": steps,
                      "as_expected": got["concepts"] == sorted(case["concepts"]) and steps == sorted(case["steps"])})
    return {"cases": cases, "as_expected": sum(c["as_expected"] for c in cases), "total": len(cases)}


def term_lookup() -> dict:
    cases = []
    for case in key()["term_lookup"]:
        found = [{"term": case["ask"]}] if case["ask"].startswith("xbpei:") else ontology.find_term(case["ask"])  # best match first
        mapped = ontology.mappings_for(found[0]["term"]) if found else {"known": False}
        got = "unknown" if not mapped["known"] else "answer" if mapped["mapped"] else "unmapped"
        cases.append({"ask": case["ask"], "expected": case["expected"], "got": got, "as_expected": got == case["expected"]})
    return {"cases": cases, "as_expected": sum(c["as_expected"] for c in cases), "total": len(cases)}


def consistency(conn, runs: list[dict]) -> dict:
    """Per arm, over its successful runs: the recipients on which the runs agree, and the spread of score, turns and cost."""
    out = {}
    for arm in sorted({r["arm"] for r in runs}):
        mine = [r for r in runs if r["arm"] == arm]
        lines = [run_lines(conn, r) for r in mine]
        recipients = sorted({p for l in lines for p in l})
        value = lambda l, p: p in l and (float(l[p].get("withholding_rate") or 0), float(l[p].get("tax_withheld") or 0))
        differ = [p for p in recipients if len({value(l, p) for l in lines}) > 1]
        spread = lambda values: [min(values), max(values)] if values else None
        out[arm] = {"runs": [r["run_id"] for r in mine], "recipients": len(recipients), "recipients_agreed": len(recipients) - len(differ),
                    "recipients_differing": differ, "lines_correct": spread([r["score"]["lines_correct"] for r in mine]),
                    "points": spread([r["score"]["cases_passed"] for r in mine]), "turns": spread([r["turns"] for r in mine if r["turns"]]),
                    "cost_usd": spread([float(r["cost_usd"]) for r in mine if r["cost_usd"] is not None])}
    return out


def report(dsn: str = DSN) -> dict:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        runs = conn.execute("SELECT * FROM runlog.run WHERE arm IN ('grounded', 'control') AND subject = 'D-001' AND model = 'claude-opus-5-5' AND outcome = 'success' AND score IS NOT NULL ORDER BY started_at").fetchall()
        return {"evidence": {r["run_id"]: dict(evidence(conn, r), arm=r["arm"]) for r in runs}, "bad_drafts": bad_drafts(conn),
                "term_impact": term_impact(), "term_lookup": term_lookup(), "consistency": consistency(conn, runs)}


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, default=str, ensure_ascii=False))
