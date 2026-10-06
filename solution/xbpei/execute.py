"""Run the bundle's attested computations, attest each run, and keep the run log.

The caller supplies a concept and values for its declared parameters. The computation text comes
from the bundle and is executed as written; the caller cannot change it.
"""
import hashlib
import importlib.util
import json
import uuid
from datetime import date
from decimal import Decimal

import psycopg
import real_ladybug as lb
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import BUNDLE, DSN, GRAPH_DB
from . import bundle


def plain(value):
    """Database values as JSON values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value))


def digest(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=plain)
    return hashlib.sha256(text.encode()).hexdigest()


def run_postgres(computation: str, parameters: dict) -> list[dict]:
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        return conn.execute(computation, parameters).fetchall()


def run_ladybug(computation: str, parameters: dict) -> list[dict]:
    result = lb.Connection(lb.Database(str(GRAPH_DB), read_only=True)).execute(computation, parameters)
    names, rows = result.get_column_names(), []
    while result.has_next():
        rows.append(dict(zip(names, result.get_next())))
    return rows


RUNTIMES = {"postgres": run_postgres, "ladybug": run_ladybug}


def load_attester(resource: str):
    spec = importlib.util.spec_from_file_location("attester", BUNDLE / bundle.resolve(resource))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.attest


def start_run(arm: str, procedure: str | None = None, subject: str | None = None, model: str | None = None) -> str:
    run_id = "RUN-" + uuid.uuid4().hex[:8]
    with psycopg.connect(DSN) as conn:
        conn.execute("INSERT INTO runlog.run (run_id, arm, procedure, subject, model) VALUES (%s, %s, %s, %s, %s)",
                     (run_id, arm, procedure, subject, model))
    return run_id


def finish_run(run_id: str, outcome: str) -> None:
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE runlog.run SET finished_at = now(), outcome = %s WHERE run_id = %s", (outcome, run_id))


def log_step(run_id: str | None, kind: str, concept: str | None = None, terms: list[str] | None = None, parameters=None,
             executed: str | None = None, result=None, row_count: int | None = None, attested: bool | None = None,
             verdict: str | None = None) -> None:
    if run_id is None:
        return
    as_json = lambda v: None if v is None else Jsonb(json.loads(json.dumps(v, default=plain)))
    with psycopg.connect(DSN) as conn:
        conn.execute("""INSERT INTO runlog.step (run_id, seq, kind, concept, terms, parameters, executed, result, row_count, attested, verdict)
                        SELECT %s, coalesce(max(seq), 0) + 1, %s, %s, %s, %s, %s, %s, %s, %s, %s FROM runlog.step WHERE run_id = %s""",
                     (run_id, kind, concept, terms, as_json(parameters), executed, as_json(result), row_count, attested, verdict, run_id))


def run_computation(concept_id: str, parameters: dict, run_id: str | None = None) -> dict:
    """Run one attested computation. Returns its rows, the terms it reads and the attester's verdict."""
    concept = bundle.concept(concept_id)
    if concept.meta["type"] != "Attested Computation":
        return {"error": f"{concept.id} is not an attested computation."}
    declared = {p["name"]: p for p in concept.meta["parameters"]}
    if set(parameters) != set(declared):
        return {"error": f"{concept.id} takes exactly these parameters: {sorted(declared)}."}
    for name, value in parameters.items():
        if declared[name]["type"] == "date":
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError):
                return {"error": f"{name} must be a date written as YYYY-MM-DD."}
    computation, runner = concept.computation, RUNTIMES[concept.meta["runtime"]]
    rows = json.loads(json.dumps(runner(computation, parameters), default=plain))
    receipt = {"executed": computation, "parameters": parameters, "computation_sha256": digest(computation),
               "result_sha256": digest(rows), "row_count": len(rows)}
    attest = load_attester(concept.meta["attester"]["resource"])
    verdict = attest(receipt, bundle.concept(concept_id).computation, concept.meta["parameters"],
                     lambda text, values: digest(json.loads(json.dumps(runner(text, values), default=plain))))
    log_step(run_id, "computation", concept.id, concept.meta.get("reads"), parameters, computation, rows, len(rows),
             verdict["passed"], "; ".join(verdict["problems"]) or "The sanctioned computation ran and the result is as reported.")
    return {"concept": concept.id, "reads": concept.meta.get("reads", []), "rows": rows, "row_count": len(rows),
            "attested": verdict["passed"], "receipt": {k: v for k, v in receipt.items() if k != "executed"}}
