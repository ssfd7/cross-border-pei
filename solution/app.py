"""Review screens over the prototype's data. Nothing here runs an agent.

    streamlit run app.py
"""
import json

import pandas as pd
import psycopg
import streamlit as st
import yaml
from psycopg.rows import dict_row

from xbpei import GOLD, REVIEWER_DSN, bundle, ontology
from xbpei.tools import source_row

st.set_page_config(page_title="PEI Clearance and LookThrough prototype", layout="wide")


def rows(sql: str, params=None) -> list[dict]:
    with psycopg.connect(REVIEWER_DSN, row_factory=dict_row) as conn:
        return conn.execute(sql, params).fetchall()


MONEY = ("gross", "tax", "net", "distribution_gross", "schedule_gross", "expected tax", "tax total", "tax error")


def table(data: list[dict], max_rows: int = 30) -> None:
    """A table tall enough to show its rows without scrolling, up to max_rows, with money columns formatted."""
    frame = pd.DataFrame(data)
    money = {c: st.column_config.NumberColumn(format="accounting") for c in frame.columns if c in MONEY}
    for column in money:
        frame[column] = frame[column].astype(float)
    st.dataframe(frame, hide_index=True, width="stretch", column_config=money, height=38 + 35 * min(len(frame), max_rows))


# Clearance ------------------------------------------------------------------

def clearance_page() -> None:
    st.header("Clearance: withholding schedule")
    schedules = rows("SELECT * FROM clearance.withholding_schedule ORDER BY schedule_id DESC")
    if not schedules:
        st.info("No schedule has been drafted. Run the grounded agent: `python -m xbpei.agent grounded D-001`.")
        return
    schedule = st.selectbox("Schedule", schedules, format_func=lambda s: f'{s["schedule_id"]} for {s["schedule_for"]} ({s["schedule_status"]})')
    dist = rows("SELECT record_dt, pay_dt, gross_amt, ccy FROM treasury.distribution WHERE dist_id = %s", (schedule["schedule_for"],))[0]
    st.write(f'Distribution **{schedule["schedule_for"]}**: record date {dist["record_dt"]}, payment date {dist["pay_dt"]}, '
             f'{dist["ccy"]} {dist["gross_amt"]:,.2f}. Prepared by `{schedule["prepared_by"]}`. Status: **{schedule["schedule_status"]}**'
             + (f', signed off by `{schedule["signed_off_by"]}` on {schedule["signed_off_on"]}.' if schedule["signed_off_by"] else "."))

    lines = rows("""SELECT d.determination_id, d.for_component AS component, d.determined_for AS recipient, i.display_name AS name,
                           d.determination_outcome AS outcome, d.gross_amount AS gross, d.withholding_rate AS rate, d.tax_withheld AS tax,
                           d.net_amount AS net, d.relies_on_clearance AS clearance, d.supported_by AS assessment, d.rate_basis AS basis
                    FROM clearance.withholding_determination d JOIN investor_register.investor i ON i.inv_no = d.determined_for
                    WHERE d.schedule_id = %s ORDER BY d.for_component, d.determined_for""", (schedule["schedule_id"],))
    totals = rows("""SELECT c.comp_id AS component, c.income_cd AS income, c.gross_amt AS distribution_gross, sum(d.gross_amount) AS schedule_gross,
                            sum(d.tax_withheld) AS tax, sum(d.net_amount) AS net, c.gross_amt = sum(d.gross_amount) AS reconciles
                     FROM treasury.distribution_component c JOIN clearance.withholding_determination d ON d.for_component = c.comp_id
                     WHERE d.schedule_id = %s GROUP BY c.comp_id, c.income_cd, c.gross_amt ORDER BY 1""", (schedule["schedule_id"],))
    st.subheader("Reconciliation to the distribution")
    table(totals)

    st.subheader("Lines")
    only_review = st.checkbox("Show only lines for review: reduced rates, defaults and holds", value=False)
    shown = [l for l in lines if not only_review or l["outcome"] in ("defaultRate", "held") or (l["outcome"] == "cleared" and float(l["rate"] or 0) < 30)]
    table([{k: v for k, v in l.items() if k != "determination_id"} for l in shown])

    st.subheader("Evidence behind a line")
    line = st.selectbox("Line", shown, format_func=lambda l: f'{l["component"]}  {l["recipient"]} {l["name"]}: {l["outcome"]} {l["rate"]}%')
    if line:
        assessments = rows("""SELECT assessment_id, evaluates_rule || ' ' || evaluates_version AS rule_version, assessment_result AS result, reasoning
                              FROM clearance.obligation_assessment WHERE subject_party = %s AND subject_event = %s ORDER BY assessment_id""",
                           (line["recipient"], line["component"]))
        st.write(f'**Basis:** {line["basis"]}')
        for a in assessments:
            marker = " (supports this line)" if a["assessment_id"] == line["assessment"] else ""
            with st.expander(f'{a["assessment_id"]}: {a["rule_version"]} is {a["result"]}{marker}', expanded=bool(marker)):
                st.write(a["reasoning"])
                gaps = rows("SELECT finding_id, unmet_requirement, about_party, description FROM clearance.missing_fact_finding WHERE assessment_id = %s", (a["assessment_id"],))
                if gaps:
                    st.write("Missing facts:")
                    table(gaps)
                facts = rows("SELECT source_ref FROM clearance.assessment_fact WHERE assessment_id = %s ORDER BY 1", (a["assessment_id"],))
                st.write(f"Facts cited: {len(facts)}")
                with psycopg.connect(REVIEWER_DSN, row_factory=dict_row) as conn:
                    for f in facts:
                        row = source_row(conn, f["source_ref"])
                        st.caption(f["source_ref"])
                        st.json(json.loads(json.dumps(row, default=str)) if row else {"unresolved": True}, expanded=False)

    st.subheader("Second review and sign-off")
    if schedule["schedule_status"] != "draft":
        st.success(f'Signed off by {schedule["signed_off_by"]} on {schedule["signed_off_on"]}.')
        return
    st.write("Signing is done by a person, under the reviewer database role. The reviewer must not be the preparer.")
    reviewer = st.selectbox("Reviewer", ["human:STAFF-02", "human:STAFF-03", schedule["prepared_by"]])
    if st.button("Sign off schedule"):
        try:
            with psycopg.connect(REVIEWER_DSN) as conn:
                conn.execute("""UPDATE clearance.withholding_schedule SET schedule_status = 'signed', signed_off_by = %s, signed_off_on = current_date
                                WHERE schedule_id = %s AND schedule_status = 'draft'""", (reviewer, schedule["schedule_id"]))
            st.rerun()
        except psycopg.errors.CheckViolation:
            st.error("Refused by the database: the reviewer who signs off a schedule must not be its preparer (control C3.5).")


