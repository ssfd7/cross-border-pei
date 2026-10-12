"""Review screens over the prototype's data. Only the LookThrough page runs an agent, when a question is asked.

    streamlit run app.py
"""
import asyncio
import html
import json
import re
import textwrap
from datetime import date
from urllib.parse import urlencode

import altair as alt
import pandas as pd
import psycopg
import streamlit as st
import yaml
from psycopg.rows import dict_row

from xbpei import BUSINESS, GOLD, REVIEWER_DSN, ROOT, bundle, measures, ontology
from xbpei.ask import ask
from xbpei.execute import run_computation
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


# Overview -------------------------------------------------------------------

TRACE_TERMS = ["xbpei:votingPercentage", "xbpei:JurisdictionFact", "xbpei:OwnershipInterest", "xbpei:TaxCertification", "xbpei:Clearance"]
EXAMPLE_VALUES = {"on_date": "2026-10-30", "distribution_id": "D-001", "fund_code": "AGF1", "company_id": "E-003", "jurisdiction": "US", "party_no": "I-001",
                  "component_id": "D-001-A", "from_date": "2024-01-01", "to_date": "2026-10-30"}
BAND_CSS = """<style>
.band {font-size:12px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; color:#52514e; margin:2px 0 6px 0}
.down {text-align:center; color:#7a7872; font-size:20px; line-height:1; margin:2px 0 4px 0}
.side {text-align:center; color:#7a7872; font-size:26px; line-height:1; margin-top:96px}
.sidenote {text-align:center; color:#7a7872; font-size:11px; line-height:1.25; margin-top:4px}
</style>"""


def go_to(page: str) -> None:
    st.session_state["page"] = page


@st.cache_data(ttl=120)
def headline() -> dict:
    """The results on record, read from the run log and recomputed by the measures."""
    found = measures.report(REVIEWER_DSN)
    runs = [r for r in all_runs() if r["score"]]
    right = lambda arm: [r["score"]["lines_correct"] == r["score"]["lines_expected"] for r in runs if r["arm"] == arm]
    asked = [r["score"] for r in runs if r["arm"] == "lookthrough"]
    grounded = [e for e in found["evidence"].values() if e["arm"] == "grounded"]
    return {"grounded": right("grounded"), "control": right("control"), "drafts": found["bad_drafts"],
            "points": (sum(a["passed"] for a in asked), sum(a["total"] for a in asked)), "evidence": grounded[-1] if grounded else None}


def questions() -> dict[str, str]:
    """The competency questions of LookThrough, from its requirements."""
    text = (BUSINESS / "lookthrough-product" / "lookthrough-business-product.md").read_text()
    return dict(re.findall(r"^\| (CQ\d) \| ([^|]+?) \|$", text, re.M))  # the two-column table of questions, not the objectives


GITHUB = "https://github.com/ssfd7/cross-border-pei/blob/main/"
IN_BUNDLE = "solution/bundle/"
MARK = '<mark style="background:#fff2cc;color:#0b0b0b;font-weight:700;padding:0 3px;border-radius:3px">'
PRE = ('<pre style="font:12px/1.55 ui-monospace,Menlo,monospace;background:#f6f6f4;color:#0b0b0b;padding:10px 12px;border-radius:8px;'
       'overflow-x:auto;white-space:pre-wrap;word-break:break-word;margin:0 0 8px 0">')
REQUIREMENTS = {"clearance": "business/clearance-product/clearance-business-product.md",
                "wf3": "business/clearance-product/wf3-withholding-at-distribution.md",
                "lookthrough": "business/lookthrough-product/lookthrough-business-product.md"}
ONTOLOGY_FILES = ["model/xb-pei-model.ttl", "model/xb-pei-governance.ttl", "model/README.md"]
KINDS_OF_FILE = (("business/", "Requirement"), ("model/", "Ontology"), (IN_BUNDLE + "procedures/", "Bundle procedure"),
                 (IN_BUNDLE + "computations/", "Bundle computation"), (IN_BUNDLE + "tools/", "Bundle tool"), (IN_BUNDLE + "references/", "Bundle mapping"))


READABLE = ("business/", "model/", IN_BUNDLE, "solution/shapes/", "solution/gold/")


def file_kind(path: str) -> str:
    return next((name for prefix, name in KINDS_OF_FILE if path.startswith(prefix)), "File")


def render_file(path: str) -> None:
    st.markdown(f"`{path}` · [the same file on GitHub]({GITHUB}{path})")
    if path.startswith("business/"):  # a requirement is read as a document; the other files are shown as written
        st.markdown((ROOT / path).read_text())
    else:
        st.code((ROOT / path).read_text(), language={"yaml": "yaml", "ttl": "turtle"}.get(path.rsplit(".", 1)[-1], "markdown"))


def file_link(label: str, path: str) -> str:
    """A link that opens a requirement, ontology or bundle file over the page it is on. For use in HTML."""
    here = {k: st.query_params[k] for k in st.query_params if k != "file"}
    return f'<a href="?{urlencode({**here, "file": path})}" target="_self" title="Open {html.escape(path)}">{label}</a>'


def close_file() -> None:
    st.session_state.pop("open_file", None)


@st.dialog("Source file", width="large", on_dismiss=close_file)
def show_file(path: str) -> None:
    st.caption(file_kind(path))
    render_file(path)


