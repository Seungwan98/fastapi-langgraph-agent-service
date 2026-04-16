# Knowledge Docs Note

`docs/` is now reserved for documentation that agents and humans read directly.

The actual runtime RAG source documents were moved to:

- `knowledge-base/`

Use that folder when:
- adding or editing retrieval source documents
- rebuilding `data/rag_index.json`
- configuring `RAG_SOURCE_DIR`

Quick command:

```bash
python3 scripts/build_rag_index.py --input-dir knowledge-base --output data/rag_index.json
```
