from __future__ import annotations

import json

from app.core.settings import Settings
from app.services.fhir_connector import FHIRPatientContextService
from app.services.public_medical_reference import PublicMedicalReferenceLookup


def test_public_medical_lookup_prefers_keyword_matching_reference(tmp_path):
    source_path = tmp_path / "public_medical_reference.json"
    source_path.write_text(
        json.dumps(
            {
                "references": [
                    {
                        "id": "public-1",
                        "source": "medlineplus",
                        "title": "Tension headache overview",
                        "content": "Most headaches are caused by stress, dehydration, or lack of sleep.",
                        "keywords": ["headache", "stress", "sleep"],
                        "url": "https://example.test/headache",
                    },
                    {
                        "id": "public-2",
                        "source": "medlineplus",
                        "title": "Sprained ankle care",
                        "content": "Ankle sprains often improve with rest and ice.",
                        "keywords": ["ankle", "sprain"],
                        "url": "https://example.test/ankle",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(PUBLIC_MEDICAL_ENABLED=True, PUBLIC_MEDICAL_SOURCE_PATH=str(source_path))

    lookup = PublicMedicalReferenceLookup(settings)
    results = lookup.lookup("I have a stress headache", k=2)

    assert len(results) == 1
    assert results[0].reference_id == "public-1"
    metadata = lookup.to_source_metadata(results)
    assert metadata[0]["source_kind"] == "public_medical"
    assert metadata[0]["provider"] == "medlineplus"


def test_fhir_context_service_loads_local_patient_summary(tmp_path):
    source_path = tmp_path / "fhir_patient_context.json"
    source_path.write_text(
        json.dumps(
            {
                "patients": [
                    {
                        "patient_id": "patient-123",
                        "source": "fhir-sandbox",
                        "title": "Patient 123 context",
                        "patient_summary": "History of episodic palpitations with normal outpatient workups.",
                        "observations": [
                            {
                                "code": "heart-rate",
                                "display": "Heart Rate",
                                "value": "72 bpm",
                                "effective": "2026-04-05",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(FHIR_ENABLED=True, FHIR_SOURCE_PATH=str(source_path), FHIR_OBSERVATION_LIMIT=3)

    service = FHIRPatientContextService(settings)
    context = service.fetch_patient_context(patient_id="patient-123")

    assert context is not None
    assert context.patient_id == "patient-123"
    assert "palpitations" in context.summary
    assert "Heart Rate: 72 bpm" in context.summary
    metadata = service.to_source_metadata(context)
    assert metadata[0]["source_kind"] == "fhir"
    assert metadata[0]["patient_id"] == "patient-123"
