from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.settings import Settings
from app.services.agent_graph import AgentService, AgentState, BASE_SYSTEM_PROMPT, RETRIEVED_CONTEXT_SYSTEM_PROMPT
from app.services.fhir_connector import FHIRPatientContextService
from app.services.public_medical_reference import PublicMedicalReferenceLookup
from app.services.retriever import KnowledgeRetriever


class FakeModel:
    def __init__(self, content: str, should_raise: bool = False):
        self.content = content
        self.should_raise = should_raise

    def invoke(self, messages: Sequence[object]) -> AIMessage:
        if self.should_raise:
            raise RuntimeError("rewrite failed")
        return AIMessage(content=self.content)


def build_service_for_rewrite(enabled: bool, model) -> AgentService:
    service = AgentService.__new__(AgentService)
    service.settings = cast(Settings, cast(object, SimpleNamespace(rag_query_rewrite_enabled=enabled)))
    service.model = model
    return service


def test_build_retrieval_query_uses_recent_user_turns_only():
    """최근 사용자 발화만 순서대로 묶어 검색 질의를 구성하는지 확인한다."""
    query = AgentService._build_retrieval_query(
        [
            HumanMessage(content="I have had headaches for two weeks."),
            AIMessage(content="Tell me more."),
            HumanMessage(content="They are worse in the morning."),
            HumanMessage(content="What should I ask my doctor?"),
        ],
        max_turns=2,
    )

    assert query == "assistant: Tell me more.\nuser: They are worse in the morning.\nuser: What should I ask my doctor?"


def test_build_retrieval_query_handles_empty_or_disabled_history():
    """검색 히스토리 길이가 0이면 빈 질의를 반환하는지 확인한다."""
    assert AgentService._build_retrieval_query([HumanMessage(content="hello")], max_turns=0) == ""


def test_query_rewrite_returns_model_rewrite_when_enabled():
    """옵션이 켜져 있으면 모델이 다시 쓴 질의를 사용한다."""
    service = build_service_for_rewrite(True, FakeModel("headache duration two weeks\nmorning worsening"))

    rewritten, used_rewrite = service._maybe_rewrite_retrieval_query("I have headaches for two weeks\nThey are worse in the morning")

    assert rewritten == "headache duration two weeks\nmorning worsening"
    assert used_rewrite is True


def test_query_rewrite_falls_back_on_failure_or_disable():
    """재작성 실패나 비활성화 시 원래 질의로 폴백한다."""
    disabled_service = build_service_for_rewrite(False, FakeModel("ignored"))
    query, used_rewrite = disabled_service._maybe_rewrite_retrieval_query("base query")
    assert query == "base query"
    assert used_rewrite is False

    failing_service = build_service_for_rewrite(True, FakeModel("", should_raise=True))
    query, used_rewrite = failing_service._maybe_rewrite_retrieval_query("base query")
    assert query == "base query"
    assert used_rewrite is False


def test_build_answer_prompt_messages_includes_health_anxiety_harness_and_context():
    service = AgentService.__new__(AgentService)
    state = cast(
        AgentState,
        cast(
            object,
            {
                "messages": [HumanMessage(content="I have a headache and I am scared it is a brain tumor.")],
                "retrieved_context": "[source 1]\nsource: docs/knowledge/health-anxiety-support.md\ncontent:\nHeadaches are often caused by stress, dehydration, or fatigue.",
            },
        ),
    )

    prompt_messages = service._build_answer_prompt_messages(state)
    system_prompt_text = cast(str, prompt_messages[0].content)
    retrieval_prompt_text = cast(str, prompt_messages[1].content)
    human_prompt_text = cast(str, prompt_messages[2].content)

    assert len(prompt_messages) == 3
    assert isinstance(prompt_messages[0], SystemMessage)
    assert system_prompt_text == BASE_SYSTEM_PROMPT
    assert "reduce unnecessary anxiety" in system_prompt_text
    assert "most likely/common explanation first" in system_prompt_text
    assert isinstance(prompt_messages[1], SystemMessage)
    assert retrieval_prompt_text.startswith(RETRIEVED_CONTEXT_SYSTEM_PROMPT)
    assert "primary evidence base" in retrieval_prompt_text
    assert "health-anxiety-support.md" in retrieval_prompt_text
    assert isinstance(prompt_messages[2], HumanMessage)
    assert human_prompt_text == "I have a headache and I am scared it is a brain tumor."


