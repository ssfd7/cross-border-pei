"""Answer a LookThrough question with an agent that only reads.

The agent has the same bundle as the Clearance agent, without the write tools: it looks terms up
in the ontology and the mappings and runs the bundle's attested computations. It writes no
queries and changes nothing. A question about a term that is not in the ontology, or that no
source holds, is refused.

    python -m xbpei.ask Q1                      a question of the answer key, scored against it
    python -m xbpei.ask "Which payments ..."    any other question, not scored
"""
import asyncio
import json
import sys
import tempfile

import psycopg
import yaml
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, TextBlock, query
from psycopg.types.json import Jsonb

from . import DSN, GOLD
from .agent import MODEL, catalogue, grounded_server
from .execute import finish_run, log_step, start_run
from .score import score_answer

MAX_BUDGET_USD = 2.0
ANSWER = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["answered", "refused"], "description": "refused if the question cannot be answered from the ontology and the data"},
        "answer": {"type": "string", "description": "The answer in plain words, or why the question is refused"},
        "facts": {"type": "array", "description": "The figures of the answer, one per item", "items": {
            "type": "object",
            "properties": {"subject": {"type": "string", "description": "Identifier of the party, entity or payment"},
                           "attribute": {"type": "string"}, "value": {"type": "string"},
                           "source_ref": {"type": "string", "description": "A source_ref returned by a computation"}},
            "required": ["subject", "attribute", "value"]}},
        "unknown": {"type": "array", "items": {"type": "string"}, "description": "What the sources do not record and the answer therefore leaves open"},
        "conflicts": {"type": "array", "items": {"type": "string"}, "description": "Where the sources disagree"},
    },
    "required": ["status", "answer", "facts", "unknown", "conflicts"],
}


def prompt() -> str:
    return f"""You answer questions about a private equity fund's structure, payments and jurisdictions for its tax and finance teams.

How you work:
- You read data only by running the computations of the firm's knowledge bundle. You cannot write queries. Each computation's note says what its rows mean and what to watch for; read a computation with read_concept before the first time you rely on it.
- The ontology defines what each term means. Find the terms the question is about before you answer. If a term is not in the ontology, the question is out of scope: refuse and say so. If a term is in the ontology and no source system holds it, refuse and name the missing mapping. Do not answer either from something else.
- Something the sources do not record is unknown, not absent. Report it as unknown. Where the sources disagree, report both figures and which is the system of record.
- Take every figure from the rows a computation returned, and cite its source_ref where one is given.

# Computations in the bundle

{catalogue()}
"""


def gold_question(question_id: str) -> dict | None:
    return next((q for q in yaml.safe_load(GOLD.read_text())["lookthrough_questions"] if q["id"] == question_id), None)


async def ask(text: str) -> dict:
    question = gold_question(text) or {"text": text}
    run_id = start_run("lookthrough", question.get("cq"), question["text"], MODEL)
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=prompt(),
        mcp_servers={"lookthrough": grounded_server(run_id, "lookthrough", writes=False)},
        strict_mcp_config=True,
        tools=[],
        allowed_tools=["mcp__lookthrough"],
        setting_sources=[],
        cwd=tempfile.mkdtemp(),
        max_turns=40,
        max_budget_usd=MAX_BUDGET_USD,
        output_format={"type": "json_schema", "schema": ANSWER},
    )
    asked = question["text"] + (f'\n\nLay out the facts of the answer like this: {question["report"]}' if question.get("report") else "")
    final = None
    try:
        async for message in query(prompt=asked, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        log_step(run_id, "message", result={"text": block.text})
            elif isinstance(message, ResultMessage):
                final = message
    except ClaudeSDKError as error:
        finish_run(run_id, f"failed: {error}")
        return {"run": run_id, "outcome": f"failed: {error}"}
    output = final.structured_output if final and final.structured_output else None
    result = score_answer(question, output) if output and "id" in question else None
    with psycopg.connect(DSN) as conn:
        conn.execute("""UPDATE runlog.run SET finished_at = now(), outcome = %s, turns = %s, duration_ms = %s, cost_usd = %s, usage = %s,
                        final_text = %s, score = %s WHERE run_id = %s""",
                     (final.subtype if final else "no result", final and final.num_turns, final and final.duration_ms, final and final.total_cost_usd,
                      Jsonb(final.usage if final else None), json.dumps(output, ensure_ascii=False) if output else final and final.result,
                      Jsonb(result) if result else None, run_id))
    return {"run": run_id, "question": question.get("id"), "outcome": final.subtype if final else None, "turns": final and final.num_turns,
            "cost_usd": final and final.total_cost_usd, "score": result, "output": output}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(ask(" ".join(sys.argv[1:]))), indent=2, ensure_ascii=False))
