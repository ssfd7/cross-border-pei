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


def score_answer(question: dict, output: dict) -> dict:
    """Score a LookThrough answer against the answer key. `output` has status, answer, facts, unknown and conflicts."""
    key = yaml.safe_load(GOLD.read_text())["lookthrough"]
    facts: dict[tuple[str, str], set[str]] = {}
    for f in output.get("facts", []):
        facts.setdefault((f["subject"], f["attribute"]), set()).add(str(f["value"]).strip())
    said = " ".join([output.get("answer", "")] + output.get("unknown", []) + output.get("conflicts", []))
    number = lambda subject, attribute: next((float(v.rstrip("%")) for v in facts.get((subject, attribute), []) if re.fullmatch(r"[\d.]+%?", v)), None)

    if "refuse" in question:
        reason = r"mapp|no source|no system|not held|not recorded" if question["refuse"] == "unmapped" else r"not (a|in|part)|no such|out of scope|outside"
        points = {"refused": output.get("status") == "refused", "no figure given": not output.get("facts"),
                  "reason named": bool(re.search(reason, said, re.I))}
    elif question["cq"] == "CQ1":
        expected = key["CQ1_effective_holding_in_orion"]
        right = [i for i, (econ, vote) in expected.items() if near(number(i, "economicPercentage"), econ) and near(number(i, "votingPercentage"), vote)]
        points = {f"holdings of {len(expected)} investors": len(right) == len(expected),
                  "no party beyond the ultimate holders": {s for s, _ in facts} <= set(expected),
                  "G8 conflict reported": bool(re.search(r"2\.8|3\.5|H-006|disagree|conflict", said, re.I))}
    elif question["cq"] == "CQ2":
        expected = key["CQ2_jurisdictions_fund_to_company"]
        points = {f"{name} {capacity}": facts.get((entity, capacity), set()) == set(expected[name][wanted])
                  for entity, name in question["companies"].items()
                  for capacity, wanted in (("incorporation", "incorporation"), ("taxResidence", "tax_residence"), ("operatingLocation", "operating_location"))}
        points["feeder's tax residence reported as unknown"] = bool(re.search(r"feeder|E-005|I-002", " ".join(output.get("unknown", [])), re.I))
    elif question["cq"] == "CQ4":
        expected, party = key["CQ4_support_i001_d001a"], "I-001"
        points = {"rule version": expected["rule"] in facts.get((party, "rule"), set()), "rate": near(number(party, "rate"), expected["rate"]),
                  "clearance relied on": facts.get((party, "clearance"), set()) == {expected["clearance"]},
                  "certification cited as a fact": expected["fact"] in facts.get((party, "fact"), set())}
    elif question["cq"] == "CQ5":
        expected = key["CQ5_missing_facts"]
        points = {"parties with a missing fact": {s for s, a in facts if a == "unmetRequirement"} == set(expected["parties"]),
                  "circular holding: ownership requirement": expected["requirement_i006"] in facts.get(("I-006", "unmetRequirement"), set())}
    elif question["cq"] == "CQ6":
        expected = key["CQ6_rests_on_i006"]
        of_kind = lambda kind: {s for (s, a), values in facts.items() if a == "kind" and values == {kind}}
        points = {"clearance": of_kind("clearance") == set(expected["clearance"]), "open change case": of_kind("case") == set(expected["case"]),
                  "assessments named": bool(of_kind("assessment")), "determinations named": bool(of_kind("determination"))}
    else:
        expected = key["CQ3_cross_border_payments"]
        groups = {"crossBorder": {p.split()[0] for p in expected["cross_border"]}, "notCrossBorder": set(expected["not_cross_border"]),
                  "undetermined": set(expected["undetermined"])}
        got = lambda value: {s for (s, a), values in facts.items() if a == "crossing" and values == {value}}
        points = {f"{value}: {len(payments)} payments": got(value) == payments for value, payments in groups.items()}
    return {"points": points, "passed": sum(points.values()), "total": len(points)}

