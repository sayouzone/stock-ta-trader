"""
ta_trader/exceptions.py
커스텀 예외 계층 정의
"""


class TATraderError(Exception):
    """TA Trader 기본 예외 클래스"""


class DataFetchError(TATraderError):
    """데이터 수집 실패"""


class InsufficientDataError(TATraderError):
    """지표 계산에 필요한 최소 데이터 부족"""


class InvalidTickerError(TATraderError):
    """유효하지 않은 티커 심볼"""


class IndicatorCalculationError(TATraderError):
    """지표 계산 중 오류"""


class ConfigurationError(TATraderError):
    """설정 파일 오류"""
