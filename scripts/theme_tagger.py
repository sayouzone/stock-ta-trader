"""
ta_trader/data/theme_tagger.py
2025-2026 핵심 주도 테마 태깅 (한국 + 미국 공통)

핵심 6개 테마 (시장 주도 + 박병창식 강세 테마 매매용):
    1. AI_SEMI       AI반도체   - AI 가속기/GPU/HBM/반도체 장비
    2. AI_INFRA      AI인프라   - 데이터센터/서버/네트워킹/전력기기
    3. NUCLEAR_POWER 원전전력   - 원전/SMR/전력 (AI 전력수요 수혜)
    4. ROBOT         로봇      - 휴머노이드/로봇 부품
    5. DEFENSE_SPACE 방산우주   - 국방/항공우주/위성
    6. QUANTUM       양자컴퓨팅  - 양자컴퓨터 HW/SW

특징:
    - 테마는 섹터를 가로지르는 별도 축 → 한 종목이 여러 테마 가질 수 있음
    - 다중 테마는 세미콜론(;)으로 구분
    - 명시 매핑(high) 위주, 키워드는 보조(medium/low)
    - 테마 편입은 주관적이므로 신뢰도 표시
"""

from __future__ import annotations

from enum import Enum


class Theme(Enum):
    AI_SEMI = "AI반도체"
    AI_INFRA = "AI인프라"
    NUCLEAR_POWER = "원전전력"
    ROBOT = "로봇"
    DEFENSE_SPACE = "방산우주"
    QUANTUM = "양자컴퓨팅"


THEME_EXPLICIT: dict[str, dict[Theme, str]] = {
    # ═══════════ 미국 ═══════════
    "NVDA": {Theme.AI_SEMI: "high"}, "AVGO": {Theme.AI_SEMI: "high"},
    "AMD": {Theme.AI_SEMI: "high"}, "TSM": {Theme.AI_SEMI: "high"},
    "MU": {Theme.AI_SEMI: "high"}, "ASML": {Theme.AI_SEMI: "high"},
    "AMAT": {Theme.AI_SEMI: "high"}, "LRCX": {Theme.AI_SEMI: "high"},
    "KLAC": {Theme.AI_SEMI: "high"}, "MRVL": {Theme.AI_SEMI: "high"},
    "ARM": {Theme.AI_SEMI: "high"}, "QCOM": {Theme.AI_SEMI: "medium"},
    "MBLY": {Theme.AI_SEMI: "medium"},
    "SMCI": {Theme.AI_INFRA: "high"}, "DELL": {Theme.AI_INFRA: "high"},
    "ANET": {Theme.AI_INFRA: "high"}, "VRT": {Theme.AI_INFRA: "high"},
    "CIEN": {Theme.AI_INFRA: "medium"}, "GLW": {Theme.AI_INFRA: "medium"},
    "CSCO": {Theme.AI_INFRA: "medium"}, "ETN": {Theme.AI_INFRA: "high"},
    "PWR": {Theme.AI_INFRA: "medium"},
    "GEV": {Theme.AI_INFRA: "high", Theme.NUCLEAR_POWER: "high"},
    "VST": {Theme.NUCLEAR_POWER: "high"}, "CEG": {Theme.NUCLEAR_POWER: "high"},
    "NEE": {Theme.NUCLEAR_POWER: "medium"}, "SO": {Theme.NUCLEAR_POWER: "medium"},
    "OKLO": {Theme.NUCLEAR_POWER: "high"}, "SMR": {Theme.NUCLEAR_POWER: "high"},
    "CCJ": {Theme.NUCLEAR_POWER: "high"}, "UEC": {Theme.NUCLEAR_POWER: "high"},
    "TSLA": {Theme.ROBOT: "medium"}, "ISRG": {Theme.ROBOT: "medium"},
    "TER": {Theme.AI_SEMI: "medium", Theme.ROBOT: "medium"},
    "LMT": {Theme.DEFENSE_SPACE: "high"}, "RTX": {Theme.DEFENSE_SPACE: "high"},
    "NOC": {Theme.DEFENSE_SPACE: "high"}, "GD": {Theme.DEFENSE_SPACE: "high"},
    "LHX": {Theme.DEFENSE_SPACE: "high"}, "BA": {Theme.DEFENSE_SPACE: "medium"},
    "PLTR": {Theme.DEFENSE_SPACE: "medium", Theme.AI_INFRA: "medium"},
    "RKLB": {Theme.DEFENSE_SPACE: "high"}, "LUNR": {Theme.DEFENSE_SPACE: "high"},
    "RDW": {Theme.DEFENSE_SPACE: "high"}, "TDG": {Theme.DEFENSE_SPACE: "medium"},
    "RGTI": {Theme.QUANTUM: "high"}, "QBTS": {Theme.QUANTUM: "high"},
    "IONQ": {Theme.QUANTUM: "high"}, "QUBT": {Theme.QUANTUM: "high"},
    "ARQQ": {Theme.QUANTUM: "high"},
    # ═══════════ 한국 ═══════════
    "005930.KS": {Theme.AI_SEMI: "high"}, "000660.KS": {Theme.AI_SEMI: "high"},
    "042700.KS": {Theme.AI_SEMI: "high"}, "000990.KS": {Theme.AI_SEMI: "high"},
    "240810.KQ": {Theme.AI_SEMI: "high"}, "036930.KQ": {Theme.AI_SEMI: "high"},
    "403870.KQ": {Theme.AI_SEMI: "high"}, "058470.KQ": {Theme.AI_SEMI: "high"},
    "357780.KQ": {Theme.AI_SEMI: "high"}, "005290.KQ": {Theme.AI_SEMI: "high"},
    "166090.KQ": {Theme.AI_SEMI: "high"}, "095610.KQ": {Theme.AI_SEMI: "medium"},
    "140860.KQ": {Theme.AI_SEMI: "medium"}, "039030.KQ": {Theme.AI_SEMI: "medium"},
    "007660.KS": {Theme.AI_SEMI: "high", Theme.AI_INFRA: "high"},
    "267260.KS": {Theme.AI_INFRA: "high"}, "010120.KS": {Theme.AI_INFRA: "high"},
    "103590.KS": {Theme.AI_INFRA: "high"}, "062040.KS": {Theme.AI_INFRA: "medium"},
    "298040.KS": {Theme.AI_INFRA: "high"},
    "034020.KS": {Theme.NUCLEAR_POWER: "high"}, "051600.KS": {Theme.NUCLEAR_POWER: "high"},
    "052690.KS": {Theme.NUCLEAR_POWER: "high"}, "015760.KS": {Theme.NUCLEAR_POWER: "medium"},
    "336260.KS": {Theme.NUCLEAR_POWER: "medium"},
    "454910.KS": {Theme.ROBOT: "high"}, "090360.KQ": {Theme.ROBOT: "high"},
    "277810.KQ": {Theme.ROBOT: "high"}, "056080.KQ": {Theme.ROBOT: "high"},
    "108490.KQ": {Theme.ROBOT: "high"}, "348340.KQ": {Theme.ROBOT: "high"},
    "389500.KQ": {Theme.ROBOT: "high"}, "160190.KQ": {Theme.ROBOT: "medium"},
    "012450.KS": {Theme.DEFENSE_SPACE: "high"}, "079550.KS": {Theme.DEFENSE_SPACE: "high"},
    "047810.KS": {Theme.DEFENSE_SPACE: "high"}, "272210.KS": {Theme.DEFENSE_SPACE: "high"},
    "064350.KS": {Theme.DEFENSE_SPACE: "high"}, "099320.KQ": {Theme.DEFENSE_SPACE: "medium"},
}