# Run replay -----------------------------------------------------------------

def all_runs() -> list[dict]:
    return rows("SELECT * FROM runlog.run ORDER BY started_at")


def run_label(r: dict) -> str:
    return f'{r["run_id"]}  {r["arm"]}  {r["outcome"] or "no outcome"}'


def step_text(step: dict) -> str:
    """The start of a query the agent wrote, or of what it said."""
    text = step["executed"] or (step["result"].get("text", "") if isinstance(step["result"], dict) else "")
    return " ".join(text.split())[:70]


def replay_page() -> None:
    st.header("Run replay")
    runs = all_runs()
    if not runs:
        st.info("No runs are recorded.")
        return
    st.write("Every step an agent took, as recorded in the run log. A grounded step names the bundle concept it used and the ontology terms it concerns; "
             "a control step is a query the agent wrote itself.")
    columns = st.columns(2)
    defaults = [next((i for i, r in enumerate(runs) if r["arm"] == arm and r["outcome"] == "success"), 0) for arm in ("control", "grounded")]
    for column, default, key in zip(columns, defaults, ("left", "right")):
        with column:
            run = st.selectbox("Run", runs, index=default, format_func=run_label, key=key)
            st.caption(f'{run["turns"] or "?"} turns, {round((run["duration_ms"] or 0) / 1000)} seconds, estimated USD {run["cost_usd"] or 0}')
            steps = rows("SELECT * FROM runlog.step WHERE run_id = %s ORDER BY seq", (run["run_id"],))
            table([{"seq": s["seq"], "kind": s["kind"], "what": s["concept"] or step_text(s), "rows": s["row_count"], "attested": s["attested"]}
                   for s in steps], max_rows=8)
            if not steps:
                continue
            step = st.selectbox("Step", steps, format_func=lambda s: f'{s["seq"]} {s["kind"]} {s["concept"] or ""}', key=key + "-step")
            if step["terms"]:
                st.write("Ontology terms: " + ", ".join(f"`{t}`" for t in step["terms"]))
            if step["verdict"]:
                st.write(f'Verdict: {step["verdict"]}')
            if step["parameters"]:
                st.caption("Parameters")
                st.json(step["parameters"], expanded=False)
            if step["executed"]:
                st.caption("Executed")
                st.code(step["executed"], language="sql")
            if isinstance(step["result"], list) and step["result"]:
                st.caption("Result")
                table(step["result"], max_rows=6)
            elif step["result"]:
                st.caption("Result")
                st.json(step["result"], expanded=step["kind"] == "message")


# Benchmark ------------------------------------------------------------------

def run_lines(run: dict) -> dict[str, dict]:
    """A run's lines for the dividend component, by recipient: from the control's output or the grounded run's accepted draft."""
    if run["arm"] == "control":
        try:
            lines = json.loads(run["final_text"])["lines"]
        except (TypeError, ValueError, KeyError):
            return {}
        return {l["recipient_no"]: l for l in lines if l["component"] == "D-001-A"}
    drafts = rows("SELECT parameters FROM runlog.step WHERE run_id = %s AND concept = 'tools/draft-schedule' AND verdict = 'Written.' ORDER BY seq DESC LIMIT 1",
                  (run["run_id"],))
    if not drafts:
        return {}
    return {d["determined_for"]: {"outcome": d["determination_outcome"], "withholding_rate": d.get("withholding_rate"), "tax_withheld": d.get("tax_withheld")}
            for d in drafts[0]["parameters"]["determinations"] if d["for_component"] == "D-001-A"}


