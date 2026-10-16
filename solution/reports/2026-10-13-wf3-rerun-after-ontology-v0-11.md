# WF3 re-run of both arms after ontology v0.11

Date: 2026-10-13. Follows the [first run report](2026-10-06-wf3-two-arm-run.md) and the [repeated runs report](2026-10-08-controls-benchmark-and-lookthrough.md). All data is synthetic and the rules are illustrative.

## 1. Summary

- Since the last WF3 runs, the ontology went to v0.10 and v0.11, nearly every computation and tool note in the bundle was revised, the shapes were regenerated and the write tool gained four checks. The control arm's inputs (procedure text, database, prompt) did not change.
- Each arm was run three more times on D-001. All six runs produced the correct schedule: 15 of 15 lines, 13 of 13 points, no difference in tax from the answer key.
- Across all runs so far, the grounded arm is correct in 7 of 7 and the ungrounded arm in 5 of 6. The ungrounded arm's miss of 2026-10-08 did not recur.
- The grounded arm now costs more per run than before the ontology changes: USD 1.50 to 1.78, against 1.25 to 1.45.

On this dataset the arms do not separate on accuracy. What separates them is what a run leaves for the reviewer (section 3) and the cost of leaving it.

## 2. Results

| Measure | Control | Grounded |
|---|---|---|
| Runs | RUN-0bc1690c, RUN-99c6230b, RUN-a9712c64 | RUN-c502560c, RUN-95068086, RUN-849f013e |
| Lines of D-001-A correct | 15, 15, 15 of 15 | 15, 15, 15 of 15 |
| Difference from the answer key in tax | 0, 0, 0 | 0, 0, 0 |
| Scored points | 13, 13, 13 of 13 | 13, 13, 13 of 13 |
| Turns | 33 to 37 | 75 to 86 |
| Elapsed time | 105 to 135 seconds | 250 to 291 seconds |
| Estimated cost per run | USD 0.49 to 0.59 | USD 1.50 to 1.78 |
| Output tokens | 12,628 to 15,344 | 32,441 to 36,693 |
| Cache-read input tokens | 33,274 to 38,052 | 568,667 to 786,153 |

The runs alternated between arms, control first. Each run started from an empty Clearance schema.

**All runs to date**

| Measure | Control | Grounded |
|---|---|---|
| Successful scored runs | 6 | 7 |
| Correct schedule | 5 | 7 |
| Recipients on which all runs agree | 14 of 15 (not I-006) | 15 of 15 |
| Estimated cost per run | USD 0.49 to 0.59 | USD 1.25 to 1.78 |

## 3. What a reviewer gets

| Measure | Control | Grounded |
|---|---|---|
| Lines with resolvable evidence | 0 of 30 in each run | 30 of 30 in each run |
| Assessments recorded | none | 34, 34, 42 |
| Cited facts that resolve | none cited | 166 of 166, 196 of 196, 236 of 236 |
| First draft accepted by the write checks | no write checks | yes, in all three |
| Faulty drafts refused by the write tool | no write tool | 11 of 11 |

Each grounded run's first draft passed the stricter checks added after the 2026-10-08 runs.

## 4. Limits

- Three runs per arm. The figures show what happened, not rates.
- The dataset is unchanged and still legible to a model without help, so it cannot show an accuracy gain from grounding. A harder dataset is the first item in [`ROADMAP.md`](../../ROADMAP.md).
- The rise in grounded cost has not been traced. More assessments and longer computation notes are likely causes; neither has been checked.

## 5. Files

- `reports/runs/`: the six runs named above, with their steps
- `xbpei/agent.py`, `xbpei/score.py`, `xbpei/measures.py`
