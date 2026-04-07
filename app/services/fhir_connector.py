from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.request import Request, urlopen

from ..core.settings import Settings


@dataclass(frozen=True)
class FHIRPatientContext:
    patient_id: str
    summary: str
    source: str
    title: str
    score: float = 1.0


class FHIRPatientContextService:
    def __init__(self, settings: Settings):
        self.enabled = settings.fhir_enabled
        self.source_path = Path(settings.fhir_source_path)
        self.base_url = (settings.fhir_base_url or "").rstrip("/")
        self.bearer_token = settings.fhir_bearer_token or ""
        self.observation_limit = settings.fhir_observation_limit
        self._cache: dict[str, dict[str, Any]] | None = None
        self._lock = Lock()

    def fetch_patient_context(self, *, patient_id: str | None) -> FHIRPatientContext | None:
        if not self.enabled or not patient_id:
            return None

        local_payload = self._load_local_payload().get(patient_id)
        if local_payload is not None:
            return self._build_local_context(patient_id=patient_id, payload=local_payload)

        remote_context = self._fetch_remote_context(patient_id)
        if remote_context is not None:
            return remote_context
        return None

    @staticmethod
    def build_context(context: FHIRPatientContext | None) -> str:
        if context is None:
            return ""
        return (
            "[fhir patient context]\n"
            f"source: {context.source}\n"
            f"title: {context.title}\n"
            f"content:\n{context.summary}"
        )

    @staticmethod
    def to_source_metadata(context: FHIRPatientContext | None) -> list[dict[str, Any]]:
        if context is None:
            return []
        return [
            {
                "chunk_id": f"fhir-{context.patient_id}",
                "source": context.source,
                "title": context.title,
                "score": context.score,
                "source_kind": "fhir",
                "provider": context.source,
                "patient_id": context.patient_id,
            }
        ]

    def _load_local_payload(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            if self._cache is not None:
                return self._cache
            if not self.source_path.exists():
                self._cache = {}
                return self._cache
            payload = json.loads(self.source_path.read_text(encoding="utf-8"))
            self._cache = {
                str(item["patient_id"]): item
                for item in payload.get("patients", [])
            }
            return self._cache

    def _build_local_context(self, *, patient_id: str, payload: dict[str, Any]) -> FHIRPatientContext:
        observations = payload.get("observations", [])[: self.observation_limit]
        observation_lines = []
        for observation in observations:
            observation_lines.append(
                f"- {observation.get('display', observation.get('code', 'observation'))}: {observation.get('value', 'unknown')} ({observation.get('effective', 'date unknown')})"
            )
        summary_parts = []
        if payload.get("patient_summary"):
            summary_parts.append(str(payload["patient_summary"]))
        if observation_lines:
            summary_parts.append("Recent observations:\n" + "\n".join(observation_lines))
        summary = "\n\n".join(summary_parts).strip() or "No patient summary available."
        return FHIRPatientContext(
            patient_id=patient_id,
            summary=summary,
            source=str(payload.get("source", "fhir_local")),
            title=str(payload.get("title", f"Patient {patient_id} context")),
        )

    def _fetch_remote_context(self, patient_id: str) -> FHIRPatientContext | None:
        if not self.base_url:
            return None
        patient_resource = self._request_json(f"{self.base_url}/Patient/{patient_id}")
        if patient_resource is None:
            return None
        observation_bundle = self._request_json(
            f"{self.base_url}/Observation?patient={patient_id}&_count={self.observation_limit}&_sort=-date"
        )
        summary_lines = [
            f"Patient id: {patient_resource.get('id', patient_id)}",
        ]
        name_text = self._extract_patient_name(patient_resource)
        if name_text:
            summary_lines.append(f"Name: {name_text}")
        for entry in (observation_bundle or {}).get("entry", []):
            resource = entry.get("resource", {})
            summary_lines.append(
                f"- {self._extract_observation_label(resource)}: {self._extract_observation_value(resource)}"
            )
        return FHIRPatientContext(
            patient_id=patient_id,
            summary="\n".join(summary_lines),
            source=self.base_url,
            title=f"FHIR patient {patient_id}",
        )

    def _request_json(self, url: str) -> dict[str, Any] | None:
        headers = {"Accept": "application/fhir+json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _extract_patient_name(resource: dict[str, Any]) -> str:
        names = resource.get("name") or []
        if not names:
            return ""
        first_name = names[0]
        given = " ".join(first_name.get("given", []))
        family = first_name.get("family", "")
        return " ".join(part for part in [given, family] if part).strip()

    @staticmethod
    def _extract_observation_label(resource: dict[str, Any]) -> str:
        coding = ((resource.get("code") or {}).get("coding") or [{}])[0]
        return str(coding.get("display") or resource.get("code", {}).get("text") or "Observation")

    @staticmethod
    def _extract_observation_value(resource: dict[str, Any]) -> str:
        quantity = resource.get("valueQuantity") or {}
        if quantity:
            return f"{quantity.get('value', 'unknown')} {quantity.get('unit', '')}".strip()
        return str(resource.get("valueString") or resource.get("valueCodeableConcept", {}).get("text") or "unknown")
