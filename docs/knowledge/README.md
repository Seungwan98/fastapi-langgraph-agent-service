# Knowledge Base Seed

Put curated health-support reference documents in this directory before building the RAG index.

Each source document can optionally begin with simple frontmatter metadata:

```md
---
type: anxiety_support
severity: low
intent: reassure
---
```

Recommended values:
- `type`: `anxiety_support`, `symptom`, `red_flag`, `general`
- `severity`: `low`, `medium`, `high`
- `intent`: `reassure`, `educate`, `escalate`

The retriever uses these fields to prefer calming, benign-first guidance unless the user query contains clear red-flag signals.

Recommended sources:
- vetted FAQ or triage guidance
- symptom education documents reviewed by a clinician
- internal support playbooks with approved language

Seed files included in this repo:
- `urgent-symptoms.md`
- `appointment-preparation.md`
- `health-anxiety-support.md`

Build the index with:

```bash
python3 scripts/build_rag_index.py --input-dir docs/knowledge --output data/rag_index.json
```

Then enable retrieval with environment variables:

```bash
RAG_ENABLED=true
RAG_INDEX_PATH=data/rag_index.json
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_TOP_K=4
RAG_MIN_SCORE=0.2
```

Do not treat this folder as a dump of arbitrary web content. Curate and version the sources.
