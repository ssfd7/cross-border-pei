"""Run WF3 with an agent, in one of two arms that use the same model.

grounded   The agent follows the procedure in the OKF bundle. It reads only through the bundle's
           attested computations and writes only through its tools, and can look terms up in the
           ontology and the mappings.
control    The agent gets the original procedure text, the bare table definitions and a
           read-only SQL tool. Nothing tells it what a table or column means.

Both start from the seeded Clearance schema and are scored against the answer key.

    python -m xbpei.agent grounded D-001
    python -m xbpei.agent control D-001
"""
import asyncio
import json
import sys
import tempfile

import psycopg
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, TextBlock, create_sdk_mcp_server, query, tool
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import ADMIN_DSN, BUSINESS, CONTROL_DSN, DSN, bundle, ontology, tools
from .execute import finish_run, log_step, plain, run_computation, start_run
from .score import score

MODEL = "claude-opus-5-5"
PROCEDURE = "procedures/wf3-withholding-at-distribution"
MAX_BUDGET_USD = 10.0
LEGACY_SCHEMAS = ("entity_mgmt", "investor_register", "onboarding", "treasury", "documents", "rulebook", "clearance")

SCHEDULE_LINE = {
    "type": "object",
    "properties": {
        "determined_for": {"type": "string", "description": "Investor number of the recipient"},
        "for_component": {"type": "string"},
        "determination_outcome": {"type": "string", "enum": ["cleared", "defaultRate", "held", "notApplicable"]},
        "gross_amount": {"type": "number"},
        "withholding_rate": {"type": "number"},
        "tax_withheld": {"type": "number"},
        "net_amount": {"type": "number"},
        "rate_basis": {"type": "string", "description": "Rule version, certification and reason"},
        "relies_on_clearance": {"type": "string"},
        "supported_by": {"type": "string", "description": "Assessment identifier"},
    },
    "required": ["determined_for", "for_component", "determination_outcome", "gross_amount", "rate_basis"],
}
CONTROL_OUTPUT = {
    "type": "object",
    "properties": {
        "lines": {"type": "array", "items": {
            "type": "object",
            "properties": {"recipient_no": {"type": "string", "description": "Investor number (inv_no) of the party whose income it is"},
                           "component": {"type": "string"},
                           "outcome": {"type": "string", "enum": ["cleared", "defaultRate", "held", "notApplicable"]},
                           "gross_amount": {"type": "number"}, "withholding_rate": {"type": "number"},
                           "tax_withheld": {"type": "number"}, "net_amount": {"type": "number"}, "basis": {"type": "string"}},
            "required": ["recipient_no", "component", "outcome", "gross_amount", "withholding_rate", "tax_withheld", "net_amount", "basis"]}},
        "notes": {"type": "string", "description": "Anything the reviewer must know"},
    },
    "required": ["lines", "notes"],
}


def reply(value) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(value, default=plain, ensure_ascii=False)}]}


def reset_clearance() -> None:
    """Remove what earlier runs wrote, so every run starts from the seeded decisions."""
    with psycopg.connect(ADMIN_DSN) as conn:
        for statement in ("DELETE FROM clearance.withholding_determination", "DELETE FROM clearance.withholding_schedule",
                          "DELETE FROM clearance.missing_fact_finding WHERE finding_id LIKE 'MF-R%'",
                          "DELETE FROM clearance.assessment_fact", "DELETE FROM clearance.obligation_assessment",
                          "DELETE FROM clearance.case WHERE case_id LIKE 'K-R%'"):
            conn.execute(statement)