def benchmark_page() -> None:
    st.header("Benchmark")
    runs = [r for r in all_runs() if r["score"]]
    if not runs:
        st.info("No scored runs are recorded.")
        return
    st.warning("Each arm has been run once. One run shows that a setup works; it says nothing about consistency. Cost is an estimate reported by the SDK. "
               "Scores are as stored when each run finished.")
    table([{"run": r["run_id"], "arm": r["arm"], "lines correct": f'{r["score"]["lines_correct"]} of {r["score"]["lines_expected"]}',
            "points": f'{r["score"]["cases_passed"]} of {r["score"]["cases_total"]}', "tax total": r["score"]["tax_total"],
            "tax error": r["score"]["tax_error"], "turns": r["turns"], "seconds": round((r["duration_ms"] or 0) / 1000),
            "estimated cost USD": float(r["cost_usd"] or 0)} for r in runs])

    st.subheader("Case by case")
    points = sorted(runs[0]["score"]["cases"])
    table([{"point": p, **{f'{r["arm"]} {r["run_id"]}': "pass" if r["score"]["cases"].get(p) else "fail" for r in runs}} for p in points])

    st.subheader("Schedule for D-001-A against the answer key")
    key = yaml.safe_load(GOLD.read_text())["schedule_d001_a"]["lines"]
    names = {r["inv_no"]: r["display_name"] for r in rows("SELECT inv_no, display_name FROM investor_register.investor")}
    by_run = {f'{r["arm"]} {r["run_id"]}': run_lines(r) for r in runs}
    table([{"recipient": f'{l["recipient"]} {names[l["recipient"]]}', "gross": l["gross"], "expected rate": l["rate"], "expected tax": l["tax"],
            **{label: (f'{float(lines[l["recipient"]].get("withholding_rate") or 0):g}% / {float(lines[l["recipient"]].get("tax_withheld") or 0):,.2f}'
                       if l["recipient"] in lines else "no line") for label, lines in by_run.items()}} for l in key])


# Ontology -------------------------------------------------------------------

def ontology_page() -> None:
    st.header("Ontology")
    st.write("What a term means, who stewards it, where its instances live, and which procedure steps depend on it.")
    text = st.text_input("Find a term", "ownership interest")
    found = ontology.find_term(text) if text.strip() else []
    if not found:
        st.info("No term of the ontology matches. A question about it is out of scope and is not answered from the data.")
        return
    term = st.selectbox("Term", [f["term"] for f in found], format_func=lambda t: f'{t}  ({next(f["kind"] for f in found if f["term"] == t)})')
    described = ontology.describe_term(term)
    st.subheader(described.get("label") or term)
    st.write(described.get("definition") or "No definition recorded.")
    if described.get("scope_note"):
        st.caption("Scope: " + described["scope_note"])
    st.write(f'Steward: **{described.get("steward", "none")}**. Status: **{described.get("status", "none")}**. Kind: {described["kind"]}.')
    for label in ("kinds_of", "of", "range", "properties"):
        if described.get(label):
            value = described[label]
            st.write(f'{label.replace("_", " ").capitalize()}: ' + (", ".join(f"`{v}`" for v in value) if isinstance(value, list) else f"`{value}`"))

    st.subheader("Where its instances live")
    mapped = ontology.mappings_for(term)
    if not mapped["mapped"]:
        st.warning(mapped["message"])
    else:
        table([{"table": m["table"], "key": str(m["key"]), "system of record": str(m["system_of_record"]), "restricted to": m.get("where", ""),
                "for": m.get("of", m.get("term", "")), "scope": " ".join(str(m.get("scope", "")).split())} for m in mapped["mappings"]])
        with st.expander("Full mapping entries"):
            st.json(json.loads(json.dumps(mapped["mappings"], default=str)), expanded=False)

    st.subheader("What depends on it")
    affected = bundle.affected_by(term)
    if not affected["concepts"]:
        st.write("No computation or tool in the bundle reads or writes this term.")
    else:
        st.write("Read or written by: " + ", ".join(f"`{c}`" for c in affected["concepts"]))
        table([{"procedure": s["procedure"], "step": s["id"] if "id" in s else s["step"], "title": s["title"], "through": ", ".join(s["through"])}
               for s in affected["steps"]])

    st.subheader("Stewardship of the whole model")
    g = ontology.graph()
    status = {}
    for subject, steward in g.subject_objects(ontology.XBPEI.steward):
        key = (str(steward), str(g.value(subject, ontology.XBPEI.termStatus)))
        status[key] = status.get(key, 0) + 1
    table([{"steward": s, "status": t, "terms": n} for (s, t), n in sorted(status.items())])


PAGES = {"Clearance": clearance_page, "Run replay": replay_page, "Benchmark": benchmark_page, "Ontology": ontology_page}
st.sidebar.title("PEI prototype")
st.sidebar.caption("Synthetic data. Rules are illustrative.")
PAGES[st.sidebar.radio("Page", list(PAGES))]()
