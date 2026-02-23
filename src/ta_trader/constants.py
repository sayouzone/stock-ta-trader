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

# ── 체제 판별 임계값 ──────────────────────────────────────
BB_BANDWIDTH_SQUEEZE: float = 4.0     # BandWidth ≤ 4% → 스퀴즈(변동성 수축)
BB_BANDWIDTH_EXPAND: float = 10.0     # BandWidth ≥ 10% → 변동성 확대

# ── 추세추종 전략 가중치 (합계 = 100) ─────────────────────
STRATEGY_TREND_ADX: int   = 25
STRATEGY_TREND_RSI: int   = 15
STRATEGY_TREND_MACD: int  = 45
STRATEGY_TREND_BB: int    = 15

# ── 평균회귀 전략 가중치 (합계 = 100) ─────────────────────
STRATEGY_REVERT_ADX: int  = 5
STRATEGY_REVERT_RSI: int  = 40
STRATEGY_REVERT_MACD: int = 15
STRATEGY_REVERT_BB: int   = 40

# ── 돌파모멘텀 전략 가중치 (합계 = 100) ───────────────────
STRATEGY_BREAKOUT_ADX: int  = 30
STRATEGY_BREAKOUT_RSI: int  = 20
STRATEGY_BREAKOUT_MACD: int = 30
STRATEGY_BREAKOUT_BB: int   = 20

# ── 추세추종: MACD 크로스 보너스 ──────────────────────────
TREND_MACD_CROSS_BONUS: float = 15.0
TREND_DI_CONFIRM_BONUS: float = 10.0

# ── 평균회귀: BB 반등 보너스 ──────────────────────────────
REVERT_BB_BOUNCE_BONUS: float = 15.0
REVERT_RSI_REVERSAL_BONUS: float = 10.0

# ── 돌파모멘텀: 스퀴즈 돌파 보너스 ────────────────────────
BREAKOUT_SQUEEZE_BONUS: float = 20.0
BREAKOUT_VOLUME_BONUS: float = 10.0

# ── 데이터 수집 기본값 ────────────────────────────────────
DEFAULT_PERIOD: str = "6mo"
DEFAULT_INTERVAL: str = "1d"
MIN_DATA_ROWS: int = 50            # 지표 계산에 필요한 최소 데이터 수

# ── 파일 경로 ─────────────────────────────────────────────
DEFAULT_WATCHLIST_PATH: str = "configs/watchlist.yaml"
DEFAULT_REPORT_DIR: str = "reports"
DEFAULT_LOG_DIR: str = "logs"
