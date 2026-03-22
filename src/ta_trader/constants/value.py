"""
ta_trader/constants/value.py
가치 투자 5단계 분석 프로세스 전용 상수

5단계 프로세스:
  1단계: 밸류에이션 필터       (Valuation Filter)
  2단계: 수익성 분석           (Profitability Analysis)
  3단계: 재무 건전성           (Financial Health)
  4단계: 안전마진 산출         (Margin of Safety)
  5단계: 기술적 진입 타이밍    (Technical Entry Timing)
"""

# ── 1단계: 밸류에이션 필터 ────────────────────────────────
PER_LOW_THRESHOLD: float = 10.0          # 저PER 기준
PER_HIGH_THRESHOLD: float = 20.0         # 고PER 기준 (초과 시 감점)
PER_SECTOR_DISCOUNT: float = 0.7         # 업종 평균 대비 70% 이하 → 저평가

PBR_LOW_THRESHOLD: float = 1.0           # PBR < 1 자산가치 이하
PBR_DEEP_VALUE: float = 0.5              # PBR < 0.5 심각한 저평가

PSR_LOW_THRESHOLD: float = 1.0           # PSR < 1 저평가
PSR_HIGH_THRESHOLD: float = 3.0          # PSR > 3 고평가

EV_EBITDA_LOW: float = 6.0              # EV/EBITDA < 6 저평가
EV_EBITDA_HIGH: float = 12.0            # EV/EBITDA > 12 고평가
EV_EBITDA_MANDA: float = 5.0            # M&A 타깃 수준

# 1단계 점수 배분 (최대 25점)
SCORE_VALUATION_MAX: float = 25.0
SCORE_PER: float = 8.0                   # PER 점수
SCORE_PBR: float = 6.0                   # PBR 점수
SCORE_PSR: float = 4.0                   # PSR 점수
SCORE_EV_EBITDA: float = 7.0             # EV/EBITDA 점수

# ── 2단계: 수익성 분석 ────────────────────────────────────
ROE_EXCELLENT: float = 0.15              # ROE 15% 이상 우수
ROE_GOOD: float = 0.10                   # ROE 10% 이상 양호
ROE_MIN: float = 0.05                    # ROE 5% 미만 저조

OPERATING_MARGIN_EXCELLENT: float = 0.15  # 영업이익률 15% 이상
OPERATING_MARGIN_GOOD: float = 0.10       # 영업이익률 10% 이상
OPERATING_MARGIN_MIN: float = 0.05        # 영업이익률 5% 미만 저조

FCF_YIELD_ATTRACTIVE: float = 0.05       # FCF Yield 5% 이상 매력적
FCF_YIELD_MIN: float = 0.03             # FCF Yield 3% 이상 적정

CASH_CONVERSION_GOOD: float = 1.0        # FCF/순이익 ≥ 1.0 우수
CASH_CONVERSION_MIN: float = 0.5         # FCF/순이익 ≥ 0.5 양호

# 2단계 점수 배분 (최대 25점)
SCORE_PROFITABILITY_MAX: float = 25.0
SCORE_ROE: float = 8.0                   # ROE 점수
SCORE_OPERATING_MARGIN: float = 7.0       # 영업이익률 점수
SCORE_FCF_YIELD: float = 5.0             # FCF Yield 점수
SCORE_CASH_CONVERSION: float = 5.0        # Cash Conversion 점수

# ── 3단계: 재무 건전성 ────────────────────────────────────
DEBT_EQUITY_SAFE: float = 0.5            # D/E 50% 이하 안전
DEBT_EQUITY_OK: float = 1.0             # D/E 100% 이하 적정
DEBT_EQUITY_DANGER: float = 2.0          # D/E 200% 초과 위험

CURRENT_RATIO_GOOD: float = 2.0          # 유동비율 200% 이상 양호
CURRENT_RATIO_MIN: float = 1.0           # 유동비율 100% 미만 주의

INTEREST_COVERAGE_SAFE: float = 5.0      # 이자보상배율 5배 이상 안전
INTEREST_COVERAGE_MIN: float = 3.0       # 이자보상배율 3배 이상 적정

REVENUE_STABILITY_YEARS: int = 3         # 매출 안정성 확인 기간 (연)
EARNINGS_STABILITY_YEARS: int = 3        # 이익 안정성 확인 기간 (연)

