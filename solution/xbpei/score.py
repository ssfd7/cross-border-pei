"""Score a withholding schedule against the answer key, case by case.

A schedule is a list of lines: recipient_no, component, outcome, gross_amount, withholding_rate,
tax_withheld. `text` is everything the agent said or recorded as reasoning, searched for the two
things a schedule line cannot carry: that a circular holding and a source conflict were reported.
"""
import re

import yaml

from . import GOLD

COMPONENT = "D-001-A"


def near(a, b) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) < 0.01


def score(lines: list[dict], text: str = "") -> dict:
    key = yaml.safe_load(GOLD.read_text())["schedule_d001_a"]
    expected = {l["recipient"]: l for l in key["lines"]}
    got: dict[str, list[dict]] = {}
    for line in lines:
        if line.get("component") == COMPONENT:
            got.setdefault(line.get("recipient_no"), []).append(line)

    def right(recipient: str, any_default: bool = False) -> bool:
        """One line for the recipient, with the expected gross amount and rate."""
        mine = got.get(recipient, [])
        if len(mine) != 1 or not near(mine[0].get("gross_amount"), expected[recipient]["gross"]):
            return False
        if any_default:  # default rate or hold are both acceptable; a reduced rate is not
            return mine[0].get("outcome") in ("defaultRate", "held") and not (0 < float(mine[0].get("withholding_rate") or 0) < 30)
        return near(mine[0].get("withholding_rate") or 0, expected[recipient]["rate"])

    cases = {
        "G1 baseline": right("I-001"),
        "G2 multiplied through tiers": right("I-010") and right("I-011") and right("I-012"),
        "G3 circular holding: no treaty rate": right("I-006", any_default=True),
        "G3 circular holding: reported": bool(re.search(r"circular|cycle|loop|each other|cross-hold", text, re.I)),
        "G4 nominee looked through": right("I-013") and right("I-014") and "I-007" not in got,
        "G5 same name kept apart": right("I-008") and right("I-009"),
        "G6 threshold: exactly on it": right("I-003"),
        "G6 threshold: just under": right("I-004"),
        "G6 threshold: voting, not economic": right("I-005"),
        "G7 expired form": right("I-015"),
        "G7 superseded holding": bool(got.get("I-008")) and near(got["I-008"][0].get("gross_amount"), 600000),
        "G8 US person not withheld": right("I-016") and right("I-017"),
        "G8 conflict reported": bool(re.search(r"3\.5\s*%?|H-006|disagree|conflict", text, re.I)),
    }
    tax = sum(float(l.get("tax_withheld") or 0) for l in lines if l.get("component") == COMPONENT)
    gross = sum(float(l.get("gross_amount") or 0) for l in lines if l.get("component") == COMPONENT)
    correct_lines = sum(1 for r in expected if right(r, any_default=(r == "I-006")))
    return {"cases": cases, "cases_passed": sum(cases.values()), "cases_total": len(cases),
            "lines_correct": correct_lines, "lines_expected": len(expected), "lines_given": sum(len(v) for v in got.values()),
            "gross_total": round(gross, 2), "tax_total": round(tax, 2), "tax_expected": key["total_tax_if_g3_defaulted"],
            "tax_error": round(tax - key["total_tax_if_g3_defaulted"], 2)}