def test_build_answer_prompt_messages_skips_context_wrapper_when_no_retrieval():
    service = AgentService.__new__(AgentService)
    state = cast(
        AgentState,
        cast(
            object,
            {
                "messages": [HumanMessage(content="My chest feels tight after a stressful day.")],
                "retrieved_context": "",
            },
        ),
    )

    prompt_messages = service._build_answer_prompt_messages(state)
    system_prompt_text = cast(str, prompt_messages[0].content)
    human_prompt_text = cast(str, prompt_messages[1].content)

    assert len(prompt_messages) == 2
    assert isinstance(prompt_messages[0], SystemMessage)
    assert system_prompt_text == BASE_SYSTEM_PROMPT
    assert isinstance(prompt_messages[1], HumanMessage)
    assert human_prompt_text == "My chest feels tight after a stressful day."


def test_retrieve_node_merges_local_public_and_fhir_sources():
    service = AgentService.__new__(AgentService)
    service.settings = cast(Settings, cast(object, SimpleNamespace(rag_history_turns=2, rag_query_rewrite_enabled=False)))

    class LocalRetriever:
        def search(self, query: str):
            return [SimpleNamespace(chunk_id="local-1", source="docs/knowledge/health.md", title="Health", content="Grounded chunk", score=0.7, doc_type="symptom", severity="medium", intent="educate")]

        def build_context(self, chunks):
            return "[source 1]\ncontent:\nGrounded chunk"

        def to_source_metadata(self, chunks):
            return [{"chunk_id": "local-1", "source": "docs/knowledge/health.md", "title": "Health", "score": 0.7, "source_kind": "knowledge"}]

    class PublicLookup:
        def lookup(self, query: str):
            return [SimpleNamespace(reference_id="public-1", source="medlineplus", title="Public", content="Public context", url="https://example.test", score=0.6, keywords=[])]

        def build_context(self, references):
            return "[public medical source 1]\ncontent:\nPublic context"

        def to_source_metadata(self, references):
            return [{"chunk_id": "public-1", "source": "medlineplus", "title": "Public", "score": 0.6, "source_kind": "public_medical"}]

    class FHIRLookup:
        def fetch_patient_context(self, *, patient_id: str | None):
            assert patient_id == "patient-123"
            return SimpleNamespace(patient_id="patient-123", summary="FHIR summary", source="fhir-sandbox", title="FHIR patient", score=1.0)

        def build_context(self, context):
            return "[fhir patient context]\ncontent:\nFHIR summary"

        def to_source_metadata(self, context):
            return [{"chunk_id": "fhir-patient-123", "source": "fhir-sandbox", "title": "FHIR patient", "score": 1.0, "source_kind": "fhir", "patient_id": "patient-123"}]

    service.retriever = cast(KnowledgeRetriever, cast(object, LocalRetriever()))
    service.public_reference_lookup = cast(PublicMedicalReferenceLookup, cast(object, PublicLookup()))
    service.fhir_context_service = cast(FHIRPatientContextService, cast(object, FHIRLookup()))

    state = cast(
        AgentState,
        cast(
            object,
            {
                "messages": [HumanMessage(content="I have chest tightness")],
                "patient_id": "patient-123",
            },
        ),
    )

    result = service._retrieve_node(state)

    assert result["retrieval_used"] is True
    assert "Grounded chunk" in result["retrieved_context"]
    assert "Public context" in result["retrieved_context"]
    assert "FHIR summary" in result["retrieved_context"]
    assert len(result["retrieved_sources"]) == 3
