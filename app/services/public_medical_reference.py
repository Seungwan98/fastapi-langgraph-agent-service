from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..core.settings import Settings
from .retriever import lexical_overlap_score


@dataclass(frozen=True)
class PublicMedicalReference:
    reference_id: str
    source: str
    title: str
    content: str
    url: str | None
    keywords: list[str]
    score: float = 0.0


class PublicMedicalReferenceLookup:
    def __init__(self, settings: Settings):
        self.enabled = settings.public_medical_enabled
        self.source_path = Path(settings.public_medical_source_path)
        self.base_url = (settings.public_medical_base_url or "").strip()
        self.top_k = settings.public_medical_top_k
        self._cache: list[PublicMedicalReference] | None = None
        self._lock = Lock()

    def lookup(self, query: str, *, k: int | None = None) -> list[PublicMedicalReference]:
        if not self.enabled or not query.strip():
            return []

        remote_results = self._fetch_remote(query, k or self.top_k)
        if remote_results:
            return remote_results

        references = self._load_local_references()
        if not references:
            return []

        ranked = sorted(
            (
                PublicMedicalReference(
                    reference_id=item.reference_id,
                    source=item.source,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    keywords=item.keywords,
                    score=self._score_reference(item, query),
                )
                for item in references
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        return [item for item in ranked[: (k or self.top_k)] if item.score > 0]

    @staticmethod
    def build_context(references: list[PublicMedicalReference]) -> str:
        if not references:
            return ""
        sections = []
        for index, reference in enumerate(references, start=1):
            url_line = f"url: {reference.url}\n" if reference.url else ""
            sections.append(
                f"[public medical source {index}]\n"
                f"provider: {reference.source}\n"
                f"title: {reference.title}\n"
                f"relevance: {reference.score:.3f}\n"
                f"{url_line}content:\n{reference.content}"
            )
        return "\n\n".join(sections)

    @staticmethod
    def to_source_metadata(references: list[PublicMedicalReference]) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": reference.reference_id,
                "source": reference.source,
                "title": reference.title,
                "score": round(reference.score, 4),
                "source_kind": "public_medical",
                "provider": reference.source,
                "url": reference.url,
            }
            for reference in references
        ]

    def _load_local_references(self) -> list[PublicMedicalReference]:
        with self._lock:
            if self._cache is not None:
                return self._cache
            if not self.source_path.exists():
                self._cache = []
                return self._cache
            payload = json.loads(self.source_path.read_text(encoding="utf-8"))
            self._cache = [
                PublicMedicalReference(
                    reference_id=str(item["id"]),
                    source=str(item.get("source", "public_medical")),
                    title=str(item["title"]),
                    content=str(item["content"]),
                    url=str(item["url"]) if item.get("url") else None,
                    keywords=[str(keyword).lower() for keyword in item.get("keywords", [])],
                )
                for item in payload.get("references", [])
            ]
            return self._cache

    def _score_reference(self, reference: PublicMedicalReference, query: str) -> float:
        content_score = lexical_overlap_score(query, reference.content)
        keyword_score = lexical_overlap_score(query, " ".join(reference.keywords))
        title_score = lexical_overlap_score(query, reference.title)
        return (content_score * 0.6) + (keyword_score * 0.3) + (title_score * 0.1)

    def _fetch_remote(self, query: str, limit: int) -> list[PublicMedicalReference]:
        if not self.base_url:
            return []
        request = Request(f"{self.base_url}?{urlencode({'q': query, 'limit': limit})}")
        try:
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        return [
            PublicMedicalReference(
                reference_id=str(item["id"]),
                source=str(item.get("source", "public_medical")),
                title=str(item["title"]),
                content=str(item["content"]),
                url=str(item["url"]) if item.get("url") else None,
                keywords=[str(keyword).lower() for keyword in item.get("keywords", [])],
                score=float(item.get("score", 0.0)),
            )
            for item in payload.get("references", [])
        ]