def open_linked_file() -> None:
    """Open the file a link named, if it is one of the project's own documents. It stays open until it is dismissed."""
    path = st.query_params.get("file")
    if path:
        del st.query_params["file"]
        target = (ROOT / path).resolve()
        if path.startswith(READABLE) and target.is_file() and target.is_relative_to(ROOT) and target.suffix in (".md", ".yaml", ".ttl"):
            st.session_state["open_file"] = path
    if st.session_state.get("open_file"):
        show_file(st.session_state["open_file"])


def source_files(paths: list[str], key: str) -> None:
    """A reader for the requirements, ontology and bundle files behind what a page shows, each with its place on GitHub."""
    with st.expander("All the requirements, ontology and bundle files behind this"):
        render_file(st.selectbox("File", list(dict.fromkeys(paths)), key=key, format_func=lambda f: f"{file_kind(f)}: {f.removeprefix(IN_BUNDLE)}"))


def marked(text: str, names: set[str]) -> str:
    """Text as HTML with the given names highlighted and anything in backticks set as code."""
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))
    for name in sorted(names, key=len, reverse=True):
        out = re.sub(rf"(?<![\w>])({re.escape(name)})(?!\w)", MARK + r"\1</mark>", out)
    return out


def trace(term: str) -> None:
    """One term followed from the work that needs it to the rows that hold it. Everything shown is read from the bundle, the ontology and the data."""
    described, reach = ontology.describe_term(term), bundle.affected_by(term)
    concepts = [bundle.concept(c) for c in reach["concepts"]]
    by_runtime = {runtime: [c for c in concepts if c.meta.get("runtime") == runtime] for runtime in ("postgres", "ladybug")}
    places = {"postgres": list(dict.fromkeys(place for c in by_runtime["postgres"] for place in bundle.in_tables(term, c))),
              "ladybug": bundle.in_graph(term) if by_runtime["ladybug"] else []}
    # What carries the term in the data: the last part of each mapped table, column or property name.
    # For an attribute that is a column or a property, not the table that holds it.
    whole = described["kind"] == "class"
    names = {name.split(".")[-1] for runtime, side in places.items() for place in side for name in re.findall(r"`([\w.]+)`", place)
             if whole or name.count(".") == (2 if runtime == "postgres" else 1)}
    spoken = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", term.split(":")[1]).lower()
    asked = questions()
    st.markdown(BAND_CSS, unsafe_allow_html=True)

    business, to_left, core, to_right, mapping = st.columns([1.25, 0.2, 1, 0.2, 1.25])
    to_left.markdown('<div class="side">&larr;</div><div class="sidenote">means</div>', unsafe_allow_html=True)
    to_right.markdown('<div class="side">&rarr;</div><div class="sidenote">maps to</div>', unsafe_allow_html=True)
    with business:
        st.markdown('<div class="band">1 · Business: the work that needs it</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f'<b>Clearance workflow</b> · {file_link("operating procedure WF3", REQUIREMENTS["wf3"])} · '
                        f'{file_link("as a bundle procedure", IN_BUNDLE + "procedures/wf3-withholding-at-distribution.md")}', unsafe_allow_html=True)
            for step in reach["steps"]:
                through = ", ".join(file_link(f"<code>{c.split('/')[1]}</code>", f"{IN_BUNDLE}{c}.md") for c in step["through"])
                st.markdown(f'Step {step["step"]}: {html.escape(step["title"])}<br><small>reads {MARK}{spoken}</mark> through {through}</small>', unsafe_allow_html=True)
            if not reach["steps"]:
                st.caption("No step of WF3 uses this term.")
        with st.container(border=True):
            st.markdown(f'<b>LookThrough analytics</b> · {file_link("competency questions", REQUIREMENTS["lookthrough"])}', unsafe_allow_html=True)
            supported = sorted({q for c in concepts for q in c.meta.get("supports", []) if q in asked})
            for q in supported:
                st.write(f"{q}: {asked[q]}")
            if not supported:
                st.caption("No LookThrough question uses this term.")
    with core:
        st.markdown('<div class="band">2 · Ontology: what it means</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f'<div style="font-size:24px;font-weight:700;line-height:1.3;margin-bottom:6px">{MARK}{spoken}</mark></div>'
                        + file_link(f"<code>{term}</code>", "model/xb-pei-model.ttl") + " · " + file_link("stewardship", "model/xb-pei-governance.ttl"),
                        unsafe_allow_html=True)
            st.write(described.get("definition") or "No definition recorded.")
            st.caption(f'{described["kind"].capitalize()}' + (" of " + ", ".join(f"`{c}`" for c in described["of"]) if described.get("of") else "")
                       + f'. Steward: {described.get("steward", "none")}. Status: {described.get("status", "none")}.')
            if described.get("sources"):
                st.caption("Source: " + "; ".join(described["sources"]))
    with mapping:
        st.markdown('<div class="band">3 · Mapping: where it lives</div>', unsafe_allow_html=True)
        held_in = sorted({m["source"] for m in ontology.mappings_for(term).get("mappings", [])})
        mapping_links = {"postgres": ", ".join(file_link(source, f"{IN_BUNDLE}references/mappings/{source}.yaml") for source in held_in),
                         "ladybug": file_link("graph mapping", IN_BUNDLE + "references/mappings/graph/ladybug.yaml")}
        for runtime, title in (("postgres", "<b>Postgres</b> · the emulated source systems"), ("ladybug", "<b>LadybugDB</b> · the graph projection")):
            with st.container(border=True):
                st.markdown(f'{title}<br><small>mapping files: {mapping_links[runtime] or "none"}</small>', unsafe_allow_html=True)
                if places[runtime]:
                    st.markdown("<ul style='margin:0;padding-left:18px'>" + "".join(f"<li>{marked(place, names)}</li>" for place in places[runtime]) + "</ul>",
                                unsafe_allow_html=True)
                else:
                    st.caption("No computation reads the term here.")

    st.markdown('<div class="down">&darr;</div><div class="band">4 · Attested query and the rows it returns</div>', unsafe_allow_html=True)
    stem = re.split(r"(?<=[a-z])(?=[A-Z])", term.split(":")[1])[0].lower()  # voting, for votingPercentage
    left, right = st.columns(2)
    for column, runtime in ((left, "postgres"), (right, "ladybug")):
        with column.container(border=True):
            if not by_runtime[runtime]:
                st.caption("No computation on this side reads the term.")
                continue
            c = by_runtime[runtime][0]
            st.markdown(f'<b>{html.escape(c.meta["title"])}</b> · {file_link(f"<code>{c.id}</code>", f"{IN_BUNDLE}{c.id}.md")} · '
                        f'supports {", ".join(c.meta.get("supports", []))}', unsafe_allow_html=True)
            code = c.computation.strip().splitlines()
            st.html(PRE + marked("\n".join(code[:12] + (["…"] if len(code) > 12 else [])), names).replace("<code>", "").replace("</code>", "") + "</pre>")
            values = {p["name"]: EXAMPLE_VALUES[p["name"]] for p in c.meta["parameters"]}
            result = run_computation(c.id, values)
            st.caption(f'Run with {values}: {result.get("row_count")} rows, attested: {result.get("attested")}. The first three:')
            found = result.get("rows", [])  # who the row is about, then its figures, which is where a percentage or an amount shows
            if found:
                figures = [k for k, v in found[0].items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
                keep = list(dict.fromkeys(list(found[0])[:2] + figures + list(found[0])[2:]))[:5]
                frame = pd.DataFrame([{k: (", ".join(map(str, row[k])) if isinstance(row[k], list) else row[k]) for k in keep} for row in found[:3]])
                carrying = [k for k in keep if described["kind"] != "class" and (k in names or stem in k.lower())]
                styled = frame.style.format({k: "{:g}" for k in figures if k in keep})
                st.dataframe(styled.set_properties(subset=carrying, **{"background-color": "#fff2cc", "color": "#0b0b0b", "font-weight": "700"}),
                             hide_index=True, width="stretch")
    st.caption("An agent supplies only the parameter values. It cannot change the query, and each run is checked against the bundle before its rows are used. "
               "The highlight follows the term: its name, the columns and properties mapped to it, those names in the queries, and its values in the rows.")
    sources = {m["source"] for m in ontology.mappings_for(term).get("mappings", [])}
    supported = {q for c in concepts for q in c.meta.get("supports", []) if q in asked}
    source_files(([REQUIREMENTS["clearance"], REQUIREMENTS["wf3"]] if reach["steps"] else []) + ([REQUIREMENTS["lookthrough"]] if supported else [])
                 + ONTOLOGY_FILES + ([IN_BUNDLE + "procedures/wf3-withholding-at-distribution.md"] if reach["steps"] else [])
                 + [f"{IN_BUNDLE}{c.id}.md" for c in concepts] + [f"{IN_BUNDLE}references/mappings/{source}.yaml" for source in sorted(sources)]
                 + ([IN_BUNDLE + "references/mappings/graph/ladybug.yaml"] if by_runtime["ladybug"] else []), key="overview-files")


def overview_page() -> None:
    st.header("One ontology grounding two products")
    st.write("Every business term has one meaning, kept in an ontology with a steward and a status. A semantic layer, packaged as an OKF bundle, ties each "
             "meaning to where its data lives in Postgres and in the graph, and to the procedure steps and questions that need it. An agent reads and "
             "writes only through that layer, so every draft it prepares and every answer it gives can be traced back to a defined term and a source row.")
    h = headline()
    tiles = st.columns(5)
    tiles[0].metric("Grounded agent, correct schedule", f'{sum(h["grounded"])} of {len(h["grounded"])} runs')
    tiles[1].metric("Ungrounded agent, correct schedule", f'{sum(h["control"])} of {len(h["control"])} runs')
    tiles[2].metric("Faulty drafts refused", f'{h["drafts"].get("caught", "?")} of {h["drafts"].get("total", "?")}')
    tiles[3].metric("LookThrough points", f'{h["points"][0]} of {h["points"][1]}')
    if h["evidence"]:
        tiles[4].metric("Schedule lines with evidence", f'{h["evidence"]["lines_with_evidence"]} of {h["evidence"]["lines"]}')
    st.caption("Read from the run log just now. Synthetic data, illustrative rules, and a handful of runs: these show what happened, not rates.")

    st.subheader("One term, from the business question to the rows")
    if st.session_state.get("term") not in TRACE_TERMS:
        st.session_state["term"] = st.query_params.get("term") if st.query_params.get("term") in TRACE_TERMS else TRACE_TERMS[0]
    term = st.selectbox("Follow a term", TRACE_TERMS, key="term", format_func=lambda t: f'{ontology.describe_term(t).get("label") or t}  ({t})')
    st.query_params["term"] = term
    trace(term)

    st.subheader("See it work")
    left, right, _ = st.columns([1, 1, 2])
    left.button("Open the Clearance workflow", on_click=go_to, args=("Clearance workflow",), help="A procedure run by an agent and signed by a person")
    right.button("Open LookThrough analytics", on_click=go_to, args=("LookThrough analytics",), help="Ask a question and see what the answer rests on")

    st.subheader("How the pieces fit")
    st.image("diagrams/okf-extension-overview.png")


# Clearance ------------------------------------------------------------------

STRIP_CSS = """<style>
.wf {display:flex; flex-wrap:wrap; gap:6px 4px; align-items:stretch; margin:4px 0 14px 0; font-family:inherit}
.wf .lane {flex-basis:100%; font-size:12px; font-weight:600; color:#52514e; margin-top:6px; letter-spacing:.02em}
.wf .step {width:150px; padding:7px 9px; border:1px solid #c9c7c0; border-radius:8px; background:#fcfcfb; color:#0b0b0b; font-size:12px; line-height:1.3}
.wf .step b {display:block; font-size:11px; color:#52514e; font-weight:600; margin-bottom:2px}
.wf .person {border:2px solid #0b0b0b}
.wf .done {background:#eef3ee}
.wf .now {background:#fff2cc; box-shadow:0 0 0 2px #0b0b0b}
.wf .out {color:#7a7872; border-style:dashed}
.wf .arrow {align-self:center; color:#7a7872; font-size:14px}
</style>"""


def workflow_strip(status: str) -> None:
    """The steps of WF3 as the bundle's procedure gives them, with who performs each and where the schedule stands."""
    steps = bundle.concept("procedures/wf3-withholding-at-distribution").meta["steps"]
    reached = {"draft": 10, "signed": 11}.get(status, 10)  # the step the schedule is waiting at
    parts, lane = [], None
    for step in steps:
        person = step["performed_by"] != "agent"
        if step["performed_by"] != lane:
            lane = step["performed_by"]
            parts.append(f'<div class="lane">{"Person" if person else "Agent"}: steps {step["id"]} to {[s["id"] for s in steps if s["performed_by"] == lane][-1]}</div>')
        elif parts:
            parts.append('<div class="arrow">&rarr;</div>')
        state = "done" if step["id"] < reached else "now" if step["id"] == reached and step["id"] == 10 else "out" if step["id"] > 10 else ""
        tag = "done" if state == "done" else "waiting here" if state == "now" else "outside the prototype" if state == "out" else ""
        parts.append(f'<div class="step {"person" if person else ""} {state}"><b>{step["id"]} &middot; {"person" if person else "agent"}'
                     f'{" &middot; " + tag if tag else ""}</b>{html.escape(textwrap.shorten(step["title"], 78, placeholder="…"))}</div>')
    st.markdown(STRIP_CSS + f'<div class="wf">{"".join(parts)}</div>', unsafe_allow_html=True)
    procedure = IN_BUNDLE + "procedures/wf3-withholding-at-distribution.md"
    st.markdown(f'<small>Generated from the {file_link("WF3 procedure in the bundle", procedure)}, which is what the agent follows, and which carries out the '
                f'{file_link("WF3 operating procedure", REQUIREMENTS["wf3"])} of the {file_link("Clearance requirements", REQUIREMENTS["clearance"])}. '
                "The agent reads through attested computations and writes drafts through checked tools; a heavy border marks the steps only a person "
                "performs.</small>", unsafe_allow_html=True)
    used = lambda step: [u.strip("/") for u in step.get("uses", [])]
    with st.expander("What each step uses in the bundle"):
        st.markdown("<ol style='padding-left:20px'>" + "".join(
            f'<li>{html.escape(step["title"])} <small>({"person" if step["performed_by"] != "agent" else "agent"})</small><br><small>'
            + (", ".join(file_link(f"<code>{u.removesuffix('.md')}</code>", IN_BUNDLE + u) for u in used(step)) or "nothing from the bundle") + "</small></li>"
            for step in steps) + "</ol>", unsafe_allow_html=True)
    source_files([REQUIREMENTS["wf3"], REQUIREMENTS["clearance"], IN_BUNDLE + "procedures/wf3-withholding-at-distribution.md"]
                 + [IN_BUNDLE + u for step in steps for u in used(step)] + ["solution/shapes/controls.ttl"], key="workflow-files")


def clearance_page() -> None:
    st.header("Clearance workflow: withholding at distribution")
    schedules = rows("SELECT * FROM clearance.withholding_schedule ORDER BY schedule_id DESC")
    if not schedules:
        st.info("No schedule has been drafted. Run the grounded agent: `python -m xbpei.agent grounded D-001`.")
        return
    schedule = st.selectbox("Schedule", schedules, format_func=lambda s: f'{s["schedule_id"]} for {s["schedule_for"]} ({s["schedule_status"]})')
    workflow_strip(schedule["schedule_status"])
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

def benchmark_page() -> None:
    st.header("Benchmark")
    runs = [r for r in all_runs() if r["score"] and r["arm"] in ("grounded", "control")]
    if not runs:
        st.info("No scored runs are recorded.")
        return
    st.warning("Cost is an estimate reported by the SDK. Scores are as stored when each run finished.")
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
    with psycopg.connect(REVIEWER_DSN, row_factory=dict_row) as conn:
        by_run = {f'{r["arm"]} {r["run_id"]}': measures.run_lines(conn, r) for r in runs}
    table([{"recipient": f'{l["recipient"]} {names[l["recipient"]]}', "gross": l["gross"], "expected rate": l["rate"], "expected tax": l["tax"],
            **{label: (f'{float(lines[l["recipient"]].get("withholding_rate") or 0):g}% / {float(lines[l["recipient"]].get("tax_withheld") or 0):,.2f}'
                       if l["recipient"] in lines else "no line") for label, lines in by_run.items()}} for l in key])

    st.header("What a reviewer gets")
    st.write("These measures do not test whether an agent reached the right figures. They test what is left for a reviewer or an auditor to rely on. "
             "The control arm has no write checks, no recorded evidence and no links from terms to steps, so it has no result on the first four.")
    found = measures.report(REVIEWER_DSN)

    st.subheader("Evidence behind the schedule")
    table([{"run": run, "arm": e["arm"], "lines": e["lines"], "lines with resolvable evidence": e["lines_with_evidence"], "assessments": e["assessments"],
            "facts cited": e["facts_cited"], "facts that resolve to a row": e["facts_resolved"]} for run, e in found["evidence"].items()])

    st.subheader("Faulty drafts put to the write tool")
    drafts = found["bad_drafts"]
    if drafts["cases"]:
        st.write(f'{drafts["caught"]} of {drafts["total"]} refused. Each is one change to the accepted draft of {drafts["from_run"]}. '
                 "A draft that is accepted would reach the reviewer.")
        table([{"id": c["id"], "fault": c["fault"], "control": c["control"], "result": "refused" if c["caught"] else "accepted",
                "reason given": c["reasons"][0] if c["reasons"] else ""} for c in drafts["cases"]])
    else:
        st.info(drafts["note"])

    st.subheader("What a change to a term reaches")
    table([{"term": c["term"], "computations and tools": ", ".join(c["concepts"]), "WF3 steps": ", ".join(str(s) for s in c["steps"]),
            "matches the hand-checked list": "yes" if c["as_expected"] else "no"} for c in found["term_impact"]["cases"]])

    st.subheader("Terms that cannot be answered")
    table([{"asked for": c["ask"], "expected": c["expected"], "lookup says": c["got"]} for c in found["term_lookup"]["cases"]])

    st.subheader("Consistency over repeated runs")
    table([{"arm": arm, "runs": len(c["runs"]), "recipients on which all runs agree": f'{c["recipients_agreed"]} of {c["recipients"]}',
            "differing": ", ".join(c["recipients_differing"]), "lines correct": spread(c["lines_correct"]), "points": spread(c["points"]),
            "turns": spread(c["turns"]), "estimated cost USD": spread(c["cost_usd"])} for arm, c in found["consistency"].items()])


def spread(values) -> str:
    """A lowest and highest value as one figure or a range."""
    return "" if not values else f"{values[0]:g}" if values[0] == values[1] else f"{values[0]:g} to {values[1]:g}"


# LookThrough ----------------------------------------------------------------

SERIES = {"Economic %": "#2a78d6", "Voting %": "#eb6834"}   # slots 1 and 2 of the validated categorical palette
RELATIONS = {"holds": "Holdings", "jurisdictionFact": "Jurisdiction facts", "payment": "Payments"}
DEFAULT_RELATIONS = {"CQ2": ["holds", "jurisdictionFact"], "CQ3": ["payment"]}
SHAPES = {"FundVehicle": "round-rectangle", "SPV": "diamond", "PortfolioCompany": "hexagon", "LegalEntity": "ellipse",
          "NaturalPerson": "ellipse", "Jurisdiction": "round-tag"}
GRAPH_HTML = """<div id="cy" style="width:100%;height:@@height@@px;background:#fcfcfb;border:1px solid #dddbd4;border-radius:8px"></div>
<div id="tip" style="position:absolute;display:none;background:#0b0b0b;color:#fff;font:12px sans-serif;padding:4px 7px;border-radius:4px;pointer-events:none"></div>
<script src="https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
<script>
const shapes = @@shapes@@, dim = @@dim@@;
const cy = cytoscape({container: document.getElementById('cy'), elements: @@elements@@, wheelSensitivity: 0.2,
  layout: {name: @@layout@@, padding: 24, animate: false, nodeDimensionsIncludeLabels: true},
  style: [
    {selector: 'node', style: {'label': 'data(label)', 'font-size': 11, 'color': '#0b0b0b', 'text-wrap': 'wrap', 'text-max-width': 110,
      'text-valign': 'bottom', 'text-margin-y': 4, 'width': 34, 'height': 34, 'border-width': 1, 'border-color': '#666',
      'background-color': '#FFF2CC', 'shape': e => shapes[e.data('kind')] || 'ellipse', 'opacity': e => dim && !e.data('named') ? 0.45 : 1}},
    {selector: 'node[kind = "Jurisdiction"]', style: {'background-color': '#E4F1E3', 'width': 34, 'height': 22, 'text-valign': 'center', 'text-margin-y': 0}},
    {selector: 'node[kind = "NaturalPerson"]', style: {'border-style': 'double', 'border-width': 3}},
    {selector: 'node[?named]', style: {'border-width': 4, 'border-color': '#0b0b0b', 'font-weight': 'bold'}},
    {selector: 'edge', style: {'label': 'data(label)', 'font-size': 8, 'color': '#52514e', 'text-background-color': '#fcfcfb', 'text-background-opacity': 1,
      'text-background-padding': 1, 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.8, 'width': 1.2,
      'line-color': '#8a8882', 'target-arrow-color': '#8a8882', 'opacity': e => dim && !e.data('named') ? 0.5 : 1}},
    {selector: 'edge[relation = "jurisdictionFact"]', style: {'line-style': 'dotted'}},
    {selector: 'edge[relation = "payment"]', style: {'line-style': 'dashed', 'line-color': '#2a78d6', 'target-arrow-color': '#2a78d6', 'width': 1.6}},
    {selector: 'edge[?named]', style: {'width': 3}}]});
const tip = document.getElementById('tip');
cy.on('mouseover', 'node, edge', e => { tip.textContent = e.target.data('tip'); tip.style.display = 'block'; });
cy.on('mousemove', e => { tip.style.left = (e.renderedPosition.x + 14) + 'px'; tip.style.top = (e.renderedPosition.y + 14) + 'px'; });
cy.on('mouseout', 'node, edge', () => { tip.style.display = 'none'; });
</script>"""


def structure(on_date: date) -> list[dict]:
    """The structure as edges, from the bundle's attested graph computation."""
    return run_computation("computations/structure-graph", {"on_date": on_date.isoformat()}).get("rows", [])


def named_in(output: dict | None, edges: list[dict]) -> tuple[set[str], set[str]]:
    """The graph nodes and payments an answer names, by any identifier a source system gives them."""
    text = json.dumps(output or {})
    alias = {}
    for e in edges:
        for node, refs in ((e["source"], e["source_refs"]), (e["target"], e["target_refs"])):
            alias[node] = node
            for ref in refs or []:
                alias[ref.split(":")[-1]] = node
    tokens = set(re.findall(r"\b(?:I|E|CP)-\d+\b", text))
    return {alias[t] for t in tokens if t in alias}, set(re.findall(r"\bP-\d+\b", text))


def draw_graph(edges: list[dict], relations: list[str], nodes_named: set[str], payments_named: set[str], only_named: bool) -> None:
    shown = [e for e in edges if e["relation"] in relations
             and (not only_named or e["label"].split()[0] in payments_named
                  or (e["source"] in nodes_named and (e["target"] in nodes_named or e["relation"] == "jurisdictionFact")))]
    if not shown:
        st.info("Nothing on record for these relations on this date.")
        return
    # Tiers for the layout: what holds nothing is at the bottom, and each holder sits above what it holds.
    held = {}
    for e in shown:
        if e["relation"] == "holds":
            held.setdefault(e["source"], set()).add(e["target"])

    def tier(node: str, path: tuple = ()) -> int:
        return 0 if node in path else 1 + max((tier(t, path + (node,)) for t in held.get(node, ())), default=0)

    kinds = {}
    for e in shown:
        kinds.update({e["source"]: (e["source_name"], e["source_kind"]), e["target"]: (e["target_name"], e["target_kind"])})
    tiers = {}
    for node, (_, kind) in sorted(kinds.items()):
        tiers.setdefault(-1 if kind == "Jurisdiction" else tier(node), []).append(node)
    position, y, per_row, width = {}, 0, 6, 900
    for level in sorted(tiers, reverse=True):  # a wide tier wraps into staggered rows; jurisdictions form the last tier
        members = tiers[level]
        for start in range(0, len(members), per_row):
            row = members[start:start + per_row]
            for k, node in enumerate(row):
                position[node] = {"x": width * (k + 1) / (len(row) + 1) + (40 if (start // per_row) % 2 else 0), "y": y}
            y += 105
        y += 25

    elements = []
    for node, (name, kind) in kinds.items():
        elements.append({"data": {"id": node, "label": node if kind == "Jurisdiction" else f"{name}\n{node}", "kind": kind,
                                  "named": node in nodes_named, "tip": f"{name or node} ({kind})"}, "position": position[node]})
    for e in shown:
        label = e["label"]
        if e["relation"] == "holds":  # economic percentage of this one interest, and the capacity where it is a nominee's
            pct, capacity = label.split("% ")
            label = f"{float(pct):g}%" + (" nominee" if capacity == "nominee" else "")
        elements.append({"data": {"id": f'{e["relation"]}:{e["source_ref"]}:{e["target"]}', "source": e["source"], "target": e["target"],
                                  "label": label, "relation": e["relation"], "named": e["label"].split()[0] in payments_named,
                                  "tip": f'{RELATIONS[e["relation"]]}: {e["label"]} ({e["source_ref"]})'}})
    height = 640
    page = GRAPH_HTML
    for key, value in {"height": height, "shapes": SHAPES, "dim": bool(nodes_named or payments_named), "elements": elements,
                       "layout": "preset" if "holds" in relations else "cose"}.items():
        page = page.replace(f"@@{key}@@", json.dumps(value).replace("</", "<\\/"))  # names from the data cannot close the script
    st.iframe(page, height=height + 10)
    st.caption("Shapes: rounded box fund vehicle, diamond SPV, hexagon portfolio company, circle other legal entity, double-ringed circle natural person, "
               "tag jurisdiction. Lines: solid holding (labelled with the percentage of that one interest), dotted jurisdiction fact, dashed payment. "
               "A heavy outline marks what the answer names. From `computations/structure-graph`, attested; the graph library loads from the network.")


def facts_frame(output: dict) -> pd.DataFrame:
    return pd.DataFrame(output["facts"] or [], columns=["subject", "attribute", "value", "source_ref"])


def analytics(cq: str | None, output: dict, names: dict[str, str]) -> None:
    """The figures of an answer, in the form that suits the question."""
    facts = facts_frame(output)
    if facts.empty:
        return
    if cq == "CQ1":
        wide = facts[facts["attribute"].isin(["economicPercentage", "votingPercentage"])].copy()
        wide["value"] = pd.to_numeric(wide["value"].astype(str).str.rstrip("%"), errors="coerce")
        wide["measure"] = wide["attribute"].map({"economicPercentage": "Economic %", "votingPercentage": "Voting %"})
        wide["investor"] = wide["subject"].map(lambda s: f"{names.get(s, s)} ({s})")
        order = wide[wide["measure"] == "Economic %"].sort_values("value", ascending=False)["investor"].tolist()
        chart = alt.Chart(wide).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("investor:N", sort=order, title=None, axis=alt.Axis(labelLimit=320), scale=alt.Scale(paddingInner=0.4)),
            yOffset=alt.YOffset("measure:N", sort=list(SERIES), scale=alt.Scale(paddingInner=0.2)),
            x=alt.X("value:Q", title="Effective holding in the company, percent"),
            color=alt.Color("measure:N", scale=alt.Scale(domain=list(SERIES), range=list(SERIES.values())), legend=alt.Legend(title=None, orient="top")),
            tooltip=[alt.Tooltip("investor:N"), alt.Tooltip("measure:N"), alt.Tooltip("value:Q", format=".2f")],
        ).properties(height=max(200, 36 * len(order)))
        st.altair_chart(chart, width="stretch")
        st.caption("Each investor's holding multiplied through every tier of the chain. Voting and economic percentages differ where a share class carries more votes.")
    elif cq == "CQ2":
        st.dataframe(facts.groupby(["subject", "attribute"])["value"].agg(lambda v: ", ".join(sorted(set(v)))).unstack(fill_value="not recorded")
                     .rename(index=lambda s: f"{names.get(s, s)} ({s})"), width="stretch")
    elif cq in ("CQ3", "CQ6"):
        attribute = "crossing" if cq == "CQ3" else "kind"
        counts = facts[facts["attribute"] == attribute]["value"].value_counts()
        for column, (value, count) in zip(st.columns(max(len(counts), 1)), counts.items()):
            column.metric(value, count)
    elif cq == "CQ5":
        missing = facts[facts["attribute"] == "unmetRequirement"]
        left, right = st.columns(2)
        left.metric("Parties with a missing fact", missing["subject"].nunique())
        right.metric("Findings", len(missing))
    else:  # a question outside the answer key: one figure per subject is drawn as a bar, anything else stays a table
        numbers = pd.to_numeric(facts["value"].astype(str).str.rstrip("%"), errors="coerce")
        if len(facts) >= 3 and numbers.notna().all() and facts["subject"].is_unique:
            one = facts.assign(value=numbers, subject=facts["subject"].map(lambda s: f"{names.get(s, s)} ({s})"))
            chart = alt.Chart(one).mark_bar(cornerRadiusEnd=4, color=SERIES["Economic %"]).encode(
                y=alt.Y("subject:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320), scale=alt.Scale(paddingInner=0.45)),
                x=alt.X("value:Q", title="Value given in the answer"),
                tooltip=[alt.Tooltip("subject:N"), alt.Tooltip("attribute:N"), alt.Tooltip("value:Q")],
            ).properties(height=max(160, 26 * len(one)))
            st.altair_chart(chart, width="stretch")
            st.caption("One bar per subject of the answer. What each figure measures is in the table below and in the tooltip.")
    with st.expander("Table of the answer's figures", expanded=cq != "CQ1"):
        table(facts.fillna("").to_dict("records"), max_rows=16)


def lookthrough_page() -> None:
    st.header("LookThrough analytics")
    st.write("Ask a question about the structure, its jurisdictions, payments or the obligations on record. An agent answers it live: it looks terms up in "
             "the ontology and runs the bundle's attested computations, and writes no queries of its own. A question outside the ontology, or about a "
             "term no source holds, is refused.")
    main, panel = st.columns([3.1, 1.25], gap="large")

    with panel:
        st.subheader("Ask")
        samples = yaml.safe_load(GOLD.read_text())["lookthrough_questions"]
        picked = st.selectbox("From the answer key", [None] + samples, format_func=lambda q: "Write your own" if q is None else f'{q["cq"]}: {q["text"][:48]}…')
        text = st.text_area("Question", value=picked["text"] if picked else "", height=130, placeholder="Which investors have indirect exposure to Borealis Logistik?")
        if st.button("Ask", type="primary", disabled=not text.strip()):
            with st.spinner("The agent is looking terms up and running computations. This takes about 10 to 30 seconds."):
                result = asyncio.run(ask(picked["id"] if picked and text == picked["text"] else text.strip()))
            st.session_state["lookthrough_run"] = result["run"]
            st.rerun()
        runs = [r for r in all_runs() if r["arm"] == "lookthrough"][::-1]
        st.subheader("Asked so far")
        if not runs:
            st.caption("Nothing yet.")
            return
        by_id = {r["run_id"]: r for r in runs}
        if st.session_state.get("lookthrough_run") not in by_id:
            st.session_state["lookthrough_run"] = st.query_params.get("run") if st.query_params.get("run") in by_id else runs[0]["run_id"]
        run = by_id[st.radio("Asked so far", list(by_id), key="lookthrough_run", label_visibility="collapsed",
                             format_func=lambda i: f'{by_id[i]["procedure"] or "live"} · {textwrap.shorten(by_id[i]["subject"] or "", 70, placeholder="…")}')]

    st.query_params["run"] = run["run_id"]
    with main:
        st.subheader(run["subject"])
        st.caption(f'{run["run_id"]}, asked {run["started_at"]:%d %b %Y %H:%M}: {run["turns"] or "?"} turns, {round((run["duration_ms"] or 0) / 1000)} seconds, '
                   f'estimated USD {float(run["cost_usd"] or 0):.2f}')
        try:
            output = json.loads(run["final_text"])
        except (TypeError, ValueError):
            output = None
            st.error(f'The agent gave no answer. Outcome: {run["outcome"] or "the run did not finish"}.')
        if output:
            (st.warning if output["status"] == "refused" else st.success)("Refused" if output["status"] == "refused" else "Answered")
            st.write(output["answer"])

        st.subheader("Where the answer sits in the structure")
        left, middle, right = st.columns([1, 2, 1.4])
        on_date = left.date_input("On date", date(2026, 10, 30))
        relations = middle.multiselect("Show", list(RELATIONS), default=DEFAULT_RELATIONS.get(run["procedure"], ["holds"]), format_func=RELATIONS.get)
        edges = structure(on_date)
        nodes_named, payments_named = named_in(output, edges)
        nodes_named |= {e[end] for e in edges if e["relation"] == "payment" and e["label"].split()[0] in payments_named for end in ("source", "target")}
        only_named = right.checkbox("Only what the answer names", value=run["procedure"] == "CQ2", disabled=not nodes_named,
                                    key=f'only-{run["run_id"]}')
        draw_graph(edges, relations, nodes_named, payments_named, only_named)

        if output:
            if output["facts"]:
                st.subheader("Figures")
                names = {key: e[f"{end}_name"] for e in edges for end in ("source", "target")
                         for key in [e[end]] + [ref.split(":")[-1] for ref in e[f"{end}_refs"] or []]}
                analytics(run["procedure"], output, names)
            for label, title in (("unknown", "Not recorded in the sources"), ("conflicts", "Where the sources disagree")):
                if output[label]:
                    st.subheader(title)
                    for item in output[label]:
                        st.write("- " + item)
            if run["score"]:
                st.subheader(f'Against the answer key: {run["score"]["passed"]} of {run["score"]["total"]}')
                table([{"point": p, "result": "pass" if ok else "fail"} for p, ok in run["score"]["points"].items()])
        st.subheader("What the answer rests on")
        steps = rows("SELECT * FROM runlog.step WHERE run_id = %s AND kind IN ('computation', 'lookup') ORDER BY seq", (run["run_id"],))
        if steps:
            table([{"seq": s["seq"], "kind": s["kind"], "concept": s["concept"], "parameters": json.dumps(s["parameters"]), "rows": s["row_count"],
                    "attested": s["attested"], "ontology terms": ", ".join(s["terms"] or [])} for s in steps])
        else:
            st.caption("The run recorded no lookup and no computation.")
        ran = list(dict.fromkeys(s["concept"] for s in steps if s["kind"] == "computation"))
        st.markdown("<small>Open: " + " · ".join([file_link("LookThrough requirements", REQUIREMENTS["lookthrough"])]
                    + [file_link(f"<code>{c}</code>", f"{IN_BUNDLE}{c}.md") for c in ran]) + "</small>", unsafe_allow_html=True)
        source_files([REQUIREMENTS["lookthrough"], "solution/gold/answer-key.yaml"] + [f"{IN_BUNDLE}{c}.md" for c in ran]
                     + [IN_BUNDLE + "references/mappings/graph/ladybug.yaml"] + ONTOLOGY_FILES, key="lookthrough-files")


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
    if described.get("sources"):
        st.caption("Source: " + "; ".join(described["sources"]))
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


PAGES = {"Overview": overview_page, "Clearance workflow": clearance_page, "LookThrough analytics": lookthrough_page, "Run replay": replay_page, "Benchmark": benchmark_page, "Ontology": ontology_page}
st.sidebar.title("PEI prototype")
st.sidebar.caption("Synthetic data. Rules are illustrative.")
if st.session_state.get("page") not in PAGES:  # a link can open a page: ?page=LookThrough analytics
    st.session_state["page"] = st.query_params.get("page") if st.query_params.get("page") in PAGES else "Overview"
chosen = st.sidebar.radio("Page", list(PAGES), key="page")
st.query_params["page"] = chosen  # kept in the address, so a link to a file returns to the page it was on
open_linked_file()
PAGES[chosen]()
