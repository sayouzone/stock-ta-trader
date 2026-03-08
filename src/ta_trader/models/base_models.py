"""
ta_trader/models/base_models.py
투자 단계 기본 분석 결과 모델

StageStatus / CheckItem / StageResult (단계별 결과)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional


class StageStatus(Enum):
    """단계별 통과 상태"""
    PASS     = "통과"
    PARTIAL  = "부분충족"
    FAIL     = "미충족"
    MANUAL   = "수동확인"    # 자동 판별 불가 (촉매 등)
    NO_DATA  = "데이터없음"  # 재무 데이터 미제공 시

@dataclass
class CheckItem:
    """개별 체크 항목 결과"""
    name:        str                    # 항목명
    passed:      bool                   # 통과 여부
    value:       Optional[float] = None # 실제 측정값
    threshold:   Optional[float] = None # 임계값
    score:       float = 0.0            # 기여 점수
    description: str = ""               # 설명

@dataclass
class StageResult:
    """단계별 분석 결과"""
    stage_num:    int                         # 1~6
    stage_name:   str                         # 단계명
    status:       StageStatus                 # 통과 상태
    score:        float                       # 이 단계 점수
    max_score:    float                       # 이 단계 최대 점수
    checks:       list[CheckItem] = field(default_factory=list)
    description:  str = ""                    # 종합 설명

    @property
    def pass_rate(self) -> float:
        """통과 비율 (0.0~1.0)"""
        if not self.checks:
            return 0.0
        passed = sum(1 for c in self.checks if c.passed)
        return passed / len(self.checks)

    @property
    def score_pct(self) -> float:
        """점수 달성률 (%)"""
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0.0
