from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document

from app.services.threat_intel_rag import ThreatIntelRAGService


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeVisionModel:
    def invoke(self, messages):
        return FakeResponse("table mentions graded exposure, symptom checking, and reassurance seeking")


class ExplodingVisionModel:
    def invoke(self, messages):
        raise RuntimeError("vision backend unavailable")


class FakeAnswerModel:
    def invoke(self, messages):
        prompt = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        return FakeResponse(f"answer::{prompt[:40]}")


class FakeChroma:
    def __init__(self, *, collection_name, persist_directory, embedding_function):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function


class FakeParentRetriever:
    def __init__(self, *, vectorstore, docstore, child_splitter, id_key, search_kwargs):
        self.vectorstore = vectorstore
        self.docstore = docstore
        self.child_splitter = child_splitter
        self.id_key = id_key
        self.search_kwargs = search_kwargs
        self.docs = []
        self.ids = []

    def add_documents(self, docs, ids):
        self.docs = list(docs)
        self.ids = list(ids)

    def invoke(self, question):
        if self.docs:
            return self.docs[:1]
        if hasattr(self.docstore, 'pairs') and self.docstore.pairs:
            return [self.docstore.pairs[0][1]]
        return []


class FakeBM25Retriever:
    def __init__(self, docs):
        self.docs = docs
        self.k = 4

    @classmethod
    def from_documents(cls, docs):
        return cls(list(docs))

    def invoke(self, question):
        return self.docs[:1]


class FakeEnsembleRetriever:
    def __init__(self, *, retrievers, weights, id_key):
        self.retrievers = retrievers
        self.weights = weights
        self.id_key = id_key

    def invoke(self, question):
        docs = []
        seen = set()
        for retriever in self.retrievers:
            for doc in retriever.invoke(question):
                doc_id = doc.metadata.get(self.id_key)
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                docs.append(doc)
        return docs


class FakeStore(dict):
    def __init__(self):
        super().__init__()
        self.pairs = []

    def mset(self, pairs):
        self.pairs = list(pairs)


class FakeSplitter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_build_visual_summaries_skips_non_visual_and_handles_base64():
    service = ThreatIntelRAGService()
    service._vision_model = FakeVisionModel()

    summaries = service.build_visual_summaries(
        [
            Document(
                page_content="ignored original text",
                metadata={"page": 1, "category": "table", "base64_encoding": "abcd"},
            ),
            Document(
                page_content="paragraph",
                metadata={"page": 1, "category": "paragraph"},
            ),
        ]
    )

    assert len(summaries) == 1
    assert summaries[0].metadata["page"] == 1
    assert "reassurance seeking" in summaries[0].page_content


def test_merge_parent_docs_appends_visual_summaries_and_doc_ids():
    service = ThreatIntelRAGService()
    page_docs = [
        Document(page_content="page one text", metadata={"page": 1}),
        Document(page_content="page two text", metadata={"page": 2}),
    ]
    visual_summaries = [
        Document(page_content="summary one", metadata={"page": 1, "category": "table"}),
    ]

    parent_docs = service.merge_parent_docs(
        page_docs=page_docs,
        visual_summaries=visual_summaries,
        doc_key="health-anxiety-01",
        pdf_path="/tmp/source.pdf",
    )

    assert len(parent_docs) == 2
    assert "Visual intelligence summary" in parent_docs[0].page_content
    assert parent_docs[0].metadata["doc_id"] == "health-anxiety-01-page-1"
    assert "Visual intelligence summary" not in parent_docs[1].page_content