def grounded_server(run_id: str):
    @tool("find_term", "Find ontology terms by words in their name or definition.", {"text": str})
    async def find_term(args):
        result = ontology.find_term(args["text"])[:8]
        log_step(run_id, "lookup", "ontology/find", [r["term"] for r in result], args, result=result)
        return reply(result)

    @tool("describe_term", "Meaning, steward, status and properties of an ontology term such as xbpei:OwnershipInterest.", {"term": str})
    async def describe_term(args):
        result = ontology.describe_term(args["term"]) or {"known": False, "message": f'{args["term"]} is not a term of the ontology.'}
        log_step(run_id, "lookup", "ontology/describe", [args["term"]], args, result=result)
        return reply(result)

    @tool("mappings_for", "Where instances of an ontology term live in the source systems, or that no system holds it.", {"term": str})
    async def mappings_for(args):
        result = ontology.mappings_for(args["term"])
        log_step(run_id, "lookup", "ontology/mappings", [args["term"]], args, result={k: v for k, v in result.items() if k != "mappings"})
        return reply(result)

    @tool("read_concept", "Read a concept of the knowledge bundle in full: a computation, a tool or a procedure.", {"concept": str})
    async def read_concept(args):
        try:
            concept = bundle.concept(args["concept"])
        except KeyError:
            return reply({"error": f'No concept {args["concept"]} in the bundle.'})
        meta = {k: v for k, v in concept.meta.items() if k not in ("executor", "attester", "generated", "@context")}
        return reply({"concept": concept.id, **meta, "body": concept.body})

    @tool("run_computation", "Run one of the bundle's computations with values for its declared parameters. Returns its rows.",
          {"type": "object", "properties": {"concept": {"type": "string", "description": "For example computations/distribution"},
                                            "parameters": {"type": "object"}}, "required": ["concept", "parameters"]})
    async def computation(args):
        try:
            result = run_computation(args["concept"], args["parameters"], run_id)
        except KeyError:
            result = {"error": f'No concept {args["concept"]} in the bundle.'}
        result.pop("receipt", None)
        return reply(result)

    @tool("read_document", "Read a document from the document folder by its reference, for example DOC-0201.", {"doc_ref": str})
    async def read_document(args):
        return reply(tools.read_document(args["doc_ref"], run_id))

    @tool("open_case", "Open a case.", {"type": "object", "properties": {"case_kind": {"type": "string"}, "concerns_party": {"type": "string"},
                                                                       "concerns_distribution": {"type": "string"}}, "required": ["case_kind"]})
    async def open_case(args):
        return reply(tools.open_case(args["case_kind"], args.get("concerns_party"), args.get("concerns_distribution"), run_id))

    @tool("record_assessment", "Record the evaluation of one rule version for one party and component, with the facts used and any missing.",
          {"type": "object", "properties": {
              "rule_id": {"type": "string"}, "version_label": {"type": "string"}, "subject_party": {"type": "string"},
              "subject_event": {"type": "string"}, "assessment_result": {"type": "string", "enum": ["applicable", "notApplicable", "undetermined"]},
              "reasoning": {"type": "string"}, "facts": {"type": "array", "items": {"type": "string"}, "description": "source_ref values"},
              "gaps": {"type": "array", "items": {"type": "object", "properties": {
                  "unmet_requirement": {"type": "string"}, "about_party": {"type": "string"}, "description": {"type": "string"}},
                  "required": ["unmet_requirement", "description"]}}},
           "required": ["rule_id", "version_label", "subject_party", "subject_event", "assessment_result", "reasoning", "facts"]})
    async def record_assessment(args):
        return reply(tools.record_assessment(args["rule_id"], args["version_label"], args["subject_party"], args["subject_event"],
                                             args["assessment_result"], args["reasoning"], args["facts"], args.get("gaps"), run_id))

    @tool("draft_schedule", "Record a draft withholding schedule. Refused with reasons if it fails the checks.",
          {"type": "object", "properties": {"distribution_id": {"type": "string"}, "determinations": {"type": "array", "items": SCHEDULE_LINE}},
           "required": ["distribution_id", "determinations"]})
    async def draft_schedule(args):
        return reply(tools.draft_schedule(args["distribution_id"], args["determinations"], run_id))

    return create_sdk_mcp_server("clearance", tools=[find_term, describe_term, mappings_for, read_concept, computation, read_document,
                                                     open_case, record_assessment, draft_schedule])


def control_server(run_id: str):
    @tool("run_sql", "Run one read-only SQL query on the firm's Postgres database and return its rows.", {"sql": str})
    async def run_sql(args):
        try:
            with psycopg.connect(CONTROL_DSN, row_factory=dict_row) as conn:
                conn.execute("SET TRANSACTION READ ONLY")
                rows = json.loads(json.dumps(conn.execute(args["sql"]).fetchmany(500), default=plain))
            result = {"rows": rows, "row_count": len(rows)}
        except psycopg.Error as error:
            result = {"error": str(error).strip()}
        log_step(run_id, "sql", executed=args["sql"], result=result.get("rows"), row_count=result.get("row_count"), verdict=result.get("error"))
        return reply(result)

    @tool("read_document", "Read a document from the document folder by its reference, for example DOC-0201.", {"doc_ref": str})
    async def read_document(args):
        return reply(tools.read_document(args["doc_ref"], run_id))

    return create_sdk_mcp_server("firm", tools=[run_sql, read_document])


def grounded_prompt() -> str:
    procedure = bundle.concept(PROCEDURE)
    steps = "\n".join(f'{s["id"]}. [{s["performed_by"]}] {s["title"]}' + (f' Uses: {", ".join(u.strip("/").removesuffix(".md") for u in s["uses"])}.' if s.get("uses") else "")
                      for s in procedure.meta["steps"])
    catalogue = "\n".join(f'- {c.id} ({", ".join(p["name"] + ": " + p["type"] for p in c.meta["parameters"])}): {c.meta["description"]}'
                          for c in bundle.concepts().values() if c.meta["type"] == "Attested Computation")
    return f"""You prepare withholding schedules for a private equity fund's tax team. You carry out an operating procedure from the firm's knowledge bundle; a tax reviewer makes the decision afterwards.

How you work:
- You read data only by running the bundle's computations, and write only through its tools. You cannot write queries. Each computation's note says what its rows mean and what to watch for; read a computation with read_concept before the first time you rely on it.
- The ontology defines what each term means. When a term's meaning matters to a decision, look it up; do not assume. If a term is not in the ontology, or no system holds it, say so plainly and do not answer from something else.
- Cite facts by the source_ref values the computations return. Take rates, thresholds and required facts from the rule versions in force, never from memory.
- Something unknown or undetermined is a result to record, not a gap to fill with a guess.
- Carry out the steps marked [agent] in order. Stop when you reach a step marked [human]. Then write a short hand-over note for the reviewer: the totals, each line that is not cleared and why, and anything the sources disagree on or leave unknown.

# Procedure: {procedure.meta["title"]}

{steps}
{procedure.body}
# Computations in the bundle

{catalogue}
"""


