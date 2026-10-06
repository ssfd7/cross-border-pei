# WF3 withholding at distribution: grounded and ungrounded agent, first run

Report date: 6 October 2026. Dataset: the gold dataset in `solution/db/` as committed with this report. All fund, investor, payment and rule data is synthetic.

## 1. Summary

One agent run was made in each of two arms, on the same model, for the same task: prepare the withholding schedule for distribution D-001 of Atlas Growth Fund I LP.

- **Both arms produced the correct schedule.** Each gave all 15 lines of the dividend component with the expected rate, and a total tax of USD 1,510,562.50, which is the answer key's figure.
- **The ungrounded arm was faster and cheaper.** It took 131 seconds and an estimated USD 0.59. The grounded arm took 274 seconds and an estimated USD 1.45.
- **The grounded arm left a record; the ungrounded arm left an answer.** The grounded run stored 43 assessments citing 207 facts, ran only attested computations, and wrote a draft schedule that passed the control checks. The ungrounded run returned the schedule as text.

On this dataset the benchmark does not show an accuracy benefit from grounding. Section 8 explains why, and section 9 lists what limits the conclusions.

## 2. The task

WF3 is the operating procedure for deciding withholding before a distribution is paid (`business/clearance-product/wf3-withholding-at-distribution.md`). For D-001 the agent must:

1. find the investors of record at the record date and the amount each is due;
2. look through intermediaries to the parties whose income it is;
3. test each party's clearance and tax certification on the payment date;
4. decide a rate for each party and component from the rule versions in force;
5. produce a schedule, and stop before the reviewer's sign-off.

D-001 has a record date of 30 October 2026 and a payment date of 16 November 2026. It has two components: D-001-A, a US-source dividend of USD 10,000,000 received from Orion Manufacturing Inc., and D-001-B, a return of capital of USD 2,000,000.

## 3. The dataset

One fund, 12 investors of record, 15 beneficial recipients, 25 parties in all across six emulated source systems (`entity_mgmt`, `investor_register`, `onboarding`, `treasury`, `documents`, `rulebook`) and a Clearance schema holding earlier decisions. Three illustrative rule versions give the rates: R-01 statutory 30%, R-02 treaty 15%, R-03 treaty 5% for a holding of at least 10% of the voting stock of the paying company.

The data carries eight trap cases. The answer key is `solution/gold/answer-key.yaml`; `solution/gold/verify.sql` recomputes its figures from the data.

| Case | Trap |
|---|---|
| G1 | None; the baseline |
| G2 | A holding of 12% of the fund that is 9.6% of the paying company once multiplied through the tiers |
| G3 | Two entities that hold each other, and a clearance still marked cleared while a change case is open |
| G4 | A nominee as holder of record, with one documented and one undocumented owner behind it |
| G5 | Two investors with the same name in different countries |
| G6 | Holdings exactly on the threshold, just under it, and with more economic than voting rights |
| G7 | A tax form marked validated that has ended, and a holding that has been superseded |
| G8 | Two systems that give different percentages for the same holding |

A ninth case, G9, tests refusal of questions about unmapped terms. It is not part of WF3 and was not run.

## 4. The two arms

Both arms used Claude Opus 5.5 through the Claude Agent SDK, with built-in tools switched off and no repository instructions loaded. Both started from the same seeded Clearance schema. The runner is `solution/xbpei/agent.py`.

| | Control (ungrounded) | Grounded |
|---|---|---|
| Procedure given | The original WF3 text | The WF3 concept of the OKF bundle: twelve steps and ten decision rules |
| Knowledge of the data | Table and column names with their types, no comments | The catalogue of twelve attested computations, each with a note on what its rows mean |
| Reading data | A read-only SQL tool; the agent writes its own queries | Only by running a bundle computation with values for its declared parameters |
| Meaning of terms | None supplied | Lookup tools over the ontology and the mapping files |
| Writing | None; the schedule is returned as structured output | The bundle's tools: open a case, record an assessment, draft a schedule |
| Checks on the output | None before scoring | Shapes generated from the ontology, the control shapes, and reconciliation to the distribution, applied before anything is written |

The control arm queried under a database role that can read the source systems and the Clearance schema but not the run log.

## 5. Results

| Measure | Control | Grounded |
|---|---|---|
| Run | RUN-c0837d95 | RUN-582dd980 |
| Lines of D-001-A correct | 15 of 15 | 15 of 15 |
| Total tax on D-001-A | 1,510,562.50 | 1,510,562.50 |
| Difference from the answer key | 0.00 | 0.00 |
| Scored points | 12 of 13 as scored; 13 of 13 on rescoring | 13 of 13 |
| Turns | 36 | 96 |
| Elapsed time | 131 seconds | 274 seconds |
| Estimated cost | USD 0.59 | USD 1.45 |
| Output tokens | 15,002 | 35,749 |
| Cache-read input tokens | 28,365 | 437,538 |
| Cache-creation input tokens | 35,849 | 81,113 |

