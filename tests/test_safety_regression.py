import importlib


_safety = importlib.import_module("app.services.safety")
TriageLevel = _safety.TriageLevel
sanitize_output = _safety.sanitize_output
triage_message = _safety.triage_message


def test_triage_red_detects_emergency_combination():
    """응급 증상 조합이 RED triage로 분류되는지 확인한다."""
    decision = triage_message("Chest pain with shortness of breath for 2 hours")
    assert decision.level is TriageLevel.RED
    assert any("emergency" in reason for reason in decision.reasons)


def test_triage_red_detects_standalone_english_respiratory_distress():
    """단독 호흡 곤란 표현이 GREEN으로 빠지지 않는지 확인한다."""
    decision = triage_message("I can't breathe right now")
    assert decision.level is TriageLevel.RED
    assert any("respiratory" in reason for reason in decision.reasons)


def test_triage_red_detects_standalone_korean_respiratory_distress():
    """한국어 단독 호흡 곤란 표현이 GREEN으로 빠지지 않는지 확인한다."""
    decision = triage_message("지금 숨이 안 쉬어져")
    assert decision.level is TriageLevel.RED
    assert any("respiratory" in reason for reason in decision.reasons)


def test_triage_red_detects_korean_self_harm_language():
    """한국어 자해/자살 위기 표현이 GREEN으로 빠지지 않는지 확인한다."""
    cases = [
        "죽어야겠어",
        "죽어야겠다고 생각해",
        "죽고 싶어",
        "극단적 선택을 하고 싶어",
        "살기 싫어",
        "사라지고 싶어",
    ]

    for message in cases:
        decision = triage_message(message)
        assert decision.level is TriageLevel.RED, message
        assert any("self-harm" in reason for reason in decision.reasons), message


def test_triage_red_detects_english_self_harm_language():
    """영어 자해/자살 위기 표현이 GREEN으로 빠지지 않는지 확인한다."""
    cases = [
        "I want to die",
        "I should die",
        "I don't want to live",
        "I wish I were dead",
    ]

    for message in cases:
        decision = triage_message(message)
        assert decision.level is TriageLevel.RED, message
        assert any("self-harm" in reason for reason in decision.reasons), message


def test_triage_amber_detects_fever():
    """지속적인 발열 증상이 AMBER triage로 분류되는지 확인한다."""
    decision = triage_message("I have had high fever for 3 days and keep vomiting")
    assert decision.level is TriageLevel.AMBER
    assert decision.reasons


def test_triage_green_default():
    """일반 메시지가 기본적으로 GREEN triage가 되는지 확인한다."""
    decision = triage_message("I enjoyed a walk outside and feel relaxed.")
    assert decision.level is TriageLevel.GREEN
    assert decision.reasons == []


def test_sanitizer_redacts_keys_and_flags():
    """노출된 키가 마스킹되고 표시되는지 확인한다."""
    message = "Here is my api key: sk-SECRET123456"
    sanitized, changed, reasons = sanitize_output(message)
    assert changed is True
    assert sanitized.endswith("[REDACTED]")
    assert reasons
