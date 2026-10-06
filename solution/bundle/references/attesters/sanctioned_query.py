"""Attester for computations run on Postgres or on the graph. No model is involved.

Given the receipt of a run, it confirms that what ran is the bundle's computation with values
bound to the declared parameters and nothing else, and that the result reported is what the
computation returns.
"""
import hashlib


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def attest(receipt: dict, computation: str, parameters: list[dict], rerun) -> dict:
    """`computation` and `parameters` are read from the bundle now; `rerun` executes them and returns the result hash."""
    problems = []
    if receipt["executed"] != computation:
        problems.append("What was executed is not the computation in the bundle.")
    if receipt["computation_sha256"] != sha256(computation):
        problems.append("The computation in the bundle is not the one the receipt names.")
    declared = {p["name"] for p in parameters}
    if set(receipt["parameters"]) != declared:
        problems.append(f"Parameters bound {sorted(receipt['parameters'])} are not the declared {sorted(declared)}.")
    if not problems and rerun(computation, receipt["parameters"]) != receipt["result_sha256"]:
        problems.append("Running the computation again does not give the result reported.")
    return {"passed": not problems, "problems": problems}
