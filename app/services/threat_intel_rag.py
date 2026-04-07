from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph


VISUAL_CATEGORIES = ("figure", "table", "chart")
VECTOR_COLLECTION_NAME = "threat-intel-parent-docs"
INDEX_MANIFEST_NAME = "index_manifest.json"


class IngestState(TypedDict, total=False):
    pdf_path: str
    doc_key: str
    page_docs: list[Document]
    element_docs: list[Document]
    visual_summaries: list[Document]
    visual_summary_errors: list[dict[str, Any]]
    parent_docs: list[Document]
    artifact_dir: str


class QueryState(TypedDict, total=False):
    question: str
    retrieved_docs: list[Document]
    answer: str


@dataclass(frozen=True)
class ThreatIntelIngestResult:
    pdf_path: str
    doc_key: str
    artifact_dir: str
    page_count: int
    element_count: int
    visual_summary_count: int
    parent_count: int


class ThreatIntelRAGService:
    """Local-first multimodal RAG service for threat-intel or workbook-style PDFs."""

    def __init__(
        self,
        *,
        parsed_dir: str | Path = "data/threat_intel/parsed",
        index_dir: str | Path = "data/threat_intel/index",
        vision_model: str = "gpt-4o-mini",
        answer_model: str = "gpt-4o-mini",
        embedding_model: str = "solar-embedding-1-large",
    ):
        self.parsed_dir = Path(parsed_dir)
        self.index_dir = Path(index_dir)
        self.vision_model_name = vision_model
        self.answer_model_name = answer_model
        self.embedding_model_name = embedding_model
        self._query_graph = None
        self._retriever = None
        self._answer_model = None
        self._vision_model = None

    def ingest_pdf(self, pdf_path: str | Path) -> ThreatIntelIngestResult:
        path = Path(pdf_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {path}")

        graph = self.build_ingest_graph()
        result = graph.invoke(
            {
                "pdf_path": str(path),
                "doc_key": self._doc_key(path),
            }
        )

        parent_docs = list(result.get("parent_docs", []))
        element_docs = list(result.get("element_docs", []))
        visual_summaries = list(result.get("visual_summaries", []))
        page_docs = list(result.get("page_docs", []))
        artifact_dir = str(result["artifact_dir"])
        self._retriever = None
        self._query_graph = None
        return ThreatIntelIngestResult(
            pdf_path=str(path),
            doc_key=result["doc_key"],
            artifact_dir=artifact_dir,
            page_count=len(page_docs),
            element_count=len(element_docs),
            visual_summary_count=len(visual_summaries),
            parent_count=len(parent_docs),
        )

    def ingest_directory(self, pdf_dir: str | Path) -> list[ThreatIntelIngestResult]:
        source_dir = Path(pdf_dir)
        if not source_dir.exists() or not source_dir.is_dir():
            raise FileNotFoundError(f"PDF directory not found: {source_dir}")

        pdf_paths = sorted(path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
        results = [self.ingest_pdf(path) for path in pdf_paths]
        if results:
            self.rebuild_index_from_parsed_artifacts()
        return results

    def rebuild_index_from_parsed_artifacts(self):
        parent_docs = self.load_parent_docs()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._retriever = self.build_hybrid_retriever(parent_docs, rebuild_index=True)
        self._query_graph = None
        return self._retriever

    def query(self, question: str) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("Question must not be empty")
        graph = self.build_query_graph()
        result = graph.invoke({"question": question})
        retrieved_docs = list(result.get("retrieved_docs", []))
        return {
            "answer": result.get("answer", ""),
            "retrieved_docs": retrieved_docs,
        }

    def load_parent_docs(self) -> list[Document]:
        parent_docs: list[Document] = []
        if not self.parsed_dir.exists():
            return parent_docs
        for path in sorted(self.parsed_dir.glob("*/parent_docs.jsonl")):
            parent_docs.extend(self._read_document_jsonl(path))
        return parent_docs

    def build_ingest_graph(self):
        builder = StateGraph(IngestState)
        builder.add_node("parse_pages", self._parse_pages_node)
        builder.add_node("parse_elements", self._parse_elements_node)
        builder.add_node("summarize_visuals", self._summarize_visuals_node)
        builder.add_node("merge_parent_docs", self._merge_parent_docs_node)
        builder.add_node("persist_artifacts", self._persist_artifacts_node)

        builder.add_edge(START, "parse_pages")
        builder.add_edge("parse_pages", "parse_elements")
        builder.add_edge("parse_elements", "summarize_visuals")
        builder.add_edge("summarize_visuals", "merge_parent_docs")
        builder.add_edge("merge_parent_docs", "persist_artifacts")
        builder.add_edge("persist_artifacts", END)
        return builder.compile()

    def build_query_graph(self):
        if self._query_graph is not None:
            return self._query_graph
        builder = StateGraph(QueryState)
        builder.add_node("retrieve", self._retrieve_node)
        builder.add_node("answer", self._answer_node)
        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "answer")
        builder.add_edge("answer", END)
        self._query_graph = builder.compile()
        return self._query_graph

    def _parse_pages_node(self, state: IngestState) -> dict[str, Any]:
        page_docs = self.parse_pdf_pages(state["pdf_path"])
        return {"page_docs": page_docs}

    def _parse_elements_node(self, state: IngestState) -> dict[str, Any]:
        element_docs = self.parse_pdf_elements(state["pdf_path"])
        return {"element_docs": element_docs}

    def _summarize_visuals_node(self, state: IngestState) -> dict[str, Any]:
        visual_summaries, visual_summary_errors = self._build_visual_summaries_with_errors(
            state.get("element_docs", [])
        )
        return {
            "visual_summaries": visual_summaries,
            "visual_summary_errors": visual_summary_errors,
        }

    def _merge_parent_docs_node(self, state: IngestState) -> dict[str, Any]:
        parent_docs = self.merge_parent_docs(
            page_docs=state.get("page_docs", []),
            visual_summaries=state.get("visual_summaries", []),
            doc_key=state["doc_key"],
            pdf_path=state["pdf_path"],
        )
        return {"parent_docs": parent_docs}

    def _persist_artifacts_node(self, state: IngestState) -> dict[str, Any]:
        artifact_dir = self.parsed_dir / state["doc_key"]
        artifact_dir.mkdir(parents=True, exist_ok=True)

        self._write_document_jsonl(artifact_dir / "page_docs.jsonl", state.get("page_docs", []))
        self._write_document_jsonl(artifact_dir / "element_docs.jsonl", state.get("element_docs", []))
        self._write_document_jsonl(artifact_dir / "visual_summaries.jsonl", state.get("visual_summaries", []))
        self._write_document_jsonl(artifact_dir / "parent_docs.jsonl", state.get("parent_docs", []))
        self._write_json(artifact_dir / "visual_summary_errors.json", state.get("visual_summary_errors", []))

        manifest = {
            "doc_key": state["doc_key"],
            "pdf_path": state["pdf_path"],
            "page_count": len(state.get("page_docs", [])),
            "element_count": len(state.get("element_docs", [])),
            "visual_summary_count": len(state.get("visual_summaries", [])),
            "visual_summary_error_count": len(state.get("visual_summary_errors", [])),
            "parent_count": len(state.get("parent_docs", [])),
        }
        self._write_json(artifact_dir / "manifest.json", manifest)
        self._write_collection_manifest()
        return {"artifact_dir": str(artifact_dir)}

    def _retrieve_node(self, state: QueryState) -> dict[str, Any]:
        retriever = self._ensure_retriever()
        retrieved_docs = retriever.invoke(state["question"])
        return {"retrieved_docs": retrieved_docs}

    def _answer_node(self, state: QueryState) -> dict[str, Any]:
        docs = state.get("retrieved_docs", [])
        if not docs:
            return {
                "answer": "I could not find supporting evidence in the indexed PDFs for that question.",
            }

        context = self._docs_to_context(docs)
        response = self._get_answer_model().invoke(
            [
                SystemMessage(
                    content=(
                        "You answer questions grounded in indexed PDF material. "
                        "Use only the retrieved context. If evidence is incomplete, say so plainly."
                    )
                ),
                HumanMessage(
                    content=f"Question:\n{state['question']}\n\nRetrieved context:\n{context}"
                ),
            ]
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        return {"answer": text}

    def parse_pdf_pages(self, pdf_path: str | Path) -> list[Document]:
        loader_cls = self._get_upstage_loader_cls()
        loader = loader_cls(
            str(pdf_path),
            split="page",
            output_format="markdown",
            coordinates=True,
        )
        return list(loader.load())

    def parse_pdf_elements(self, pdf_path: str | Path) -> list[Document]:
        loader_cls = self._get_upstage_loader_cls()
        loader = loader_cls(
            str(pdf_path),
            split="element",
            output_format="markdown",
            coordinates=True,
            base64_encoding=list(VISUAL_CATEGORIES),
        )
        return list(loader.load())

    def build_visual_summaries(self, element_docs: list[Document]) -> list[Document]:
        visual_summaries, _ = self._build_visual_summaries_with_errors(element_docs)
        return visual_summaries

    def _build_visual_summaries_with_errors(
        self, element_docs: list[Document]
    ) -> tuple[list[Document], list[dict[str, Any]]]:
        summaries: list[Document] = []
        errors: list[dict[str, Any]] = []
        for doc in element_docs:
            category = str(doc.metadata.get("category", "")).lower()
            if category not in VISUAL_CATEGORIES:
                continue
            try:
                summary_text = self._describe_visual_element(doc)
            except Exception as exc:
                errors.append(
                    {
                        "page": doc.metadata.get("page"),
                        "category": category,
                        "reason": str(exc),
                    }
                )
                continue
            if not summary_text:
                continue
            summaries.append(
                Document(
                    page_content=summary_text,
                    metadata={
                        "page": doc.metadata.get("page"),
                        "category": category,
                        "source": doc.metadata.get("source"),
                    },
                )
            )
        return summaries, errors

    def merge_parent_docs(
        self,
        *,
        page_docs: list[Document],
        visual_summaries: list[Document],
        doc_key: str,
        pdf_path: str,
    ) -> list[Document]:
        summaries_by_page: dict[int, list[str]] = {}
        for item in visual_summaries:
            page = int(item.metadata.get("page", 0) or 0)
            summaries_by_page.setdefault(page, []).append(item.page_content)

        parent_docs: list[Document] = []
        for page_doc in page_docs:
            page = int(page_doc.metadata.get("page", 0) or 0)
            page_summaries = summaries_by_page.get(page, [])
            extra = ""
            if page_summaries:
                extra = "\n\n## Visual intelligence summary\n" + "\n".join(
                    f"- {summary}" for summary in page_summaries
                )
            parent_docs.append(
                Document(
                    page_content=page_doc.page_content + extra,
                    metadata={
                        **page_doc.metadata,
                        "doc_id": f"{doc_key}-page-{page}",
                        "source": pdf_path,
                        "doc_key": doc_key,
                    },
                )
            )
        return parent_docs

    def build_hybrid_retriever(self, parent_docs: list[Document], *, rebuild_index: bool):
        if not parent_docs:
            raise ValueError("No parent documents available to build a retriever")

        BM25Retriever, ParentDocumentRetriever, EnsembleRetriever = self._get_retriever_classes()
        Chroma = self._get_chroma_cls()
        embeddings = self._get_embeddings_model()
        store = self._get_in_memory_store()

        chroma_dir = self.index_dir / "chroma"
        if rebuild_index:
            self._reset_vector_index_dir(chroma_dir)
        else:
            chroma_dir.mkdir(parents=True, exist_ok=True)

        vectorstore = Chroma(
            collection_name=VECTOR_COLLECTION_NAME,
            persist_directory=str(chroma_dir),
            embedding_function=embeddings,
        )

        child_splitter = self._get_text_splitter_cls()(
            chunk_size=700,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""],
        )

        parent_retriever = ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=child_splitter,
            id_key="doc_id",
            search_kwargs={"k": 6},
        )

        store.mset([(str(doc.metadata["doc_id"]), doc) for doc in parent_docs])
        if rebuild_index:
            parent_retriever.add_documents(parent_docs, ids=[str(doc.metadata["doc_id"]) for doc in parent_docs])
            self._write_index_manifest(parent_docs)

        bm25_retriever = BM25Retriever.from_documents(parent_docs)
        bm25_retriever.k = 6

        return EnsembleRetriever(
            retrievers=[bm25_retriever, parent_retriever],
            weights=[0.45, 0.55],
            id_key="doc_id",
        )

    def _get_upstage_loader_cls(self):
        try:
            from langchain_upstage import UpstageDocumentParseLoader
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "langchain-upstage is required for PDF parsing. Install it with `pip install langchain-upstage`."
            ) from exc
        return UpstageDocumentParseLoader

    def _get_embeddings_model(self):
        try:
            from langchain_upstage import UpstageEmbeddings
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "langchain-upstage is required for Upstage embeddings. Install it with `pip install langchain-upstage`."
            ) from exc
        return UpstageEmbeddings(model=self.embedding_model_name)

    def _get_chroma_cls(self):
        try:
            from langchain_chroma import Chroma
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "langchain-chroma is required for vector retrieval. Install it with `pip install langchain-chroma chromadb`."
            ) from exc
        return Chroma

    def _get_retriever_classes(self):
        from langchain_community.retrievers import BM25Retriever
        from langchain_classic.retrievers import EnsembleRetriever, ParentDocumentRetriever

        return BM25Retriever, ParentDocumentRetriever, EnsembleRetriever

    def _get_in_memory_store(self):
        try:
            from langchain.storage import InMemoryStore
        except ImportError:
            from langchain_core.stores import InMemoryStore
        return InMemoryStore()

    def _get_text_splitter_cls(self):
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        return RecursiveCharacterTextSplitter

    def _get_answer_model(self):
        if self._answer_model is None:
            from langchain_openai import ChatOpenAI

            self._answer_model = ChatOpenAI(model=self.answer_model_name, temperature=0)
        return self._answer_model

    def _get_vision_model(self):
        if self._vision_model is None:
            from langchain_openai import ChatOpenAI

            self._vision_model = ChatOpenAI(model=self.vision_model_name, temperature=0)
        return self._vision_model

    def _ensure_retriever(self):
        if self._retriever is None:
            parent_docs = self.load_parent_docs()
            if not parent_docs:
                raise ValueError(
                    "No parsed threat-intel artifacts found. Run the ingest script before querying."
                )
            self.index_dir.mkdir(parents=True, exist_ok=True)
            rebuild_index = not self._index_manifest_path().exists()
            self._retriever = self.build_hybrid_retriever(parent_docs, rebuild_index=rebuild_index)
        return self._retriever

    @staticmethod
    def _extract_data_url(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict):
            for key in ("base64", "data", "content", "image_base64"):
                nested = value.get(key)
                if isinstance(nested, str) and nested:
                    value = nested
                    break
        if not isinstance(value, str) or not value:
            return None
        if value.startswith("data:"):
            return value
        return f"data:image/png;base64,{value}"

    @staticmethod
    def _doc_key(path: Path) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
        return slug or "document"

    @staticmethod
    def _serialize_document(doc: Document) -> dict[str, Any]:
        return {"page_content": doc.page_content, "metadata": doc.metadata}

    @classmethod
    def _deserialize_document(cls, payload: dict[str, Any]) -> Document:
        return Document(
            page_content=str(payload.get("page_content", "")),
            metadata=dict(payload.get("metadata", {})),
        )

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_document_jsonl(self, path: Path, documents: list[Document]) -> None:
        lines = [json.dumps(self._serialize_document(doc), ensure_ascii=False) for doc in documents]
        path.write_text("\n".join(lines), encoding="utf-8")

    def _read_document_jsonl(self, path: Path) -> list[Document]:
        if not path.exists():
            return []
        documents: list[Document] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            documents.append(self._deserialize_document(json.loads(stripped)))
        return documents

    def _write_collection_manifest(self) -> None:
        collection_manifest: list[dict[str, Any]] = []
        if self.parsed_dir.exists():
            for manifest_path in sorted(self.parsed_dir.glob("*/manifest.json")):
                collection_manifest.append(json.loads(manifest_path.read_text(encoding="utf-8")))
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self.parsed_dir / "collection_manifest.json", collection_manifest)

    def _write_index_manifest(self, parent_docs: list[Document]) -> None:
        manifest = {
            "collection_name": VECTOR_COLLECTION_NAME,
            "parent_count": len(parent_docs),
            "doc_ids": [str(doc.metadata["doc_id"]) for doc in parent_docs],
        }
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._index_manifest_path(), manifest)

    def _index_manifest_path(self) -> Path:
        return self.index_dir / INDEX_MANIFEST_NAME

    def _describe_visual_element(self, doc: Document) -> str | None:
        data_url = self._extract_data_url(doc.metadata.get("base64_encoding"))
        if not data_url:
            return None

        response = self._get_vision_model().invoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Summarize this figure or table for retrieval. "
                                "Capture the key facts, lists, relationships, or structured rows in plain text."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                )
            ]
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        return " ".join(text.split()) or None

    @staticmethod
    def _docs_to_context(docs: list[Document]) -> str:
        sections = []
        for index, doc in enumerate(docs, start=1):
            meta = doc.metadata or {}
            sections.append(
                f"[doc {index}]\n"
                f"doc_id={meta.get('doc_id', 'unknown')}\n"
                f"source={meta.get('source', 'unknown')}\n"
                f"page={meta.get('page', 'unknown')}\n"
                f"content=\n{doc.page_content}"
            )
        return "\n\n".join(sections)

    def _reset_vector_index_dir(self, chroma_dir: Path) -> None:
        if chroma_dir.exists():
            shutil.rmtree(chroma_dir)
        chroma_dir.mkdir(parents=True, exist_ok=True)