def test_ingest_pdf_persists_artifacts_with_stubbed_nodes(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    service = ThreatIntelRAGService(parsed_dir=tmp_path / "parsed", index_dir=tmp_path / "index")

    monkeypatch.setattr(
        service,
        "parse_pdf_pages",
        lambda _: [Document(page_content="page 1", metadata={"page": 1})],
    )
    monkeypatch.setattr(
        service,
        "parse_pdf_elements",
        lambda _: [Document(page_content="table el", metadata={"page": 1, "category": "table", "base64_encoding": "abcd"})],
    )
    monkeypatch.setattr(
        service,
        "build_visual_summaries",
        lambda docs: [Document(page_content="visual summary", metadata={"page": 1, "category": "table"})],
    )
    monkeypatch.setattr(
        service,
        "_build_visual_summaries_with_errors",
        lambda docs: ([Document(page_content="visual summary", metadata={"page": 1, "category": "table"})], []),
    )

    result = service.ingest_pdf(pdf_path)

    artifact_dir = Path(result.artifact_dir)
    assert result.page_count == 1
    assert result.visual_summary_count == 1
    assert (artifact_dir / "page_docs.jsonl").exists()
    assert (artifact_dir / "element_docs.jsonl").exists()
    assert (artifact_dir / "visual_summaries.jsonl").exists()
    assert (artifact_dir / "parent_docs.jsonl").exists()
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["doc_key"] == result.doc_key
    assert manifest["visual_summary_error_count"] == 0


def test_ingest_pdf_degrades_gracefully_when_visual_summary_fails(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    service = ThreatIntelRAGService(parsed_dir=tmp_path / "parsed", index_dir=tmp_path / "index")
    service._vision_model = ExplodingVisionModel()

    monkeypatch.setattr(
        service,
        "parse_pdf_pages",
        lambda _: [Document(page_content="page 1", metadata={"page": 1})],
    )
    monkeypatch.setattr(
        service,
        "parse_pdf_elements",
        lambda _: [Document(page_content="table el", metadata={"page": 1, "category": "table", "base64_encoding": "abcd"})],
    )

    result = service.ingest_pdf(pdf_path)
    artifact_dir = Path(result.artifact_dir)
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    errors = json.loads((artifact_dir / "visual_summary_errors.json").read_text(encoding="utf-8"))

    assert result.visual_summary_count == 0
    assert manifest["visual_summary_error_count"] == 1
    assert errors[0]["reason"] == "vision backend unavailable"


def test_query_returns_clear_message_when_no_docs_exist(tmp_path: Path):
    service = ThreatIntelRAGService(parsed_dir=tmp_path / "parsed", index_dir=tmp_path / "index")

    try:
        service.query("What is this document about?")
    except ValueError as exc:
        assert "Run the ingest script" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected query() to fail when parsed artifacts are missing")


def test_query_graph_uses_retriever_and_answer_model(tmp_path: Path):
    service = ThreatIntelRAGService(parsed_dir=tmp_path / "parsed", index_dir=tmp_path / "index")
    service._answer_model = FakeAnswerModel()
    service._retriever = SimpleNamespace(
        invoke=lambda question: [
            Document(
                page_content="Health anxiety can be maintained by repeated checking.",
                metadata={"doc_id": "doc-1", "page": 6, "source": "sample.pdf"},
            )
        ]
    )

    result = service.query("What keeps health anxiety going?")

    assert result["retrieved_docs"][0].metadata["doc_id"] == "doc-1"
    assert result["answer"].startswith("answer::Question:")


def test_build_hybrid_retriever_resets_stale_vector_dir(tmp_path: Path, monkeypatch):
    service = ThreatIntelRAGService(parsed_dir=tmp_path / "parsed", index_dir=tmp_path / "index")
    stale_dir = tmp_path / "index" / "chroma"
    stale_dir.mkdir(parents=True)
    stale_file = stale_dir / "stale.txt"
    stale_file.write_text("old", encoding="utf-8")

    monkeypatch.setattr(
        service,
        "_get_retriever_classes",
        lambda: (FakeBM25Retriever, FakeParentRetriever, FakeEnsembleRetriever),
    )
    monkeypatch.setattr(service, "_get_chroma_cls", lambda: FakeChroma)
    monkeypatch.setattr(service, "_get_embeddings_model", lambda: object())
    monkeypatch.setattr(service, "_get_in_memory_store", lambda: FakeStore())
    monkeypatch.setattr(service, "_get_text_splitter_cls", lambda: FakeSplitter)

    retriever = service.build_hybrid_retriever(
        [Document(page_content="page text", metadata={"doc_id": "doc-1", "page": 1, "source": "sample.pdf"})],
        rebuild_index=True,
    )

    assert stale_dir.exists()
    assert not stale_file.exists()
    docs = retriever.invoke("page")
    assert docs[0].metadata["doc_id"] == "doc-1"


def test_build_hybrid_retriever_load_mode_reuses_existing_index(tmp_path: Path, monkeypatch):
    service = ThreatIntelRAGService(parsed_dir=tmp_path / "parsed", index_dir=tmp_path / "index")
    service.index_dir.mkdir(parents=True, exist_ok=True)
    service._write_json(service._index_manifest_path(), {"collection_name": "threat-intel-parent-docs"})

    monkeypatch.setattr(
        service,
        "_get_retriever_classes",
        lambda: (FakeBM25Retriever, FakeParentRetriever, FakeEnsembleRetriever),
    )
    monkeypatch.setattr(service, "_get_chroma_cls", lambda: FakeChroma)
    monkeypatch.setattr(service, "_get_embeddings_model", lambda: object())
    monkeypatch.setattr(service, "_get_in_memory_store", lambda: FakeStore())
    monkeypatch.setattr(service, "_get_text_splitter_cls", lambda: FakeSplitter)

    docs = [Document(page_content="page text", metadata={"doc_id": "doc-1", "page": 1, "source": "sample.pdf"})]
    retriever = service.build_hybrid_retriever(docs, rebuild_index=False)

    assert retriever.invoke("page")[0].metadata["doc_id"] == "doc-1"
