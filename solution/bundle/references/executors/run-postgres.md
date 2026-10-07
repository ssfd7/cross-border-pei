---
type: Reference
title: Run a computation on Postgres
description: Run instructions for attested computations with runtime postgres.
status: draft
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Connect to the prototype database as the read-only agent role. Bind the supplied values to the declared parameters, which appear in the computation as `%(name)s`, and execute the computation exactly as written. Return the text executed, the parameter values, the SHA-256 of the computation text, the SHA-256 of the result rows and the row count.

The agent supplies parameter values only. It does not write or change the computation. Implemented in `xbpei/execute.py`.
