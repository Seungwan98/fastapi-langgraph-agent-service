from __future__ import annotations

import json
import math
from dataclasses import dataclass
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from ..core.settings import Settings


DEFAULT_DOCUMENT_PATTERNS = ("*.md", "*.txt")
SEMANTIC_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.3
HIGH_SEVERITY_PATTERNS = (
    ("chest pain", "shortness of breath"),
    ("one-sided weakness",),
    ("trouble speaking",),
    ("fainting",),
    ("seizure",),
    ("face swelling", "throat"),
    ("uncontrolled bleeding",),
)


def _normalize_metadata_value(value: Any, default: str) -> str:
    if not isinstance(value, str):
        return default
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or default


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    source: str
    title: str | None
    content: str
    embedding: list[float]
    doc_type: str
    severity: str
    intent: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    source: str
    title: str | None
    content: str
    score: float
    semantic_score: float
    lexical_score: float
    doc_type: str
    severity: str
    intent: str


@dataclass(frozen=True)
class RAGBuildResult:
    document_count: int
    chunk_count: int
    output_path: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int


class KnowledgeRetriever:
    """JSON-backed semantic retriever using OpenAI embeddings."""

    def __init__(self, settings: Settings):
        self.enabled = settings.rag_enabled
        self.index_path = Path(settings.rag_index_path)
        self.embedding_model = settings.rag_embedding_model
        self.top_k = settings.rag_top_k
        self.min_score = settings.rag_min_score
        self._api_key = settings.openai_api_key or ""
        self._index_lock = Lock()
        self._embedding_lock = Lock()
        self._index_cache: list[IndexedChunk] | None = None
        self._embeddings: OpenAIEmbeddings | None = None

    def search(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        """Return the most similar chunks for the query."""
        if not self.enabled or not query.strip():
            return []

        indexed_chunks = self._load_index()
        if not indexed_chunks:
            return []

        query_embedding = self._get_embeddings().embed_query(query)
        top_k = k or self.top_k
        ranked_chunks = sorted(
            (
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    title=chunk.title,
                    content=chunk.content,
                    score=self._score_chunk(
                        chunk=chunk,
                        query=query,
                        query_embedding=query_embedding,
                    ),
                    semantic_score=cosine_similarity(query_embedding, chunk.embedding),
                    lexical_score=lexical_overlap_score(query, chunk.content),
                    doc_type=chunk.doc_type,
                    severity=chunk.severity,
                    intent=chunk.intent,
                )
                for chunk in indexed_chunks
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        return [chunk for chunk in ranked_chunks[:top_k] if chunk.score >= self.min_score]

    def build_context(self, chunks: list[RetrievedChunk]) -> str:
        """Convert retrieved chunks into a prompt-friendly context block."""
        if not chunks:
            return ""

        sections: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            title_line = f"title: {chunk.title}\n" if chunk.title else ""
            sections.append(
                f"[source {index}]\n"
                f"id: {chunk.chunk_id}\n"
                f"source: {chunk.source}\n"
                f"{title_line}"
                f"relevance: {chunk.score:.3f}\n"
                f"content:\n{chunk.content}"
            )
        return "\n\n".join(sections)

    @staticmethod
    def to_source_metadata(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
        """Convert retrieval results into API-safe metadata."""
        return [
            {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "title": chunk.title,
                "score": round(chunk.score, 4),
                "type": chunk.doc_type,
                "severity": chunk.severity,
                "intent": chunk.intent,
            }
            for chunk in chunks
        ]

    def refresh_index(self) -> None:
        """Clear the in-memory index cache after a rebuild."""
        with self._index_lock:
            self._index_cache = None

    def _load_index(self) -> list[IndexedChunk]:
        with self._index_lock:
            if self._index_cache is not None:
                return self._index_cache

            if not self.index_path.exists():
                self._index_cache = []
                return self._index_cache

            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            self._index_cache = [
                IndexedChunk(
                    chunk_id=str(item["id"]),
                    source=str(item["source"]),
                    title=item.get("title"),
                    content=str(item["content"]),
                    embedding=[float(value) for value in item["embedding"]],
                    doc_type=_normalize_metadata_value(item.get("type"), "general"),
                    severity=_normalize_metadata_value(item.get("severity"), "medium"),
                    intent=_normalize_metadata_value(item.get("intent"), "educate"),
                )
                for item in payload.get("documents", [])
            ]
            return self._index_cache

    def _get_embeddings(self) -> OpenAIEmbeddings:
        with self._embedding_lock:
            if self._embeddings is None:
                self._embeddings = OpenAIEmbeddings(
                    model=self.embedding_model,
                    api_key=SecretStr(self._api_key),
                )
            return self._embeddings

    def _score_chunk(self, *, chunk: IndexedChunk, query: str, query_embedding: list[float]) -> float:
        semantic_score = cosine_similarity(query_embedding, chunk.embedding)
        lexical_score = lexical_overlap_score(query, chunk.content)
        blended = (semantic_score * SEMANTIC_WEIGHT) + (lexical_score * LEXICAL_WEIGHT)
        return blended + metadata_priority_boost(chunk=chunk, query=query)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for two embedding vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def tokenize(text: str) -> list[str]:
    return [token.strip(".,!?():;\"'").lower() for token in text.split() if token.strip(".,!?():;\"'")]


def lexical_overlap_score(query: str, document: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    query_counts = Counter(query_tokens)
    doc_counts = Counter(tokenize(document))
    overlap = sum(min(query_counts[token], doc_counts[token]) for token in query_counts)
    return overlap / max(len(query_tokens), 1)


def has_clear_red_flag(query: str) -> bool:
    normalized = " ".join(tokenize(query))
    return any(all(pattern in normalized for pattern in group) for group in HIGH_SEVERITY_PATTERNS)


def metadata_priority_boost(*, chunk: IndexedChunk, query: str) -> float:
    boost = 0.0
    if chunk.intent == "reassure":
        boost += 0.12
    elif chunk.intent == "educate":
        boost += 0.06
    elif chunk.intent == "escalate":
        boost -= 0.02

    if chunk.severity == "low":
        boost += 0.10
    elif chunk.severity == "medium":
        boost += 0.04
    elif chunk.severity == "high":
        boost += 0.12 if has_clear_red_flag(query) else -0.15

    if chunk.doc_type == "anxiety_support":
        boost += 0.10
    elif chunk.doc_type == "symptom":
        boost += 0.06
    elif chunk.doc_type == "red_flag":
        boost += 0.10 if has_clear_red_flag(query) else -0.08

    return boost


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split long text into overlapping character chunks."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = max(0, end - chunk_overlap)
    return chunks


def load_documents_from_directory(directory: Path, patterns: tuple[str, ...] = DEFAULT_DOCUMENT_PATTERNS) -> list[dict[str, Any]]:
    """Load plain-text knowledge documents from a directory."""
    documents: list[dict[str, Any]] = []
    for pattern in patterns:
        for path in sorted(directory.rglob(pattern)):
            if not path.is_file():
                continue
            raw_text = path.read_text(encoding="utf-8")
            metadata, text = parse_document_metadata(raw_text)
            documents.append(
                {
                    "source": str(path),
                    "title": path.stem.replace("_", " ").replace("-", " ").strip() or path.name,
                    "content": text,
                    "type": metadata.get("type", "general"),
                    "severity": metadata.get("severity", "medium"),
                    "intent": metadata.get("intent", "educate"),
                }
            )
    return documents


def parse_document_metadata(raw_text: str) -> tuple[dict[str, str], str]:
    stripped = raw_text.lstrip()
    if not stripped.startswith("---\n"):
        return {}, raw_text

    lines = stripped.splitlines()
    metadata: dict[str, str] = {}
    end_index = -1
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = _normalize_metadata_value(value, "")

    if end_index == -1:
        return {}, raw_text

    body = "\n".join(lines[end_index + 1 :]).lstrip()
    return metadata, body


def build_rag_index(
    *,
    input_dir: Path,
    output_path: Path,
    embedding_model: str,
    api_key: str,
    chunk_size: int,
    chunk_overlap: int,
    patterns: tuple[str, ...] = DEFAULT_DOCUMENT_PATTERNS,
) -> RAGBuildResult:
    """Build a JSON RAG index from local documents and persist it to disk."""
    if not api_key.strip():
        raise ValueError("OPENAI_API_KEY is required to build the RAG index")
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    documents = load_documents_from_directory(input_dir, patterns)
    if not documents:
        raise ValueError(f"No source documents found in: {input_dir}")

    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=SecretStr(api_key))

    index_documents: list[dict[str, object]] = []
    for document in documents:
        chunks = chunk_text(str(document["content"]), chunk_size, chunk_overlap)
        for chunk_number, chunk in enumerate(chunks, start=1):
            chunk_id = f"{Path(str(document['source'])).stem}-chunk-{chunk_number}"
            index_documents.append(
                {
                    "id": chunk_id,
                    "source": document["source"],
                    "title": document.get("title"),
                    "content": chunk,
                    "embedding": embeddings.embed_query(chunk),
                    "type": document.get("type", "general"),
                    "severity": document.get("severity", "medium"),
                    "intent": document.get("intent", "educate"),
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "embedding_model": embedding_model,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "documents": index_documents,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return RAGBuildResult(
        document_count=len(documents),
        chunk_count=len(index_documents),
        output_path=str(output_path),
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def build_rag_index_from_settings(settings: Settings) -> RAGBuildResult:
    """Build a RAG index using the configured runtime settings."""
    return build_rag_index(
        input_dir=Path(settings.rag_source_dir),
        output_path=Path(settings.rag_index_path),
        embedding_model=settings.rag_embedding_model,
        api_key=settings.openai_api_key or "",
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
