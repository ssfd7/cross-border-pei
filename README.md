# Cross-border private equity investment

A prototype showing how a shared ontology grounds AI agents that do the bulk of the work for two business products, over data held in enterprise legacy systems. All fund, investor and payment data is synthetic.

**Status (2026-10-06):** business requirements and the semantic model are drafted. A first prototype exists for one procedure, WF3 withholding at distribution, and has been run once with a grounded agent and once with an ungrounded one. Both produced the correct schedule; the benchmark does not yet show an accuracy benefit from grounding. See the [run report](solution/reports/2026-10-06-wf3-two-arm-run.md).

## The two products

| Product | What it does | Requirements |
|---|---|---|
| PEI LookThrough | Analytics: answers structure, payment and tax-obligation questions (CQ1–CQ6) about an investment that spans jurisdictions | [`business/lookthrough-product/lookthrough-business-product.md`](business/lookthrough-product/lookthrough-business-product.md) |
| PEI Clearance | Operations: investor tax onboarding, documentation upkeep, and withholding at distribution (WF1–WF3) | [`business/clearance-product/clearance-business-product.md`](business/clearance-product/clearance-business-product.md) |

Both share one domain background and one ontology.

## Repository layout

| Path | Contents |
|---|---|
| [`business/domain-narrative.md`](business/domain-narrative.md) | Domain background: fund, deal and company lifecycles |
| [`business/domain-glossary.md`](business/domain-glossary.md) | Acronyms |
| `business/lookthrough-product/` | LookThrough business requirements |
| `business/clearance-product/` | Clearance business requirements and three operating procedures (`wf1`–`wf3`), each with controls and scenarios |
| [`model/`](model/README.md) | The ontology, draft v0.9: OWL Turtle, stewardship and status per term, a generated JSON-LD form, the Draw.io diagram (overview and five detail pages) with PNG renderings, and a README with decisions, traceability and checks |
| `solution/` | The prototype: emulated source systems and gold dataset, the OKF bundle, the graph projection, the agent runner and the run report |
| [`AGENTS.md`](AGENTS.md) | Modelling and Draw.io conventions for AI agents working in this repository |

## Where to start reviewing

1. The two business requirements documents, for scope and objectives.
2. [`model/README.md`](model/README.md), which shows each diagram page as an image; the editable source is `model/xb-pei-model.drawio` (diagrams.net). Pages 04 and 05 are the newest and least reviewed.
3. One operating procedure, for example [`wf3-withholding-at-distribution.md`](business/clearance-product/wf3-withholding-at-distribution.md), to see what the agents are expected to carry out.
4. The [run report](solution/reports/2026-10-06-wf3-two-arm-run.md), for what the prototype does, what the first runs showed and what limits the conclusions.

## The prototype

Everything is under `solution/`. It covers WF3 only; WF1, WF2 and the LookThrough questions are not built.

| Path | Contents |
|---|---|
| `solution/db/` | Postgres schemas and seed data: six emulated source systems (entity management, investor register, onboarding, treasury, documents, rule library), the Clearance schema and the run log. Agents read the source systems and never write to them |
| `solution/gold/` | The answer key for the gold dataset and a script that recomputes its figures from the data |
| `solution/documents/` | Five synthetic documents |
| `solution/bundle/` | An [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundle: the WF3 procedure, twelve attested computations, five tools, and the mapping files that say where instances of each ontology term live |
| `solution/shapes/` | SHACL shapes generated from the ontology, and hand-written shapes for four procedure controls |
| `solution/xbpei/` | Python: ontology and mapping lookups, checks, the graph projection (LadybugDB), the executor and attester, the write tools, the agent runner and the scorer |
| `solution/reports/` | The run report and the exported runs |

How the pieces relate:

- **The ontology says what a term means, a mapping says where its instances live, and a query retrieves them.** These are three separate artifacts. Nothing translates ontology terms into SQL automatically.
- **The bundle refers to the ontology.** Concept frontmatter is YAML-LD: a shared `context.jsonld` and the keys `reads`, `writes` and `supports` tie each computation, tool and procedure step to ontology terms, so the bundle and the ontology load into one graph.
- **Reads are attested computations.** An agent supplies values for declared parameters; it does not write or change the query. Each run is checked against the bundle.
- **Writes are tools.** Agents add drafts to the Clearance schema after the draft passes the shapes. Only a person signs a schedule, under a separate database role.
- **The graph is a read-only projection** rebuilt from Postgres. Its schema is written by hand to follow the mappings; it is not generated from the ontology.

To run it, see section 12 of the [run report](solution/reports/2026-10-06-wf3-two-arm-run.md).

## Open decisions

- How to make the benchmark able to separate a grounded agent from an ungrounded one: a larger and less legible dataset, measures of evidence and control in place of accuracy alone, or a smaller model. The run report sets out the options.
- Whether Jurisdiction Fact and Tax Status Assertion are kinds of Fact Assertion in the ontology.
- Ontology terms the source data needs and the model lacks: the treaty a certification claims under, its limitation-on-benefits category, the treaty partner of a rule version, and the party a missing-fact finding concerns.
- The clearance questions CL1–CL8 in the model are proposals and are not yet in the Clearance requirements.

## Sources and licence

The domain background draws on the Coursera course [*Private Equity and Venture Capital*](https://www.coursera.org/learn/private-equity) (Università Bocconi), cited by week and page. The course slides are not included in this repository.

Copyright 2026 Radu Marian. Licensed under the [Apache License 2.0](LICENSE).

## Limits

The operating procedures are illustrative and have not been reviewed by a practitioner. The ontology encodes no jurisdiction-specific tax rule. The three rule versions in the prototype's rule library are illustrative: their rates, citations and the way the holding threshold is measured have not been checked against primary law. The Turtle parses with rdflib and has not been run through a reasoner. The bundle's concepts are drafts and none has been verified by a person. Each agent arm has been run once.