The control's one missed point was "circular holding reported". The scorer searched for a fixed list of words; the agent wrote that the two entities "each hold 30% of the other" in its notes and called it a "loop". The scorer's word list was widened afterwards and the stored output rescored at 13 of 13. The stored score in the run log still reads 12.

### Case by case

| Scored point | Control | Grounded |
|---|---|---|
| G1 baseline | Pass | Pass |
| G2 multiplied through tiers | Pass | Pass |
| G3 circular holding: no treaty rate | Pass | Pass |
| G3 circular holding: reported | Pass on rescoring | Pass |
| G4 nominee looked through | Pass | Pass |
| G5 same name kept apart | Pass | Pass |
| G6 threshold: exactly on it | Pass | Pass |
| G6 threshold: just under | Pass | Pass |
| G6 threshold: voting, not economic | Pass | Pass |
| G7 expired form | Pass | Pass |
| G7 superseded holding | Pass | Pass |
| G8 US person not withheld | Pass | Pass |
| G8 conflict reported | Pass | Pass |

### Schedule for D-001-A

Each cell gives the outcome, the rate and the tax withheld, in USD.

| Recipient | Gross | Expected | Control | Grounded |
|---|---|---|---|---|
| I-001 Harbor Pension Trust | 1,000,000.00 | 15% / 150,000.00 | cleared 15% / 150,000.00 | cleared 15% / 150,000.00 |
| I-010 Ardennes Industrial Holding S.A. | 1,200,000.00 | 15% / 180,000.00 | cleared 15% / 180,000.00 | cleared 15% / 180,000.00 |
| I-011 Moselle Capital S.A. | 720,000.00 | 15% / 108,000.00 | cleared 15% / 108,000.00 | cleared 15% / 108,000.00 |
| I-012 Claire Dumont | 480,000.00 | 30% / 144,000.00 | cleared 30% / 144,000.00 | cleared 30% / 144,000.00 |
| I-003 Kirchberg Industries S.A. | 1,250,000.00 | 5% / 62,500.00 | cleared 5% / 62,500.00 | cleared 5% / 62,500.00 |
| I-004 Limpertsberg Holdings S.A. | 1,248,750.00 | 15% / 187,312.50 | cleared 15% / 187,312.50 | cleared 15% / 187,312.50 |
| I-005 Grund Participations S.A. | 1,300,000.00 | 15% / 195,000.00 | cleared 15% / 195,000.00 | cleared 15% / 195,000.00 |
| I-006 Meridian Holdings I S.à r.l. | 300,000.00 | 30% / 90,000.00 | defaultRate 30% / 90,000.00 | defaultRate 30% / 90,000.00 |
| I-013 Echternach Pension Fund | 375,000.00 | 15% / 56,250.00 | cleared 15% / 56,250.00 | cleared 15% / 56,250.00 |
| I-014 Client account 7731 | 225,000.00 | 30% / 67,500.00 | defaultRate 30% / 67,500.00 | defaultRate 30% / 67,500.00 |
| I-008 Alpha Holdings SA (Luxembourg) | 600,000.00 | 15% / 90,000.00 | cleared 15% / 90,000.00 | cleared 15% / 90,000.00 |
| I-009 Alpha Holdings SA (Switzerland) | 100,000.00 | 30% / 30,000.00 | cleared 30% / 30,000.00 | cleared 30% / 30,000.00 |
| I-015 Bertrange Capital S.A. | 500,000.00 | 30% / 150,000.00 | defaultRate 30% / 150,000.00 | defaultRate 30% / 150,000.00 |
| I-016 Atlas Co-Invest Vehicle LP | 300,000.00 | 0% / 0.00 | notApplicable 0% / 0.00 | notApplicable 0% / 0.00 |
| I-017 Atlas GP LLC | 401,250.00 | 0% / 0.00 | notApplicable 0% / 0.00 | notApplicable 0% / 0.00 |
| **Total** | **10,000,000.00** | **1,510,562.50** | **1,510,562.50** | **1,510,562.50** |

Both arms also gave 15 lines for D-001-B, all `notApplicable`.

## 6. How each arm worked

### Control

The agent ran 29 SQL queries and read 5 documents. Almost every query was `select *` on one table: it read each source system and the Clearance schema in full, then reasoned over the contents. Two queries joined tables; none filtered by date. The agent applied the date tests, the look-through and the multiplication through tiers itself, from the rows.

Its notes to the reviewer raised three judgement calls unprompted:

- Meridian's clearance rests on an ownership fact that ended on 31 July 2026, and the change case is still open. It resolved the mutual holding to the Jersey trust as 100% ultimate owner and still applied the default rate.
- Kirchberg's 5% rate rests on an effective vote of exactly 10.00%, read as "at least 10%"; the note gives the tax under the other reading.
- It applied the default rate, not a hold, because it could not read the fund's terms.

### Grounded

| Step kind | Count | Detail |
|---|---|---|
| Attested computations | 15 | All twelve computations of the bundle; three were run twice. Every run passed attestation |
| Ontology and mapping lookups | 13 | Eight searches, three descriptions, two mapping lookups |
| Documents read | 6 | Three read in full, two indexed but not digitised, one reference that is not in the index |
| Assessments recorded | 43 | None refused |
| Cases opened | 1 | |
| Schedules drafted | 1 | Accepted at the first attempt |

