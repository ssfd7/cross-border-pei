---
type: Reference
title: Run a computation on the graph
description: Run instructions for attested computations with runtime ladybug.
status: draft
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Open the graph, which is rebuilt from the source systems by `xbpei.project_graph`, read-only. Bind the supplied values to the declared parameters, which appear in the computation as `$name`, and execute the computation exactly as written. Return the text executed, the parameter values, the SHA-256 of the computation text, the SHA-256 of the result rows and the row count.

The agent supplies parameter values only. It does not write or change the computation. Implemented in `xbpei/execute.py`.
