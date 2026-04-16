from dataclasses import dataclass
from enum import Enum
import re


class TriageLevel(str, Enum):
    RED = "RED"
    AMBER = "AMBER"
    GREEN = "GREEN"


@dataclass
class TriageDecision:
    level: TriageLevel
    reasons: list[str]


_SECURITY_RED_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"reveal\s+(?:the\s+)?system\s+prompt",
    r"api\s*key",
    r"token\s*(?:value)?",
    r"password",
    r"secret\s*key",
]

_CRISIS_PATTERNS = [
    (
        r"\b("
        r"suicide|kill\s+myself|end\s+my\s+life|self-harm|"
        r"want\s+to\s+die|should\s+die|wish\s+i\s+were\s+dead|"
        r"don'?t\s+want\s+to\s+live|do\s+not\s+want\s+to\s+live|"
        r"better\s+off\s+dead"
        r")\b",
        "self-harm crisis signal",
    ),
    (
        r"(자해|죽고\s*싶|죽어야겠|죽는\s*게\s*낫|살기\s*싫|살고\s*싶지\s*않|"
        r"없어지고\s*싶|사라지고\s*싶|극단적\s*선택)",
        "self-harm crisis signal",
    ),
]

_RESPIRATORY_RED_PATTERNS = [
    (r"\b(i\s+can't\s+breathe|cannot\s+breathe|struggling\s+to\s+breathe|trouble\s+breathing)\b", "possible respiratory distress"),
    (r"\b(shortness\s+of\s+breath)\b", "possible respiratory distress"),
    (r"(숨\s*이\s*안\s*쉬어|숨\s*을\s*못\s*쉬|호흡\s*이\s*안\s*돼|숨쉬기\s*힘들|호흡\s*곤란)", "possible respiratory distress"),
]

_EMERGENCY_COMBINATIONS = [
    (
        [r"\b(chest\s+pain|pressure\s+in\s+chest)\b", r"\b(shortness\s+of\s+breath|can't\s+breathe)\b"],
        "possible cardiopulmonary emergency",
    ),
    ([r"\b(half\s+body\s+weakness|one-sided\s+weakness)\b", r"\b(slurred\s+speech|can't\s+speak)\b"], "possible stroke symptoms"),
    ([r"\b(가슴\s*통증|흉통)\b", r"\b(호흡\s*곤란|숨\s*이\s*안\s*쉬어|숨차)\b"], "possible cardiopulmonary emergency"),
    ([r"\b(한쪽\s*마비|편측\s*마비)\b", r"\b(말\s*이\s*어눌|발음\s*이\s*이상)\b"], "possible stroke symptoms"),
]

_AMBER_PATTERNS = [
    (r"\b(high\s+fever|fever\s+for\s+\d+\s*days?)\b", "persistent fever pattern"),
    (r"\b(severe\s+abdominal\s+pain|blood\s+in\s+stool|blood\s+in\s+urine)\b", "possible urgent physical symptom"),
    (r"\b(persistent\s+vomiting|fainting|passed\s+out)\b", "possible urgent physical symptom"),
    (r"(고열(?=$|[\s.,!?]|[이가은는을를도만에로와과])|열이\s*(?:\d+일\s*째|사흘째)|지속되는\s*열)", "persistent fever pattern"),
    (r"(심한\s*복통|혈변|혈뇨|실신[가-힣]*|기절[가-힣]*|계속\s*구토)", "possible urgent physical symptom"),
    (r"\b(bypass|exploit|payload|privilege\s+escalation|sql\s+injection)\b", "suspicious security language"),
    (r"\b(allergic\s+reaction|swelling\s+of\s+(throat|face|tongue)|difficulty\s+swallowing)\b", "possible allergic reaction"),
    (r"(알레르기\s*반응|목\s*부종|얼굴\s*부종|혀\s*부종|목\s*이?\s*부(?:어|었)|혀\s*(?:가|이)?\s*붓[가-힣]*|얼굴\s*(?:이|가)?\s*붓[가-힣]*[^.?!\n]{0,40}입술\s*(?:이|가)?\s*따끔거[가-힣]*|입술\s*(?:이|가)?\s*(?:붓[가-힣]*|부(?:어|었|은)[가-힣]*|부어오르[가-힣]*)[^.?!\n]{0,40}(?:입[^\S\n]*안\s*(?:이|가)?\s*(?:따끔거|간질거|가려|얼얼)[가-힣]*|간질간질[가-힣]*)|삼키기\s*어려|넘기기\s*힘들|음식\s*알레르기)", "possible allergic reaction"),
]


def triage_message(message: str) -> TriageDecision:
    """사용자 메시지를 RED, AMBER, GREEN 단계로 분류한다."""
    normalized = message.lower()

    red_reasons: list[str] = []
    for pattern in _SECURITY_RED_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            red_reasons.append("safety-sensitive prompt override or secret request")
            break

    for pattern, reason in _CRISIS_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            red_reasons.append(reason)

    for pattern, reason in _RESPIRATORY_RED_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            red_reasons.append(reason)

    for required_patterns, reason in _EMERGENCY_COMBINATIONS:
        if all(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in required_patterns):
            red_reasons.append(reason)

    if red_reasons:
        return TriageDecision(level=TriageLevel.RED, reasons=list(dict.fromkeys(red_reasons)))

    amber_reasons = [
        reason
        for pattern, reason in _AMBER_PATTERNS
        if re.search(pattern, normalized, flags=re.IGNORECASE)
    ]
    if amber_reasons:
        return TriageDecision(level=TriageLevel.AMBER, reasons=list(dict.fromkeys(amber_reasons)))

    return TriageDecision(level=TriageLevel.GREEN, reasons=[])


_SANITIZE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9]{10,}"), "possible sk key"),
    (re.compile(r"(api\s*key\s*:\s*)([^\s]+)", re.IGNORECASE), "api key prefix"),
    (re.compile(r"(password\s*:\s*)([^\s]+)", re.IGNORECASE), "password prefix"),
    (re.compile(r"(token\s*:\s*)([^\s]+)", re.IGNORECASE), "token prefix"),
]


def sanitize_output(text: str) -> tuple[str, bool, list[str]]:
    """민감한 출력 패턴을 가리고 변경 여부를 함께 반환한다."""
    sanitized = text
    reasons: list[str] = []

    for pattern, reason in _SANITIZE_PATTERNS:
        def _replace(match: re.Match[str]) -> str:
            """민감한 값을 마스킹된 문자열로 치환한다."""
            reasons.append(reason)
            if match.lastindex:
                return f"{match.group(1)}[REDACTED]"
            return "[REDACTED]"

        sanitized, _ = pattern.subn(_replace, sanitized)

    changed = sanitized != text
    return sanitized, changed, list(dict.fromkeys(reasons))
