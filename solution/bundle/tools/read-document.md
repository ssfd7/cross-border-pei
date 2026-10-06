---
type: Tool
title: Read a document
description: Return the text of a document in the document folder by its reference.
status: draft
"@context": /context.jsonld
performed_by: agent
supports: [WF3.2, C3.3]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Reads only. The document index says where the file is; a document with no file is not digitised, which is not the same as not existing.

# Input

| Field | Meaning |
|---|---|
| `doc_ref` | Reference in the document index, for example `DOC-0201` |
