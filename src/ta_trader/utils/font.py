"""
ta_trader/utils/font.py
matplotlib 한글 폰트 설정 유틸리티

사용법:
    from ta_trader.utils.font import setup_korean_font
    setup_korean_font()   # plt.show() / plt.savefig() 호출 전 1회 실행
"""

from __future__ import annotations

import platform
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt


def setup_korean_font() -> str:
    """
    OS에 맞는 한글 폰트를 자동으로 설정합니다.

    Returns:
        적용된 폰트 이름

    동작 순서:
        1. OS 기본 한글 폰트 시도 (macOS: AppleGothic, Windows: Malgun Gothic, Linux: NanumGothic)
        2. 실패 시 시스템에 설치된 한글 폰트를 탐색
        3. 모두 실패 시 경고 출력
    """
    os_name = platform.system()

    # OS별 우선 후보 폰트
    candidates: list[str] = {
        "Darwin":  ["AppleGothic", "Apple SD Gothic Neo", "NanumGothic"],
        "Windows": ["Malgun Gothic", "맑은 고딕", "NanumGothic"],
        "Linux":   ["NanumGothic", "NanumBarunGothic", "UnDotum", "Noto Sans KR"],
    }.get(os_name, ["NanumGothic"])

    available = {f.name for f in mpl.font_manager.fontManager.ttflist}

    chosen = next((f for f in candidates if f in available), None)

    if chosen is None:
        # 폴백: 시스템 폰트 중 한글 포함 폰트 탐색
        chosen = _find_korean_font()

    if chosen:
        plt.rcParams["font.family"] = chosen
    else:
        warnings.warn(
            "한글 폰트를 찾지 못했습니다. "
            "NanumGothic 설치를 권장합니다.\n"
            "  macOS/Linux: brew install font-nanum-gothic\n"
            "  pip: pip install koreanize-matplotlib",
            stacklevel=2,
        )
        chosen = "sans-serif"

    # 마이너스 부호 깨짐 방지
    plt.rcParams["axes.unicode_minus"] = False

    return chosen


def _find_korean_font() -> str | None:
    """시스템 폰트 중 한글(NFC 유니코드 범위) 폰트를 탐색합니다."""
    keywords = ("nanum", "gothic", "gulim", "batang", "dotum", "malgun", "noto")
    for font in mpl.font_manager.fontManager.ttflist:
        if any(kw in font.name.lower() for kw in keywords):
            return font.name
    return None