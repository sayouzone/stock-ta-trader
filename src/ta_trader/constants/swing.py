"""
ta_trader/constants/swing.py
스윙 트레이딩 6단계 프로세스 전용 상수

단계별 파라미터:
  1. 시장 환경 판단
  2. 종목 스크리닝
  3. 진입 타이밍
  4. 포지션 사이징/리스크 관리
  5. 포지션 관리/익절
  6. 매매 복기
"""

# ── 1단계: 시장 환경 판단 ─────────────────────────────────
MARKET_ADX_TREND_THRESHOLD: float = 25.0     # ADX ≥ 25 → 추세 존재
MARKET_BULLISH_SMA200: bool = True           # SMA200 위 → 강세장

# ── 2단계: 종목 스크리닝 ──────────────────────────────────
SCREEN_VOL_SURGE_THRESHOLD: float = 1.5      # 150% 이상 거래량
SCREEN_VOL_STRONG_SURGE: float = 2.5         # 250% 이상 강한 급증
SCREEN_MIN_ADX: float = 20.0                 # 최소 ADX (횡보 제외)
SCREEN_RS_LOOKBACK_DAYS: int = 20            # 상대강도 산출 기간
SCREEN_RS_MIN_SCORE: float = 0.0             # RS > 0 (시장 대비 양호)
SCREEN_MA_TREND_MIN: int = 2                 # 최소 정배열 점수 (4점 만점)

# ── 3단계: 진입 타이밍 ────────────────────────────────────
# MACD
ENTRY_MACD_GOLDEN_CROSS: bool = True         # MACD 골든크로스 확인
ENTRY_MACD_ABOVE_ZERO_BONUS: float = 10.0    # MACD > 0 에서 골든크로스 보너스

# RSI
ENTRY_RSI_OVERSOLD_BOUNCE: float = 40.0      # RSI < 40 에서 반등 시작
ENTRY_RSI_RECOVERY_TARGET: float = 50.0      # RSI 50 복귀 = 모멘텀 회복

# 볼린저 밴드
ENTRY_BB_LOWER_BOUNCE: float = 0.2           # BB%B ≤ 0.2 + 반등
ENTRY_BB_SQUEEZE_BREAKOUT: float = 1.0       # BB%B ≥ 1.0 (상단 돌파)

# 피보나치
ENTRY_FIBO_GOLDEN_LOW: float = 0.382         # 골든존 하단
ENTRY_FIBO_GOLDEN_HIGH: float = 0.618        # 골든존 상단

# 진입 종합 점수 임계값
ENTRY_SCORE_STRONG_BUY: float = 70.0
ENTRY_SCORE_BUY: float = 40.0
ENTRY_SCORE_NEUTRAL: float = 20.0

# ── 4단계: 포지션 사이징 ──────────────────────────────────
POSITION_RISK_PER_TRADE_PCT: float = 0.02    # 1회 거래 최대 손실 = 자본의 2%
POSITION_ATR_SL_MULTIPLIER: float = 1.5      # 손절: 진입가 - 1.5 ATR
POSITION_ATR_TP_MULTIPLIER: float = 3.0      # 익절: 진입가 + 3.0 ATR
POSITION_MIN_RR_RATIO: float = 2.0           # 최소 R배수 (보상/위험 ≥ 2.0)
POSITION_MAX_PORTFOLIO_PCT: float = 0.2      # 단일 종목 최대 비중 20%
POSITION_DEFAULT_CAPITAL: float = 10_000_000 # 기본 자본금 1000만원

# ── 5단계: 포지션 관리/익절 ───────────────────────────────
EXIT_TRAILING_ATR_MULTIPLIER: float = 2.0    # 트레일링: 종가 - 2.0 ATR
EXIT_RSI_OVERBOUGHT: float = 70.0            # RSI ≥ 70 → 1차 익절
EXIT_RSI_EXTREME: float = 80.0               # RSI ≥ 80 → 적극 익절
EXIT_MACD_DEAD_CROSS: bool = True            # MACD 데드크로스 → 청산
EXIT_BB_UPPER_TOUCH: float = 0.95            # BB%B ≥ 0.95 → 1차 익절
EXIT_PARTIAL_SELL_RATIO: float = 0.5         # 1차 익절 시 50% 매도
EXIT_FIBO_TARGET_LEVEL: float = 1.618        # 피보나치 161.8% 목표가

# ── 6단계: 매매 복기 ──────────────────────────────────────
JOURNAL_FIELDS: list[str] = [
    "ticker", "name", "entry_date", "exit_date",
    "entry_price", "exit_price", "entry_signal",
    "pnl_pct", "r_multiple", "market_regime",
    "strategy", "notes",
]

# ── 단계별 최대 점수 ──────────────────────────────────────
STEP1_MAX_SCORE: float = 100.0    # 시장 환경
STEP2_MAX_SCORE: float = 100.0    # 종목 스크리닝
STEP3_MAX_SCORE: float = 100.0    # 진입 타이밍
STEP4_MAX_SCORE: float = 100.0    # 리스크 관리
STEP5_MAX_SCORE: float = 100.0    # 익절 전략
