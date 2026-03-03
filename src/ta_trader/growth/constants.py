"""
ta_trader/growth/constants.py
100% 상승 후보 발굴 6단계 프로세스 전용 상수

6단계 프로세스:
  1단계: 이익 가속 필터       (Earnings Acceleration)
  2단계: 촉매 확인            (Catalyst / New)
  3단계: 스테이지 판별         (Stage Analysis)
  4단계: 기술적 진입 조건      (Technical Entry)
  5단계: 리스크 관리           (Risk Management)
  6단계: 보유 관리 & 청산      (Hold & Exit)
"""

# ── 1단계: 이익 가속 필터 ─────────────────────────────────
# yfinance info에서 획득 가능한 항목 기준
EPS_GROWTH_MIN: float = 0.25          # 분기 EPS 성장률 최소 25%
REVENUE_GROWTH_MIN: float = 0.20      # 매출 성장률 최소 20%
PROFIT_MARGIN_MIN: float = 0.0        # 영업이익률 양수
EARNINGS_SURPRISE_MIN: float = 0.0    # 어닝 서프라이즈 양수

# 1단계 점수 배분 (최대 25점)
SCORE_EARNINGS_MAX: float = 25.0
SCORE_EPS_GROWTH: float = 8.0         # EPS 성장률 충족
SCORE_REVENUE_GROWTH: float = 7.0     # 매출 성장률 충족
SCORE_PROFIT_MARGIN: float = 5.0      # 영업이익률 양수+개선
SCORE_EARNINGS_SURPRISE: float = 5.0  # 어닝 서프라이즈

# ── 2단계: 촉매 확인 (수동) ───────────────────────────────
# 2단계는 정성적 판단이므로 점수 부여하지 않고 플래그만 제공
# 산업 분류(sector/industry)와 최근 뉴스 키워드로 힌트 제공

# ── 3단계: 스테이지 판별 (미너비니 SEPA) ──────────────────
SMA_150_WINDOW: int = 150
SMA_200_WINDOW: int = 200
SMA_50_WINDOW: int = 50

# SEPA 체크리스트 임계값
SEPA_ABOVE_52W_LOW_PCT: float = 0.30   # 52주 저가 대비 +30% 이상
SEPA_NEAR_52W_HIGH_PCT: float = 0.25   # 52주 고가 대비 -25% 이내
SMA200_UPTREND_DAYS: int = 22          # 200일선 1개월(22거래일) 이상 상승
RS_RANK_THRESHOLD: float = 0.70        # 상대강도 상위 30% (≥0.70)

# 3단계 점수 배분 (최대 25점)
SCORE_STAGE_MAX: float = 25.0
SCORE_MA_ALIGNMENT: float = 8.0        # 현재가>150일>200일 정배열
SCORE_SMA200_UPTREND: float = 5.0      # 200일선 상승 지속
SCORE_52W_POSITION: float = 7.0        # 52주 고/저 위치
SCORE_RS_RANK: float = 5.0             # 상대강도 순위

# ── 4단계: 기술적 진입 조건 ───────────────────────────────
# 기존 지표(ADX, MACD, BB, RSI) + 거래량 분석
VOLUME_BREAKOUT_RATIO: float = 1.5     # 50일 평균 거래량의 1.5배
VOLUME_AVG_WINDOW: int = 50

ADX_RISING_MIN: float = 25.0           # ADX 상승 전환 최소값
ADX_ENTRY_IDEAL: float = 30.0          # 이상적 진입 ADX
ADX_LATE_ENTRY: float = 40.0           # 추세 후반 (진입 위험)

MACD_ZERO_CROSS: float = 0.0           # MACD 제로라인
RSI_BULLISH_MIN: float = 50.0          # 강세 구간 최소
RSI_OVERHEAT: float = 80.0             # 단기 과열

BB_BREAKOUT_UPPER: float = 1.0         # BB 상단 돌파
BB_SQUEEZE_THRESHOLD: float = 4.0      # BW ≤ 4% 스퀴즈

# 4단계 점수 배분 (최대 30점)
SCORE_TECHNICAL_MAX: float = 30.0
SCORE_ADX_GATE: float = 8.0            # ADX 게이트 조건
SCORE_MACD_DIRECTION: float = 8.0      # MACD 방향 + 히스토그램
SCORE_BB_BREAKOUT: float = 6.0         # BB 돌파/스퀴즈
SCORE_RSI_ZONE: float = 3.0            # RSI 강세 구간
SCORE_VOLUME_CONFIRM: float = 5.0      # 거래량 확인

# ── 5단계: 리스크 관리 ────────────────────────────────────
GROWTH_ATR_SL_MULTIPLIER: float = 2.5  # 손절: 2.5x ATR
GROWTH_ATR_TP_MULTIPLIER: float = 5.0  # 익절: 5.0x ATR
GROWTH_DEFAULT_SL_PCT: float = 0.07    # 기본 손절 7%
GROWTH_DEFAULT_TP_PCT: float = 0.15    # 기본 익절 15%
GROWTH_MIN_RR_RATIO: float = 2.0       # 최소 위험보상비율 1:2
GROWTH_IDEAL_RR_RATIO: float = 3.0     # 이상적 R:R 1:3

# 5단계 점수 배분 (최대 10점)
SCORE_RISK_MAX: float = 10.0
SCORE_RR_ADEQUATE: float = 5.0         # R:R ≥ 1:2
SCORE_RR_IDEAL: float = 5.0            # R:R ≥ 1:3

# ── 6단계: 보유 관리 (현재 건강도) ────────────────────────
# 이미 보유 중인 경우의 모니터링 지표 임계값
HOLD_ADX_HEALTHY: float = 25.0         # ADX ≥ 25 유지
HOLD_MACD_POSITIVE: float = 0.0        # MACD > 0 유지
HOLD_RSI_BULLISH: float = 50.0         # RSI > 50 유지
HOLD_DI_MARGIN: float = 2.0            # +DI - (-DI) 최소 격차

# 6단계 점수 배분 (최대 10점)
SCORE_HOLD_MAX: float = 10.0
SCORE_ADX_HEALTH: float = 3.0
SCORE_MACD_HEALTH: float = 3.0
SCORE_DI_HEALTH: float = 2.0
SCORE_RSI_HEALTH: float = 2.0

# ── 종합 등급 임계값 (0~100) ──────────────────────────────
GRADE_STRONG_BUY: float = 75.0         # ★★★★★ 적극매수
GRADE_BUY: float = 60.0                # ★★★★  매수
GRADE_CONDITIONAL: float = 45.0        # ★★★   조건부매수
GRADE_WATCH: float = 30.0              # ★★    관심관망
# 30 미만                               # ★     부적합

# ── 데이터 수집 ───────────────────────────────────────────
GROWTH_DEFAULT_PERIOD: str = "1y"       # 1년 데이터 기본
GROWTH_MIN_DATA_ROWS: int = 200         # 200일 SMA 계산에 필요
