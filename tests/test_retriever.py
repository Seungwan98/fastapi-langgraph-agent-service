from __future__ import annotations

import json

from app.core.settings import Settings
from app.services.retriever import (
    KnowledgeRetriever,
    build_rag_index,
    chunk_text,
    cosine_similarity,
    has_clear_red_flag,
    lexical_overlap_score,
    load_documents_from_directory,
    parse_document_metadata,
)


class FakeEmbeddings:
    def __init__(self, vector: list[float]):
        self.vector = vector

    def embed_query(self, query: str) -> list[float]:
        return self.vector


def test_cosine_similarity_prefers_aligned_vectors():
    """코사인 유사도가 같은 방향 벡터에서 가장 높게 계산되는지 확인한다."""
    assert round(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 3) == 1.0
    assert round(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 3) == 0.0


def test_chunk_text_builds_overlapping_chunks():
    """텍스트가 겹침을 유지하며 여러 조각으로 분할되는지 확인한다."""
    chunks = chunk_text("abcdefghij", chunk_size=4, chunk_overlap=1)
    assert chunks == ["abcd", "defg", "ghij"]


def test_parse_document_metadata_reads_frontmatter():
    metadata, body = parse_document_metadata("---\ntype: anxiety_support\nseverity: low\nintent: reassure\n---\n\nBody text")

    assert metadata == {"type": "anxiety_support", "severity": "low", "intent": "reassure"}
    assert body == "Body text"


def test_lexical_overlap_and_red_flag_detection():
    assert lexical_overlap_score("chest pain shortness of breath", "Chest pain with shortness of breath needs urgent care") > 0.5
    assert has_clear_red_flag("I have chest pain and shortness of breath right now") is True
    assert has_clear_red_flag("I feel stressed and a bit tired") is False


def test_knowledge_retriever_returns_ranked_sources(monkeypatch, tmp_path):
    """검색기가 가장 유사한 청크와 메타데이터를 반환하는지 확인한다."""
    index_path = tmp_path / "rag_index.json"
    index_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "doc-1",
                        "source": "docs/knowledge/chest.md",
                        "title": "Chest Guidance",
                        "content": "Seek urgent care if chest pain is severe.",
                        "embedding": [1.0, 0.0],
                        "type": "red_flag",
                        "severity": "high",
                        "intent": "escalate",
                    },
                    {
                        "id": "doc-2",
                        "source": "docs/knowledge/stress.md",
                        "title": "Stress Guidance",
                        "content": "Slow breathing can reduce anxiety symptoms.",
                        "embedding": [0.0, 1.0],
                        "type": "anxiety_support",
                        "severity": "low",
                        "intent": "reassure",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        OPENAI_API_KEY="test-key",
        RAG_ENABLED=True,
        RAG_INDEX_PATH=str(index_path),
        RAG_TOP_K=2,
        RAG_MIN_SCORE=0.1,
    )
    retriever = KnowledgeRetriever(settings)
    monkeypatch.setattr(retriever, "_get_embeddings", lambda: FakeEmbeddings([1.0, 0.0]))

    results = retriever.search("chest pain")

    assert len(results) == 2
    assert results[0].chunk_id == "doc-1"
    assert results[0].source.endswith("chest.md")

    metadata = retriever.to_source_metadata(results)
    assert metadata[0] == {
        "chunk_id": "doc-1",
        "source": "docs/knowledge/chest.md",
        "title": "Chest Guidance",
        "score": 0.75,
        "type": "red_flag",
        "severity": "high",
        "intent": "escalate",
    }
    assert metadata[1] == {
        "chunk_id": "doc-2",
        "source": "docs/knowledge/stress.md",
        "title": "Stress Guidance",
        "score": 0.32,
        "type": "anxiety_support",
        "severity": "low",
        "intent": "reassure",
    }
    assert "Chest Guidance" in retriever.build_context(results)


def test_load_documents_from_directory_reads_markdown(tmp_path):
    """지식 문서 디렉터리에서 마크다운 파일을 읽는지 확인한다."""
    docs_dir = tmp_path / "knowledge"
    docs_dir.mkdir()
    (docs_dir / "sample-guide.md").write_text("A short guide", encoding="utf-8")

    documents = load_documents_from_directory(docs_dir, ("*.md",))

    assert documents == [
        {
            "source": str(docs_dir / "sample-guide.md"),
            "title": "sample guide",
            "content": "A short guide",
            "type": "general",
            "severity": "medium",
            "intent": "educate",
        }
    ]


def test_metadata_policy_prefers_reassuring_doc_for_non_red_flag_query(monkeypatch, tmp_path):
    index_path = tmp_path / "rag_index.json"
    index_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "doc-red",
                        "source": "docs/knowledge/urgent.md",
                        "title": "Urgent Guidance",
                        "content": "Chest pain with shortness of breath needs urgent care.",
                        "embedding": [1.0, 0.0],
                        "type": "red_flag",
                        "severity": "high",
                        "intent": "escalate",
                    },
                    {
                        "id": "doc-calm",
                        "source": "docs/knowledge/anxiety.md",
                        "title": "Anxiety Support",
                        "content": "Stress and muscle tension often cause chest tightness and can improve with slower breathing.",
                        "embedding": [0.96, 0.04],
                        "type": "anxiety_support",
                        "severity": "low",
                        "intent": "reassure",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        OPENAI_API_KEY="test-key",
        RAG_ENABLED=True,
        RAG_INDEX_PATH=str(index_path),
        RAG_TOP_K=2,
        RAG_MIN_SCORE=0.0,
    )
    retriever = KnowledgeRetriever(settings)
    monkeypatch.setattr(retriever, "_get_embeddings", lambda: FakeEmbeddings([1.0, 0.0]))

    results = retriever.search("I feel chest tightness when I am stressed")

    assert results[0].chunk_id == "doc-calm"
    assert results[0].intent == "reassure"


def test_build_rag_index_writes_json_payload(monkeypatch, tmp_path):
    """인덱스 빌더가 문서를 청크와 임베딩으로 저장하는지 확인한다."""
    docs_dir = tmp_path / "knowledge"
    docs_dir.mkdir()
    (docs_dir / "sample-guide.md").write_text(
        "---\ntype: anxiety_support\nseverity: low\nintent: reassure\n---\n\nHelpful health guidance",
        encoding="utf-8",
    )
    output_path = tmp_path / "rag_index.json"

    class FakeEmbeddingClient:
        def __init__(self, *args, **kwargs):
            pass

        def embed_query(self, text: str) -> list[float]:
            return [float(len(text)), 1.0]

    monkeypatch.setattr("app.services.retriever.OpenAIEmbeddings", FakeEmbeddingClient)

    result = build_rag_index(
        input_dir=docs_dir,
        output_path=output_path,
        embedding_model="fake-embedding-model",
        api_key="test-key",
        chunk_size=50,
        chunk_overlap=10,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result.document_count == 1
    assert result.chunk_count == 1
    assert payload["embedding_model"] == "fake-embedding-model"
    assert payload["documents"][0]["id"] == "sample-guide-chunk-1"
    assert payload["documents"][0]["embedding"] == [23.0, 1.0]
    assert payload["documents"][0]["type"] == "anxiety_support"
    assert payload["documents"][0]["severity"] == "low"
    assert payload["documents"][0]["intent"] == "reassure"
