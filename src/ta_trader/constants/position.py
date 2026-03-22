"""
ta_trader/constants/position.py
포지션 트레이딩 7단계 프로세스 전용 상수

단계별 파라미터:
  1. 시장 환경 판단  (200MA, ADL, 변동성)
  2. 섹터/테마 선정  (섹터 RS, 자금 흐름)
  3. 종목 선정       (RS, Stage 2, ADX, 52주 신고가)
  4. 매수 타이밍     (MA Pullback, Breakout, MACD, BB Squeeze)
  5. 리스크 관리     (ATR 손절, 포지션 사이징)
  6. 보유 관리       (트레일링 스톱, 피라미딩)
  7. 매도/청산       (MA 이탈, 다이버전스, ADX 하락)
"""

# ── 1단계: 시장 환경 판단 ─────────────────────────────────
MARKET_SMA200_BULLISH: bool = True               # 가격 > SMA200 → 강세장
MARKET_ADX_TREND_THRESHOLD: float = 25.0          # ADX ≥ 25 → 추세 존재
MARKET_MA_TREND_MIN: int = 3                      # 정배열 점수 ≥ 3 → 강세
MARKET_ATR_PCT_HIGH: float = 4.0                  # ATR% ≥ 4 → 고변동성
MARKET_VOLATILITY_STABLE_MAX: float = 3.5         # ATR% < 3.5 → 안정적 변동성

# ── 2단계: 섹터/테마 선정 ─────────────────────────────────
SECTOR_RS_LOOKBACK_DAYS: int = 60                 # 섹터 RS 산출 기간 (3개월)
SECTOR_RS_MIN_SCORE: float = 5.0                  # 섹터 RS 최소 기준 (%)
SECTOR_FUND_FLOW_LOOKBACK: int = 20               # 자금 흐름 관찰 기간

# ── 3단계: 종목 선정 ──────────────────────────────────────
SCREEN_RS_LOOKBACK_DAYS: int = 60                 # 종목 RS 산출 기간 (3개월)
SCREEN_RS_MIN_SCORE: float = 5.0                  # RS > 5% (시장 대비 강한 종목)
SCREEN_MIN_ADX: float = 25.0                      # ADX ≥ 25 (명확한 추세)
SCREEN_MA_TREND_MIN: int = 3                      # 정배열 ≥ 3 (Stage 2)
SCREEN_ABOVE_SMA50: bool = True                   # 가격 > SMA50
SCREEN_ABOVE_SMA200: bool = True                  # 가격 > SMA200
SCREEN_NEAR_52W_HIGH_PCT: float = 0.90            # 52주 고가 대비 90% 이상
SCREEN_VOL_SURGE_THRESHOLD: float = 1.5           # 150% 이상 거래량
SCREEN_MIN_CHECKS: int = 4                        # 최소 통과 기준

# ── 4단계: 매수 타이밍 ────────────────────────────────────
# MA Pullback 매수
ENTRY_PULLBACK_MA20_BOUNCE: bool = True           # 20일 MA 지지 반등
ENTRY_PULLBACK_MA50_BOUNCE: bool = True           # 50일 MA 지지 반등
ENTRY_PULLBACK_TOLERANCE_PCT: float = 0.02        # MA ± 2% 허용 범위

# Breakout 매수
ENTRY_BREAKOUT_VOL_SURGE: float = 1.5             # 돌파 시 거래량 150%+
ENTRY_BREAKOUT_STRONG_VOL: float = 2.0            # 강한 돌파 거래량 200%+

# MACD
ENTRY_MACD_SIGNAL_CROSS: bool = True              # MACD 시그널 상향 교차
ENTRY_MACD_ABOVE_ZERO_BONUS: float = 10.0         # MACD > 0 에서 골든크로스 보너스

# 볼린저 밴드 Squeeze
ENTRY_BB_SQUEEZE_BREAKOUT: float = 1.0            # BB%B ≥ 1.0 (상단 돌파)
ENTRY_BB_BANDWIDTH_SQUEEZE: float = 4.0           # 밴드폭 ≤ 4% → Squeeze