THEME_KEYWORD_RULES: list[tuple[str, Theme, str]] = [
    ("양자", Theme.QUANTUM, "high"),
    ("Quantum", Theme.QUANTUM, "medium"),
    ("로보", Theme.ROBOT, "high"),
    ("로봇", Theme.ROBOT, "high"),
    ("Robotics", Theme.ROBOT, "high"),
    ("우주항공", Theme.DEFENSE_SPACE, "high"),
    ("Aerospace", Theme.DEFENSE_SPACE, "high"),
    ("Defense", Theme.DEFENSE_SPACE, "high"),
    ("SpaceMobile", Theme.DEFENSE_SPACE, "medium"),
    ("원자력", Theme.NUCLEAR_POWER, "high"),
    ("Nuclear", Theme.NUCLEAR_POWER, "high"),
    ("Uranium", Theme.NUCLEAR_POWER, "high"),
    ("SMR", Theme.NUCLEAR_POWER, "medium"),
]

# 키워드 오태깅 방지
THEME_KEYWORD_EXCLUDE: set[str] = {
    "006340.KS",  # 대원전선 ("원전" 부분문자열 방지) - 실제로는 '원자력' 키워드라 무관하나 안전장치
    "001440.KS",  # 대한전선
}


def tag_themes(ticker: str, name: str, sector: str = "") -> dict[Theme, str]:
    """단일 종목 테마 태깅. {Theme: confidence} 반환."""
    themes: dict[Theme, str] = {}
    if ticker in THEME_EXPLICIT:
        themes.update(THEME_EXPLICIT[ticker])
    if ticker not in THEME_KEYWORD_EXCLUDE:
        for kw, theme, conf in THEME_KEYWORD_RULES:
            if kw.lower() in name.lower():
                if theme not in themes:
                    themes[theme] = conf
    # ETF는 테마 신뢰도 한 단계 낮춤 (직접 보유 아님)
    if sector == "ETF/기타" and themes:
        themes = {t: ("low" if c == "high" else c) for t, c in themes.items()}
    return themes


def format_themes(themes: dict[Theme, str]) -> tuple[str, str]:
    """테마 dict → CSV 문자열. Returns (theme_str, confidence_str)."""
    if not themes:
        return "", ""
    names = ";".join(t.value for t in themes)
    confs = ";".join(themes[t] for t in themes)
    return names, confs
