---
type: Tool
title: Open a case
description: Open a unit of clearance work.
status: draft
"@context": /context.jsonld
performed_by: agent
writes: [xbpei:Case, xbpei:caseKind, xbpei:concernsParty, xbpei:concernsDistribution, xbpei:openedOn]
supports: [WF3.1]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Adds one row to the Clearance schema and returns the case identifier.

# Input

| Field | Meaning |
|---|---|
| `case_kind` | `onboarding`, `renewal`, `change` or `distribution` |
| `concerns_party` | Investor number, for a case about one party |
| `concerns_distribution` | Distribution identifier, for a distribution case |
