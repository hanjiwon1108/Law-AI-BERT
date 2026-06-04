import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RiskInfo:
    category: str
    severity: str
    keywords: List[str]
    explanation: str
    questions: List[str]


RISK_INFOS: List[RiskInfo] = [
    RiskInfo("과도한 위약금", "high", ["위약금", "손해배상", "배상금", "벌금", "지체상금", "일체의 손해"], "해지나 의무 불이행 시 금전 부담이 크게 발생할 수 있습니다.", ["금액 산정 기준이 명확한가?", "실제 손해보다 과도한 금액은 아닌가?", "상대방도 같은 수준의 책임을 지는가?"]),
    RiskInfo("자동 연장", "medium", ["자동 연장", "자동 갱신", "갱신되는 것으로 본다", "통지하지 않는 경우", "동일 조건으로 연장"], "사용자가 종료 의사를 놓치면 원하지 않는 계약이 계속될 수 있습니다.", ["해지 통지 기한이 충분한가?", "자동 연장 전 별도 안내가 있는가?", "연장 후 해지 방법이 명확한가?"]),
    RiskInfo("책임 면책", "high", ["책임을 지지 않는다", "면책", "배상하지 않는다", "책임이 없다", "어떠한 책임도", "손해에 대하여 책임"], "상대방의 책임이 과도하게 제한되면 손해가 발생해도 구제받기 어려울 수 있습니다.", ["고의 또는 중대한 과실까지 면책되는가?", "손해 발생 시 보상 절차가 있는가?", "책임 제한 범위가 구체적인가?"]),
    RiskInfo("일방적 변경", "high", ["임의로 변경", "사전 통지 없이", "일방적으로 변경", "변경할 수 있다", "회사 사정에 따라", "별도 동의 없이"], "계약 조건이 한쪽 당사자에게 유리하게 바뀔 수 있습니다.", ["변경 시 사전 통지와 동의 절차가 있는가?", "변경을 거부할 권리가 있는가?", "변경 가능한 범위가 제한되어 있는가?"]),
    RiskInfo("일방적 해지", "medium", ["즉시 해지", "언제든지", "일방적으로 해지", "계약을 해제할 수 있다", "통보만으로"], "상대방이 계약을 쉽게 종료할 수 있으면 대금, 업무, 거주 안정성이 흔들릴 수 있습니다.", ["해지 사유가 구체적인가?", "해지 전 시정 기회가 있는가?", "해지 시 정산 기준이 명확한가?"]),
    RiskInfo("권리 귀속", "medium", ["모든 권리", "권리가 귀속", "저작권", "지식재산권", "양도", "무상으로 사용"], "결과물이나 권리가 예상보다 넓게 이전될 수 있습니다.", ["이전되는 권리 범위가 명확한가?", "대가가 권리 이전 범위에 비례하는가?", "포트폴리오 사용 가능 여부가 정해져 있는가?"]),
    RiskInfo("지급 지연", "medium", ["검수 후 지급", "사정에 따라", "지급을 보류", "추후 지급", "정산 후 지급", "지급하지 않을 수 있다"], "대금 지급 시점이 불명확하면 현금 흐름과 분쟁 위험이 커질 수 있습니다.", ["검수 기간이 정해져 있는가?", "지급 기한이 날짜로 명확한가?", "보류 사유와 이의 제기 절차가 있는가?"]),
    RiskInfo("경업 금지", "high", ["경업 금지", "동종 업계", "취업할 수 없다", "거래할 수 없다", "영업을 할 수 없다", "경쟁 업체"], "계약 종료 후 직업 선택이나 영업 활동이 제한될 수 있습니다.", ["제한 기간과 지역이 합리적인가?", "보상 조항이 있는가?", "제한 대상 업무가 과도하게 넓지 않은가?"]),
    RiskInfo("관할 및 분쟁", "low", ["전속 관할", "관할 법원", "중재", "소송", "분쟁", "소송 비용"], "분쟁이 생겼을 때 사용자가 불리한 장소나 절차를 따라야 할 수 있습니다.", ["관할지가 사용자에게 과도하게 불리하지 않은가?", "중재 절차와 비용을 이해했는가?", "분쟁 해결 절차가 균형적인가?"]),
]


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_clauses(text: str) -> List[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    lines = [line.strip() for line in re.split(r"\n+", normalized) if line.strip()]
    clauses: List[str] = []
    buffer = ""

    for line in lines:
        starts_new = re.match(r"^(제\s*\d+\s*조|\d+\.|\(\d+\)|[가-하]\.)", line) is not None
        if starts_new and buffer:
            clauses.append(buffer.strip())
            buffer = line
        elif buffer:
            buffer = f"{buffer} {line}"
        else:
            buffer = line

    if buffer:
        clauses.append(buffer.strip())

    if len(clauses) <= 1:
        clauses = [
            clause.strip()
            for clause in re.split(r"(?<=[.다])\s+(?=(제\s*\d+\s*조|\d+\.|\(\d+\)|[가-힣A-Za-z]))", normalized)
            if clause.strip() and len(clause.strip()) > 8
        ]

    return clauses


def infer_category(text: str) -> Dict[str, object]:
    matched = []
    for info in RISK_INFOS:
        evidence = [keyword for keyword in info.keywords if keyword in text]
        if evidence:
            matched.append((info, evidence))

    if not matched:
        return {
            "category": "BERT 위험 조항",
            "severity": "medium",
            "evidence": [],
            "explanation": "BERT 모델이 문맥상 위험 가능성이 있는 조항으로 분류했습니다.",
            "questions": ["계약상 불리한 의무나 권리 제한이 있는지 확인하세요.", "상대방에게만 유리한 조건인지 확인하세요."],
        }

    selected = matched[0][0]
    evidence = sorted({keyword for _, keywords in matched for keyword in keywords})
    return {
        "category": selected.category,
        "severity": selected.severity,
        "evidence": evidence,
        "explanation": selected.explanation,
        "questions": selected.questions,
    }


def risk_level(score: int) -> Dict[str, str]:
    if score >= 60:
        return {"label": "높은 위험", "tone": "high"}
    if score >= 30:
        return {"label": "주의 필요", "tone": "medium"}
    if score > 0:
        return {"label": "낮은 위험", "tone": "low"}
    return {"label": "위험 낮음", "tone": "low"}