Most of the lookups concerned whether a payment may be held. The agent searched the ontology for the fund's terms and for a limitation-on-benefits term, found that the agreement is indexed but not digitised and that the ontology has no term for the limitation-on-benefits category, and applied the default rate under decision rule 10.

## 7. What the grounded run left on record

| Record | Count |
|---|---|
| Obligation assessments | 43 |
| Facts cited by those assessments, each resolved to an existing row | 207 |
| Missing-fact findings | 9 |
| Determinations in the draft schedule | 30 |
| Schedules | 1, status `draft`, prepared by the agent, not signed |

Assessments by rule version and result:

| Rule version | Applicable | Not applicable | Undetermined |
|---|---|---|---|
| R-01 statutory 30% | 5 | 17 | 0 |
| R-02 treaty 15% | 7 | 2 | 3 |
| R-03 treaty 5% | 1 | 8 | 0 |

The control run has no equivalent. Its reasoning exists only as the `basis` text of each line and its notes, and nothing in it was checked against the data.

This is not a like-for-like cost comparison. The control arm was not asked to record assessments or to pass any checks, and most of the grounded arm's extra turns were the 43 assessment records.

## 8. Why the arms did not separate

The benchmark was built on the expectation that the ungrounded agent would fail cases G2, G4, G5 and G6. It did not. Three properties of the dataset, all introduced when it was built, explain this:

- **It is small.** Twenty-five parties and a few hundred rows fit in the model's context in full. The control agent did not have to find anything; it read everything.
- **The emulated legacy schemas explain themselves.** Columns such as `pct_vote`, `is_intermediary`, `alloc_basis` and `min_vote_pct` carry their meaning in their names. The trap in G6, voting against economic percentage, is labelled in the data.
- **Some answers are written out.** Rule names, the default treatment recorded on earlier clearances and the descriptions of open items state in plain words what a real system would leave implicit.

A capable model given a small, legible database does not need a semantic layer to answer correctly. That is the finding of this run.

## 9. Limits

- **One run per arm.** Agent runs vary. A single pair shows that both setups work; it says nothing about consistency, and the cost and time figures are single observations.
- **Cost is an estimate.** The runs used a Claude subscription login, for which the SDK reports an equivalent dollar figure, not a billed amount. Token counts are as the SDK reported them.
- **Two scored points are word searches.** "Circular holding reported" and "conflict reported" depend on phrasing, as the control's result showed.
- **The answer key and the grounded procedure share an author.** The decision rules in the bundle's WF3 concept and the answer key were written together. The grounded arm's agreement with the key is in part agreement between two statements of the same reasoning. The control arm reached the same answers from the original procedure text, which is independent evidence that the key is reasonable, but not that it is right.
- **The rules are illustrative.** Rates, the treaty citation and the measurement of the holding threshold through the ownership chain have not been checked against primary law. A correct schedule here means agreement with the answer key, not a correct tax treatment.
- **Refusal was not tested.** Case G9 is outside WF3.
- **The control was not asked to write.** See section 7.

## 10. Incidents

- **Usage limit.** The first grounded attempt (RUN-50392573) stopped after the case was opened and all twelve computations had run, when the subscription's session limit was reached. It was run again after the limit reset. The runner now records such a stop as a failed run. The failed run's steps are in `runs/`.
- **Scorer word list.** Described in section 5.

## 11. Options from here

1. **Make the dataset realistic:** hundreds of investors across several funds, legacy tables with cryptic names and codes, and no plain-language hints. This changes the test in the direction of the hoped-for result, so the present result should stay on record beside it.
2. **Measure what a reviewer or auditor needs:** the share of lines with resolvable evidence, bad drafts caught before writing, the list of procedure steps affected by a change to a term, refusal of unmapped terms, and consistency over repeated runs.
3. **Try a smaller model in both arms.** If grounding lets a cheaper model succeed where it fails ungrounded, that is a cost result. This has not been tested.

## 12. Reproducing the runs

From `solution/`, with Docker running and a Claude Code login or an API key:

```
docker compose up -d --wait
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m xbpei.check_mappings
.venv/bin/python -m xbpei.build_model
.venv/bin/python -m xbpei.project_graph
.venv/bin/python -m xbpei.bundle check
.venv/bin/python -m xbpei.agent control D-001
.venv/bin/python -m xbpei.agent grounded D-001
```

Each agent run first removes what earlier runs wrote to the Clearance schema. Scores, cost and every step are stored in the `runlog` schema.

## 13. Files

| Path | Contents |
|---|---|
| `runs/RUN-c0837d95-control.json` | The control run: its record and all 34 steps, with each query and its rows |
| `runs/RUN-582dd980-grounded.json` | The grounded run: its record and all 80 steps |
| `runs/RUN-50392573-grounded-failed.json` | The attempt stopped by the usage limit |
| `../gold/answer-key.yaml` | Expected results |
| `../gold/verify.sql` | Recomputes the answer key's figures from the data |
| `../xbpei/score.py` | The scorer |
