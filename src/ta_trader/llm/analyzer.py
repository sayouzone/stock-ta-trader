"""
ta_trader/llm/analyzer.py
하위 호환성 유지용 모듈 (Deprecated)

이 모듈은 이전 코드와의 호환성을 위해 유지됩니다.
신규 코드에서는 아래를 사용하세요:

    from ta_trader.llm.factory import create_llm_analyzer          # 권장
    from ta_trader.llm.anthropic_analyzer import AnthropicAnalyzer # 직접 지정
    from ta_trader.llm.google_analyzer import GoogleAnalyzer       # 직접 지정
"""

from ta_trader.llm.anthropic_analyzer import AnthropicAnalyzer

# 기존 코드 호환: LLMAnalyzer → AnthropicAnalyzer
LLMAnalyzer = AnthropicAnalyzer

__all__ = ["LLMAnalyzer", "AnthropicAnalyzer"]