# 진입 종합 점수 임계값
ENTRY_SCORE_STRONG_BUY: float = 65.0
ENTRY_SCORE_BUY: float = 40.0
ENTRY_SCORE_NEUTRAL: float = 20.0

# ── 5단계: 리스크 관리 ────────────────────────────────────
RISK_PER_TRADE_PCT: float = 0.02                  # 1회 거래 최대 손실 = 자본의 2%
RISK_ATR_SL_MULTIPLIER: float = 2.5               # 손절: 진입가 - 2.5 ATR (스윙보다 넓음)
RISK_ATR_TP_MULTIPLIER: float = 5.0               # 익절: 진입가 + 5.0 ATR
RISK_MIN_RR_RATIO: float = 2.0                    # 최소 R배수 (보상/위험 ≥ 2.0)
RISK_MAX_PORTFOLIO_PCT: float = 0.20              # 단일 종목 최대 비중 20%
RISK_MAX_TOTAL_RISK_PCT: float = 0.10             # 포트폴리오 동시 리스크 최대 10%
RISK_DEFAULT_CAPITAL: float = 10_000_000           # 기본 자본금 1000만원
RISK_SPLIT_BUY_RATIO_1: float = 0.34              # 1차 매수 비율
RISK_SPLIT_BUY_RATIO_2: float = 0.33              # 2차 매수 비율
RISK_SPLIT_BUY_RATIO_3: float = 0.33              # 3차 매수 비율

# ── 6단계: 보유 관리 ──────────────────────────────────────
HOLD_TRAILING_ATR_MULTIPLIER: float = 2.5         # 트레일링: 고점 - 2.5 ATR
HOLD_TRAILING_MA50: bool = True                   # 50일 MA 기준 트레일링
HOLD_PARABOLIC_SAR_AF: float = 0.02               # Parabolic SAR 가속인자 초기값
HOLD_PARABOLIC_SAR_MAX_AF: float = 0.20           # Parabolic SAR 최대 가속인자
HOLD_PYRAMID_MIN_PROFIT_PCT: float = 0.05         # 피라미딩 최소 이익률 5%
HOLD_PYRAMID_REDUCE_RATIO: float = 0.5            # 추가 매수 시 수량 감소 비율

# ── 7단계: 매도/청산 ──────────────────────────────────────
EXIT_MA50_BREAK: bool = True                      # 50일 MA 종가 이탈 → 청산
EXIT_MA200_BREAK: bool = True                     # 200일 MA 이탈 → 완전 청산
EXIT_MACD_DIVERGENCE: bool = True                 # MACD 다이버전스 → 경고
EXIT_RSI_DIVERGENCE: bool = True                  # RSI 다이버전스 → 경고
EXIT_ADX_DECLINE_FROM_PEAK: float = 5.0           # ADX 피크 대비 5p 이상 하락 → 추세 약화
EXIT_VOLUME_DRY_UP_RATIO: float = 0.5             # 신고가 시 거래량이 20일 평균의 50% 이하
EXIT_PARTIAL_SELL_RATIO: float = 0.34             # 1차 익절 시 1/3 매도
EXIT_RSI_OVERBOUGHT: float = 70.0                 # RSI ≥ 70 → 과매수 경고
EXIT_RSI_EXTREME: float = 80.0                    # RSI ≥ 80 → 적극 청산

# ── 단계별 가중치 (종합 점수 산출) ────────────────────────
WEIGHT_STEP1_MARKET: float = 0.15                 # 시장 환경 15%
WEIGHT_STEP2_SECTOR: float = 0.10                 # 섹터 선정 10%
WEIGHT_STEP3_SCREENING: float = 0.20              # 종목 선정 20%
WEIGHT_STEP4_ENTRY: float = 0.25                  # 매수 타이밍 25%
WEIGHT_STEP5_RISK: float = 0.15                   # 리스크 관리 15%
WEIGHT_STEP6_HOLD: float = 0.05                   # 보유 관리 5%
WEIGHT_STEP7_EXIT: float = 0.10                   # 매도 청산 10%

# ── 단계별 최대 점수 ──────────────────────────────────────
STEP_MAX_SCORE: float = 100.0
