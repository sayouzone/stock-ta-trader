"""
ta_trader/constants.py
모든 상수 정의 (매직 넘버 금지 원칙)
"""

# ── 지표 계산 파라미터 ─────────────────────────────────────
ADX_WINDOW: int = 14
RSI_WINDOW: int = 14
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL_PERIOD: int = 9
BB_WINDOW: int = 20
BB_STD_DEV: float = 2.0

# ── ADX 임계값 ────────────────────────────────────────────
ADX_STRONG_TREND: float = 25.0
ADX_WEAK_TREND: float = 20.0

# ── RSI 임계값 ────────────────────────────────────────────
RSI_OVERBOUGHT: float = 70.0
RSI_OVERSOLD: float = 30.0
RSI_UPPER_NEUTRAL: float = 60.0
RSI_LOWER_NEUTRAL: float = 40.0

# ── Bollinger Bands 임계값 ────────────────────────────────
BB_UPPER_THRESHOLD: float = 0.8   # %B ≥ 0.8 → 과매수
BB_LOWER_THRESHOLD: float = 0.2   # %B ≤ 0.2 → 과매도

# ── 신호 점수 임계값 (-100 ~ +100) ───────────────────────
SCORE_STRONG_BUY: float = 60.0
SCORE_BUY: float = 20.0
SCORE_SELL: float = -20.0
SCORE_STRONG_SELL: float = -60.0

# ── 기본 가중치 (합계 = 100) ──────────────────────────────
WEIGHT_ADX_DEFAULT: int = 20
WEIGHT_RSI_DEFAULT: int = 30
WEIGHT_MACD_DEFAULT: int = 30
WEIGHT_BB_DEFAULT: int = 20

# ── 추세장 가중치 (ADX ≥ STRONG_TREND) ───────────────────
WEIGHT_ADX_TREND: int = 25
WEIGHT_RSI_TREND: int = 25
WEIGHT_MACD_TREND: int = 35
WEIGHT_BB_TREND: int = 15

# ── 횡보장 가중치 (ADX < WEAK_TREND) ─────────────────────
WEIGHT_ADX_SIDEWAYS: int = 10
WEIGHT_RSI_SIDEWAYS: int = 35
WEIGHT_MACD_SIDEWAYS: int = 25
WEIGHT_BB_SIDEWAYS: int = 30

# ── 리스크 관리 ───────────────────────────────────────────
ATR_STOP_LOSS_MULTIPLIER: float = 1.5
ATR_TAKE_PROFIT_MULTIPLIER: float = 3.0
DEFAULT_STOP_LOSS_PCT: float = 0.03    # 3%
DEFAULT_TAKE_PROFIT_PCT: float = 0.05  # 5%

# ── 데이터 수집 기본값 ────────────────────────────────────
DEFAULT_PERIOD: str = "6mo"
DEFAULT_INTERVAL: str = "1d"
MIN_DATA_ROWS: int = 50            # 지표 계산에 필요한 최소 데이터 수

# ── 파일 경로 ─────────────────────────────────────────────
DEFAULT_WATCHLIST_PATH: str = "configs/watchlist.yaml"
DEFAULT_REPORT_DIR: str = "reports"
DEFAULT_LOG_DIR: str = "logs"