# 3단계 점수 배분 (최대 20점)
SCORE_FINANCIAL_MAX: float = 20.0
SCORE_DEBT_EQUITY: float = 6.0           # 부채비율 점수
SCORE_CURRENT_RATIO: float = 5.0         # 유동비율 점수
SCORE_INTEREST_COVERAGE: float = 5.0     # 이자보상배율 점수
SCORE_EARNINGS_STABILITY: float = 4.0    # 이익 안정성 점수

# ── 4단계: 안전마진 산출 ──────────────────────────────────
# 비교 밸류에이션 기반 내재가치
MARGIN_OF_SAFETY_STRONG: float = 0.40    # 40% 이상 → 강력 매수 신호
MARGIN_OF_SAFETY_GOOD: float = 0.25      # 25% 이상 → 매수 고려
MARGIN_OF_SAFETY_MIN: float = 0.10       # 10% 이상 → 최소 안전마진

# 배당 관련
DIVIDEND_YIELD_ATTRACTIVE: float = 0.03  # 배당수익률 3% 이상
DIVIDEND_YIELD_HIGH: float = 0.05        # 배당수익률 5% 이상
PAYOUT_RATIO_SAFE_MAX: float = 0.60      # 배당성향 60% 이하 안전
PAYOUT_RATIO_DANGER: float = 0.80        # 배당성향 80% 초과 위험

# PEG Ratio
PEG_UNDERVALUED: float = 1.0            # PEG < 1 성장 대비 저평가
PEG_FAIR: float = 1.5                   # PEG < 1.5 적정

# 4단계 점수 배분 (최대 20점)
SCORE_MARGIN_MAX: float = 20.0
SCORE_INTRINSIC_VALUE: float = 8.0       # 내재가치 대비 할인율
SCORE_DIVIDEND: float = 5.0              # 배당 매력도
SCORE_PEG: float = 4.0                   # PEG Ratio
SCORE_BUYBACK: float = 3.0              # 자사주 매입 등 주주환원

# ── 5단계: 기술적 진입 타이밍 ─────────────────────────────
# 이동평균 기준
SMA_200_WINDOW: int = 200
SMA_50_WINDOW: int = 50
SMA_20_WINDOW: int = 20

# RSI 과매도 기준
RSI_OVERSOLD: float = 30.0              # RSI < 30 과매도 (매수 기회)
RSI_NEUTRAL_LOW: float = 40.0           # RSI 40 이하 저평가 영역
RSI_OVERBOUGHT: float = 70.0            # RSI > 70 과매수

# 52주 범위
NEAR_52W_LOW_PCT: float = 0.15          # 52주 저가 대비 +15% 이내

# ATR 기반 손절/익절
VALUE_ATR_SL_MULTIPLIER: float = 2.0    # 가치투자 손절: 2x ATR (넓게)
VALUE_ATR_TP_MULTIPLIER: float = 4.0    # 가치투자 익절: 4x ATR
VALUE_DEFAULT_SL_PCT: float = 0.10      # 기본 손절 10%
VALUE_DEFAULT_TP_PCT: float = 0.25      # 기본 익절 25% (안전마진 기반)
VALUE_MIN_RR_RATIO: float = 2.0         # 최소 R:R 1:2

# 5단계 점수 배분 (최대 10점)
SCORE_ENTRY_MAX: float = 10.0
SCORE_MA_SUPPORT: float = 3.0           # 이평선 지지 여부
SCORE_RSI_ENTRY: float = 3.0            # RSI 저평가 영역
SCORE_52W_ENTRY: float = 2.0            # 52주 위치
SCORE_RISK_REWARD: float = 2.0          # R:R 비율

# ── 종합 등급 임계값 (0~100) ──────────────────────────────
GRADE_STRONG_BUY: float = 75.0          # ★★★★★ 적극매수
GRADE_BUY: float = 60.0                 # ★★★★  매수
GRADE_CONDITIONAL: float = 45.0         # ★★★   조건부매수
GRADE_WATCH: float = 30.0               # ★★    관심관망
# 30 미만                                # ★     부적합

# ── 데이터 수집 ───────────────────────────────────────────
VALUE_DEFAULT_PERIOD: str = "2y"         # 가치투자는 2년 데이터 기본
VALUE_MIN_DATA_ROWS: int = 200           # 200일 SMA 계산에 필요
