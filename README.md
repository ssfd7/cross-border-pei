# Cross-border private equity investment

A prototype showing how a shared ontology grounds AI agents that do the bulk of the work for two business products, over data held in enterprise legacy systems. All fund, investor and payment data is synthetic.

**Status (2026-10-05):** business requirements and the semantic model are drafted. The solution design is in progress; no solution code exists yet.

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
| [`model/`](model/README.md) | The ontology, draft v0.8: Draw.io diagram (overview and five detail pages), OWL Turtle, and a README with decisions, traceability and checks |
| [`AGENTS.md`](AGENTS.md) | Modelling and Draw.io conventions for AI agents working in this repository |

## Where to start reviewing

1. The two business requirements documents, for scope and objectives.
2. [`model/README.md`](model/README.md), which shows each diagram page as an image; the editable source is `model/xb-pei-model.drawio` (diagrams.net). Pages 04 and 05 are the newest and least reviewed.
3. One operating procedure, for example [`wf3-withholding-at-distribution.md`](business/clearance-product/wf3-withholding-at-distribution.md), to see what the agents are expected to carry out.

## Solution direction agreed so far

Nothing below is built or written up yet.

- **Legacy systems** (investor register, entity management, onboarding, documents, treasury) are emulated as Postgres schemas and a document folder. Agents read them and never write to them.
- **LookThrough** runs on a property graph (LadybugDB, Cypher). The graph schema is generated from the ontology. The graph is a read-only projection, rebuilt from Postgres.
- **Clearance** agents write drafts to a new Clearance schema in Postgres. People make the decisions: second review and sign-off are recorded against a human.
- **Operating procedures become [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundles.** Reads are attested computations; writes are agent tools implemented in code and described in the bundle.
- **One extension to OKF:** YAML-LD in bundle frontmatter, pointing at a JSON-LD context generated from the Turtle, so procedures, queries and tools refer to ontology terms.

## Open decisions

- The first obligation and jurisdiction pair. US withholding on dividends with Luxembourg as the treaty jurisdiction is proposed.
- Bundle layout and location, and the names of the YAML-LD extension keys.
- Whether Jurisdiction Fact and Tax Status Assertion are kinds of Fact Assertion in the ontology.
- The clearance questions CL1–CL8 in the model are proposals and are not yet in the Clearance requirements.

## Sources and licence

The domain background draws on the Coursera course [*Private Equity and Venture Capital*](https://www.coursera.org/learn/private-equity) (Università Bocconi), cited by week and page. The course slides are not included in this repository.

Copyright 2026 Radu Marian. Licensed under the [Apache License 2.0](LICENSE).

## Limits

The operating procedures are illustrative and have not been reviewed by a practitioner. The ontology encodes no jurisdiction-specific tax rule. The Turtle has not been parsed with an RDF library or run through a reasoner.
