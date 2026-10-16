# WF3 on D-002: traps that only the semantic layer can settle

Date: 2026-10-16. Follows the [D-002 report](2026-10-14-d002-traps-and-smaller-model.md). All data is synthetic and the rules are illustrative.

## 1. Summary

- The traps of the last round (G10 to G12) did not separate the arms with Opus, because the right answer was in the data: a frontier model that reads every table finds it. Two traps were added in which no table settles the question and only the mappings do (G13, G14).
- With Opus, the grounded arm produced the correct schedule in 3 of 3 runs; the ungrounded arm in 2 of 3. Its miss was the new trap G13: it gave Kirchberg the 5% rate on votes the holder has waived, under-withholding by USD 50,000.
- The two ungrounded Opus runs that got G13 right did so by caution, not knowledge: they saw a side letter they could not read and held back from the 5% rate. None of the three knew what class A2 means.
- With Haiku, the grounded arm produced the correct schedule in 3 of 3 runs; the ungrounded arm in none, with 9 of 15 lines right in each run.
- Grounded Haiku cost USD 0.29 to 0.35 a run; ungrounded Opus USD 0.54 to 0.59; grounded Opus USD 1.00 to 1.26.

Three runs per arm and model are counts, not rates.

## 2. The new traps

Both are dated from 2026-12-01, so D-001 is unchanged.

| Case | What the data shows | What only the semantic layer says |
|---|---|---|
| G13 | From 2026-12-01 I-003 holds class `A2` units (C-003b). The register shows `vote_pct` 12.5, which multiplies to 10.0% of Orion and meets the 5% rule R-03. A side letter, DOC-0003, is listed but not digitised. | The investor register mapping: class A2 units carry no votes, waived by side letter. Effective voting is 0; the rate is R-02 2027.1, 10%. |
| G14 | From 2026-12-01 entity management (H-005b) gives the feeder 25% of the votes in the fund; the register (C-002) gives 24%. Entity management holds the whole chain from feeder to Orion. Neither system says which wins. | The entity management mapping: where the holder is an investor of record, the register is the system of record. I-010 holds 9.6% of Orion, not 10.0%; the rate is 10%, not 5%. |

The class meaning is applied in the graph projection (`xbpei/project_graph.py`) and in `computations/frozen-investor-list`. The precedence rule was already in the mapping and the graph; `computations/record-conflicts` reports the difference. The answer key (`schedule_d002_a`) now gives I-003 10%, total tax USD 1,175,900; `gold/verify.sql` recomputes it.

The control's output schema now states that rates are in percent and what a component identifier looks like, so the ungrounded arm is no longer marked down for format, as Haiku was in the last round.

## 3. Results

| Measure | Control, Opus | Grounded, Opus | Control, Haiku | Grounded, Haiku |
|---|---|---|---|---|
| Runs | RUN-03de3966, RUN-4615b89a, RUN-bb55213f | RUN-248f3347, RUN-380f085b, RUN-2276e3d2 | RUN-46dd5344, RUN-1b053291, RUN-a5a6208a | RUN-5bf58d07, RUN-1bf7b08c, RUN-07f66e15 |
| Lines of D-002-A correct | 15, 15, 14 of 15 | 15, 15, 15 of 15 | 9, 9, 9 of 15 | 15, 15, 15 of 15 |
| Scored points | 9, 9, 8 of 9 | 9, 9, 9 of 9 | 4, 4, 4 of 9 | 9, 9, 9 of 9 |
| Difference from the answer key in tax | 0, 0, −50,000 | 0, 0, 0 | +144,000 in each | 0, 0, 0 |
| Turns | 30 to 34 | 55 to 63 | 24 to 29 | 59 to 65 |
| Elapsed time | 116 to 147 seconds | 185 to 193 seconds | 96 to 172 seconds | 231 to 277 seconds |
| Estimated cost per run | USD 0.54 to 0.59 | USD 1.00 to 1.26 | USD 0.12 to 0.18 | USD 0.29 to 0.35 |

**Ungrounded Opus and G13.** RUN-bb55213f multiplied the register's 12.5% through to 10.0% of Orion and applied R-03 at 5%, asking the reviewer to confirm. RUN-03de3966 and RUN-4615b89a applied 10% because "the class A2 side letter DOC-0003 is not digitised". They reached the right rate without knowing the reason. All three handled G14: they took the feeder's share from the register.

**Ungrounded Haiku.** The three runs gave identical schedules. The feeder I-002 and the nominee I-007 were each given one line at 30% instead of lines for the recipients behind them, and the circular holding I-006 was given the 10% treaty rate. So G10, G11 and G14 were never reached: I-010, I-011 and I-013 have no line. The runs did not apply R-03 to anyone, so G13 passed by default. Haiku's failures are of look-through, not of the new traps.

**Grounded Haiku.** All three runs correct, on every trap. The gross-amount error of the last round (RUN-f3d24725) did not recur, but the check that would catch it has not been added.

## 4. What this shows

- A trap separates the arms only if the deciding fact is absent from the data. G10 to G12 put it in a less obvious table, and Opus found it every time. G13 put it only in the mappings, and Opus without them either applied the wrong rate or reached the right one for a reason it could not state.
- The listed side letter softens G13: it tells a careful agent that something is unknown. A real register would list it, so it stays.
- G14 did not catch ungrounded Opus. Taking the register for an investor's holding is the reading a careful model makes on its own; a fairer test of source precedence would set two sources of equal standing against each other.
- With the smaller model, grounding decides whether the schedule is right, and grounded Haiku costs less than ungrounded Opus.

## 5. Limits

- Three runs per arm and model.
- The traps were written by the same hand as the semantic layer that settles them. A practitioner would set others.
- The write tool still tests only the total gross amount per component, not each line's share.
- The reviewer measures in `xbpei/measures.py` stay on the D-001 Opus runs. The faulty-draft test needs a fresh grounded D-001 run to start from, because later runs reset the Clearance schema.

## 6. Files

- `db/03_seed_legacy.sql` (C-003b, H-005b, DOC-0003)
- `bundle/references/mappings/investor_register.yaml`, `bundle/computations/frozen-investor-list.md`, `xbpei/project_graph.py`
- `gold/answer-key.yaml` (G13, G14, `schedule_d002_a`), `gold/verify.sql` (sections 8 and 9), `xbpei/score.py`
- `xbpei/agent.py` (control output schema)
- `reports/runs/`: the twelve runs named above, with their steps