def control_prompt() -> str:
    with psycopg.connect(CONTROL_DSN) as conn:
        columns = conn.execute("""SELECT table_schema, table_name, string_agg(column_name || ' ' || data_type, ', ' ORDER BY ordinal_position)
                                  FROM information_schema.columns WHERE table_schema = ANY(%s) GROUP BY 1, 2 ORDER BY 1, 2""",
                               (list(LEGACY_SCHEMAS),)).fetchall()
    tables = "\n".join(f"- {schema}.{table} ({cols})" for schema, table, cols in columns)
    procedure = (BUSINESS / "clearance-product" / "wf3-withholding-at-distribution.md").read_text()
    return f"""You prepare withholding schedules for a private equity fund's tax team. You carry out the operating procedure below; a tax reviewer makes the decision afterwards.

You can run read-only SQL on the firm's Postgres database and read documents from its document folder. Carry out the procedure up to, but not including, the second review and sign-off. Return the schedule with one line per recipient and component, where the recipient is the party whose income it is, identified by investor number (inv_no), and put anything the reviewer must know in the notes.

# Tables

{tables}

# Operating procedure

{procedure}
"""


async def run(arm: str, distribution_id: str) -> dict:
    reset_clearance()
    run_id = start_run(arm, PROCEDURE, distribution_id, MODEL)
    grounded = arm == "grounded"
    server_name, server = ("clearance", grounded_server(run_id)) if grounded else ("firm", control_server(run_id))
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=grounded_prompt() if grounded else control_prompt(),
        mcp_servers={server_name: server},
        strict_mcp_config=True,
        tools=[],                      # no built-in tools: the agent has only the tools above
        allowed_tools=[f"mcp__{server_name}"],
        setting_sources=[],            # no user or project settings, so the repository's instructions do not leak in
        cwd=tempfile.mkdtemp(),
        max_turns=120,
        max_budget_usd=MAX_BUDGET_USD,
        output_format=None if grounded else {"type": "json_schema", "schema": CONTROL_OUTPUT},
    )
    prompt = f"Run WF3, withholding determination at distribution, for distribution {distribution_id}."
    texts, final = [], None
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        texts.append(block.text)
                        log_step(run_id, "message", result={"text": block.text})
            elif isinstance(message, ResultMessage):
                final = message
    except ClaudeSDKError as error:  # for example a usage limit: record the run as failed, not as a result
        finish_run(run_id, f"failed: {error}")
        return {"run": run_id, "arm": arm, "outcome": f"failed: {error}"}

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        if grounded:
            lines = conn.execute("""SELECT d.determined_for AS recipient_no, d.for_component AS component, d.determination_outcome AS outcome,
                                           d.gross_amount, d.withholding_rate, d.tax_withheld, d.rate_basis
                                    FROM clearance.withholding_determination d
                                    WHERE d.schedule_id = (SELECT max(schedule_id) FROM clearance.withholding_schedule)""").fetchall()
            recorded = conn.execute("SELECT string_agg(reasoning, ' ') AS t FROM clearance.obligation_assessment").fetchone()["t"] or ""
            evidence = " ".join(texts + [recorded] + [l["rate_basis"] or "" for l in lines])
        else:
            output = final.structured_output if final and final.structured_output else {"lines": [], "notes": ""}
            lines = output["lines"]
            evidence = " ".join(texts + [output.get("notes", "")] + [l.get("basis", "") for l in lines])
        result = score(json.loads(json.dumps(lines, default=plain)), evidence)
        conn.execute("""UPDATE runlog.run SET finished_at = now(), outcome = %s, turns = %s, duration_ms = %s, cost_usd = %s, usage = %s,
                        final_text = %s, score = %s WHERE run_id = %s""",
                     (final.subtype if final else "no result", final and final.num_turns, final and final.duration_ms,
                      final and final.total_cost_usd, Jsonb(final.usage if final else None),
                      (final.result if final and final.result else "\n\n".join(texts[-1:])), Jsonb(result), run_id))
    return {"run": run_id, "arm": arm, "outcome": final.subtype if final else None, "turns": final and final.num_turns,
            "seconds": final and round(final.duration_ms / 1000), "cost_usd": final and final.total_cost_usd, "score": result}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run(sys.argv[1], sys.argv[2])), indent=2))
