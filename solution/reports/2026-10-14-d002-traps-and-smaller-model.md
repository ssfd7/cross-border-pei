# WF3 on D-002: three new traps, and a smaller model in both arms

Date: 2026-10-14. Follows the [re-run report](2026-10-13-wf3-rerun-after-ontology-v0-11.md). All data is synthetic and the rules are illustrative.

These runs were scored against the D-002 data and answer key as they stood on 2026-10-14. Two traps added on 2026-10-16 changed both; see the [next report](2026-10-16-d002-traps-only-in-the-semantic-layer.md).

## 1. Summary

- A second distribution, D-002, was added with three traps in which the place an agent looks first holds a plausible wrong answer and the semantic layer names the right one (G10 to G12). D-001 and its answer key are unchanged.
- With Opus 5.5, both arms produced the correct schedule in all three runs. The new traps did not separate them.
- With Haiku 4.5, the arms separated. The ungrounded arm produced no correct schedule in three runs: it did not look through the feeder or the nominee, gave the circular holding a treaty rate and missed the qualifying-holding rate. The grounded arm produced the correct schedule in two of three runs and, in the third, the right rate for every recipient with wrong gross amounts, which the write checks did not catch.
- Grounded Haiku cost USD 0.36 to 0.41 a run, against USD 0.53 to 0.61 for ungrounded Opus and USD 1.13 to 1.27 for grounded Opus.

The accuracy gain from grounding shows with the smaller model, not the larger one. Three runs per arm and model is a small number; these are counts, not rates.

## 2. The traps

D-002 pays a US-source dividend of USD 8,000,000. Record date 2026-12-15, payment date 2027-01-12, so the year end falls between them. Holdings at the record date are those of D-001.

| Case | Trap | Where the wrong answer sits | Where the right one sits |
|---|---|---|---|
| G10 | I-011 moved its tax residence to Belgium on 2026-12-01 | The register's `country_res`, form F-011 (treaty claim LU, VALIDATED) and clearance CL-002 | `onboarding.residence_record`, which the mapping names as the system of record |
| G11 | Form F-013 ends on 2026-12-31 | The form is valid on the record date and still reads VALIDATED | Validity on the payment date, as the procedure and the certification computation test it |
| G12 | R-02 2027.1 (10%) starts on 2027-01-01 | R-02 2026.1 (15%) was never closed, so both read as in force; 15% is also the rate a model knows | The rulebook mapping's warning, and the rules-in-force computation, which drops superseded versions |

The answer key is `gold/answer-key.yaml` (`schedule_d002_a`, total tax USD 1,125,900); `gold/verify.sql` sections 8 and 9 recompute it from the data. A schedule that falls for all three traps scores 8 of 15 lines.

Changes to the semantic layer for this round: the warning in `bundle/references/mappings/rulebook.yaml`, the superseded-version filter in `bundle/computations/rules-in-force.md`, and a write check that refuses a line whose rule version is not in force on the payment date (`xbpei/tools.py`).

## 3. Results

| Measure | Control, Opus | Grounded, Opus | Control, Haiku | Grounded, Haiku |
|---|---|---|---|---|
| Runs | RUN-48171675, RUN-dada0efa, RUN-d638402b | RUN-ddac9f0f, RUN-9022c3d6, RUN-a3d2060b | RUN-ddad8024, RUN-4095623c, RUN-6bad835a | RUN-62e5d941, RUN-f3d24725, RUN-905110e2 |
| Lines of D-002-A correct, as scored | 15, 15, 15 of 15 | 15, 15, 15 of 15 | 0, 0, 2 of 15 | 15, 0, 15 of 15 |
| Lines correct with format normalised | same | same | 8, 8, 8 of 15 | same |
| Scored points | 8, 8, 8 of 8 | 8, 8, 8 of 8 | 0, 0, 1 of 8 (2, 2, 2 normalised) | 8, 0, 8 of 8 |
| Turns | 28 to 34 | 54 to 58 | 26 to 34 | 39 to 65 |
| Elapsed time | 116 to 140 seconds | 179 to 213 seconds | 95 to 143 seconds | 282 to 309 seconds |
| Estimated cost per run | USD 0.53 to 0.61 | USD 1.13 to 1.27 | USD 0.12 to 0.16 | USD 0.36 to 0.41 |

**Ungrounded Haiku.** As scored, the three runs got 0, 0 and 2 lines right, mostly because rates were given as fractions (0.1 for 10%) and, in one run, the component as `DIV`. With rates and component normalised, each run has 8 of 15 lines right. The errors are of substance:

- the feeder I-002 and the nominee I-007 were each given one line, at 30% and at a blended 17.5% to 30%, instead of lines for the recipients behind them (G2, G4); so I-011 and I-013 have no line, and G10 and G11 were never reached;
- the circular holding I-006 was given the 10% treaty rate (G3);
- I-003 was given 10% instead of the 5% its 10.0% voting holding qualifies for (G6).

All three runs applied R-02 2027.1 at 10%, so G12 did not catch Haiku either.

**Grounded Haiku, RUN-f3d24725.** Every one of the 15 rates matches the answer key. The gross amounts do not: the agent worked out each recipient's share itself rather than from the distribution lines, the amounts still summed to USD 8,000,000, and the write tool, which tests only the total per component, accepted the draft. The tax is out by USD 24,982.35. Its first three drafts were refused for other reasons.

## 4. Limits

- Three runs per arm and model. The figures show what happened, not rates.
- G10 to G12 did not separate the arms with Opus. A frontier model that reads every table finds the residence record, tests validity on the payment date and takes the later rule version without being told.
- The ungrounded Haiku runs failed on the older traps (G2 to G6), not on the new ones, which they never reached for I-011 and I-013.
- The control's output format is checked by a JSON schema, but the schema does not say that rates are percentages or what a component identifier looks like. A fairer prompt would; the normalised figures are given for that reason.

## 5. Options from here

1. **Check each line's gross amount** in the write tool: the recipient's share of the payee's distribution line, not only the total. RUN-f3d24725 would then have been refused.
2. **State the output units in the control's schema** and re-run ungrounded Haiku, so its score reflects substance only.
3. **More runs of both arms with Haiku**, to report rates rather than counts.

## 6. Files

- `db/03_seed_legacy.sql`, `documents/DOC-0202-distribution-notice-d002.md`
- `gold/answer-key.yaml` (cases G10 to G12, `schedule_d002_a`), `gold/verify.sql` (sections 8 and 9)
- `bundle/references/mappings/rulebook.yaml`, `bundle/computations/rules-in-force.md`
- `xbpei/score.py` (scores by distribution), `xbpei/agent.py` (model set by `XBPEI_MODEL`), `xbpei/tools.py`, `xbpei/measures.py` (reviewer measures stay on the D-001 Opus runs)
- `reports/runs/`: the twelve runs named above, with their steps
