"""
ta_trader/growth — 100% 상승 후보 발굴 6단계 분석 모듈

사용 예:
    from ta_trader.growth import GrowthMomentumAnalyzer, format_growth_result

    result = GrowthMomentumAnalyzer("NVDA").analyze()
    print(format_growth_result(result))
"""

from ta_trader.formatters.growth import format_growth_report, format_growth_result

__all__ = [
    "format_growth_report",
    "format_growth_result",
]
