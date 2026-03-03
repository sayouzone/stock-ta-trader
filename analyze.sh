#!/bin/bash

ANALYZE_CMD="python main.py analyze --save-chart --save-report"

# ── 한국 주식 분석 함수 ─────────────────────
analyze_ko() {
    echo "=== 한국 KOSPI 주식 분석을 시작합니다 ==="
    $ANALYZE_CMD "005930.KS"   # 삼성전자
    $ANALYZE_CMD "000660.KS"   # SK하이닉스
    $ANALYZE_CMD "005380.KS"   # 현대차
    $ANALYZE_CMD "000270.KS"   # 기아자동차
    $ANALYZE_CMD "373220.KS"   # LG에너지솔루션
    $ANALYZE_CMD "402340.KS"   # SK스퀘어
    $ANALYZE_CMD "207940.KS"   # 삼성바이오로직스
    $ANALYZE_CMD "034020.KS"   # 두산에너빌리티
    $ANALYZE_CMD "012450.KS"   # 한화에어로스페이스
    $ANALYZE_CMD "329180.KS"   # HD현대중공업
    $ANALYZE_CMD "028260.KS"   # 삼성물산
    $ANALYZE_CMD "105560.KS"   # KB금융
    $ANALYZE_CMD "068270.KS"   # 셀트리온
    $ANALYZE_CMD "032830.KS"   # 삼성생명
    $ANALYZE_CMD "012330.KS"   # 현대모비스
    $ANALYZE_CMD "042660.KS"   # 한화오션
    $ANALYZE_CMD "009150.KS"   # 삼성전기
    $ANALYZE_CMD "035720.KS"   # 카카오
    $ANALYZE_CMD "035420.KS"   # NAVER
    $ANALYZE_CMD "005935.KS"   # 삼성전자우
    $ANALYZE_CMD "055550.KS"   # 신한지주
    $ANALYZE_CMD "010130.KS"   # 고려아연
    $ANALYZE_CMD "006800.KS"   # 미래에셋증권
    $ANALYZE_CMD "267260.KS"   # HD현대일렉트릭
    $ANALYZE_CMD "015760.KS"   # 한국전력
    $ANALYZE_CMD "006400.KS"   # 삼성SDI
    $ANALYZE_CMD "086790.KS"   # 하나금융지주
    $ANALYZE_CMD "005490.KS"   # POSCO홀딩스
    $ANALYZE_CMD "009540.KS"   # HD한국조선해양
    $ANALYZE_CMD "042700.KS"   # 한미반도체
    $ANALYZE_CMD "051910.KS"   # LG화학
    $ANALYZE_CMD "034730.KS"   # SK	
    $ANALYZE_CMD "316140.KS"   # 우리금융지주	
    $ANALYZE_CMD "298040.KS"   # 효성중공업
    $ANALYZE_CMD "010140.KS"   # 삼성중공업
    $ANALYZE_CMD "000810.KS"   # 삼성화재
    $ANALYZE_CMD "066570.KS"   # LG전자
    $ANALYZE_CMD "010120.KS"   # LS ELECTRIC
    $ANALYZE_CMD "267250.KS"   # HD현대
    $ANALYZE_CMD "138040.KS"   # 메리츠금융지주
    $ANALYZE_CMD "003670.KS"   # 포스코퓨처엠
    $ANALYZE_CMD "086280.KS"   # 현대글로비스
    $ANALYZE_CMD "096770.KS"   # SK이노베이션
    $ANALYZE_CMD "272210.KS"   # 한화시스템
    $ANALYZE_CMD "000150.KS"   # 두산
    $ANALYZE_CMD "024110.KS"   # 기업은행
    $ANALYZE_CMD "011200.KS"   # HMM
    $ANALYZE_CMD "069500.KS"   # KODEX 200
    $ANALYZE_CMD "033780.KS"   # KT&G

    # ── 보유종목 ─────────────────────
    $ANALYZE_CMD "001680.KS"   # 대상
    $ANALYZE_CMD "005680.KS"   # 삼영전자
    $ANALYZE_CMD "007070.KS"   # GS리테일
    $ANALYZE_CMD "008490.KS"   # 서흥
    $ANALYZE_CMD "016580.KS"   # 환인제약
    $ANALYZE_CMD "040420.KQ"   # 정상제이엘에스
    $ANALYZE_CMD "079550.KS"   # LIG넥스원

    # ── KOSDAQ 종목 ─────────────────────
    $ANALYZE_CMD "064350.KS"   # 현대로템
    $ANALYZE_CMD "452430.KQ"   # 사피엔반도체
    $ANALYZE_CMD "298050.KS"   # HS효성첨단소재
    $ANALYZE_CMD "086520.KQ"   # 에코프로
    $ANALYZE_CMD "196170.KQ"   # 알테오젠
    $ANALYZE_CMD "247540.KQ"   # 에코프로비엠
    $ANALYZE_CMD "000250.KQ"   # 삼천당제약
    $ANALYZE_CMD "277810.KQ"   # 레인보우로보틱스
    $ANALYZE_CMD "298380.KQ"   # 에이비엘바이오
    $ANALYZE_CMD "950160.KQ"   # 코오롱티슈진
    $ANALYZE_CMD "058470.KQ"   # 리노공업
    $ANALYZE_CMD "214370.KQ"   # 케어젠
    $ANALYZE_CMD "141080.KQ"   # 리가켐바이오
    $ANALYZE_CMD "028300.KQ"   # HLB
    $ANALYZE_CMD "087010.KQ"   # 펩트론
    $ANALYZE_CMD "240810.KQ"   # 원익IPS
    $ANALYZE_CMD "310210.KQ"   # 보로노이
    $ANALYZE_CMD "039030.KQ"   # 이오테크닉스
    $ANALYZE_CMD "140410.KQ"   # 메지온
    $ANALYZE_CMD "108490.KQ"   # 로보티즈
    $ANALYZE_CMD "095340.KQ"   # ISC
    $ANALYZE_CMD "347850.KQ"   # 디앤디파마텍
    $ANALYZE_CMD "0009K0.KQ"   # 에임드바이오
    $ANALYZE_CMD "319400.KQ"   # 현대무벡스
    $ANALYZE_CMD "214150.KQ"   # 클래시스
    $ANALYZE_CMD "403870.KQ"   # HPSP
    $ANALYZE_CMD "226950.KQ"   # 올릭스
    $ANALYZE_CMD "214450.KQ"   # 파마리서치
    $ANALYZE_CMD "357780.KQ"   # 솔브레인
    $ANALYZE_CMD "263750.KQ"   # 편어비스
    $ANALYZE_CMD "145020.KQ"   # 휴젤
    $ANALYZE_CMD "058610.KQ"   # 에스피지
    $ANALYZE_CMD "237690.KQ"   # 에스티팜
    $ANALYZE_CMD "068760.KQ"   # 셀트리온제약
    $ANALYZE_CMD "084370.KQ"   # 유진테크
    $ANALYZE_CMD "440110.KQ"   # 파두
    $ANALYZE_CMD "083650.KQ"   # 비에이치아이
    $ANALYZE_CMD "032820.KQ"   # 우리기술
    $ANALYZE_CMD "005290.KQ"   # 동진쎄미켐
    $ANALYZE_CMD "475830.KQ"   # 오름테라퓨틱
    $ANALYZE_CMD "178320.KQ"   # 서진시스템
    $ANALYZE_CMD "030530.KQ"   # 원익홀딩스
    $ANALYZE_CMD "257720.KQ"   # 실리콘투
    $ANALYZE_CMD "036930.KQ"   # 주성엔지니어링
    $ANALYZE_CMD "041510.KQ"   # 에스엠
    $ANALYZE_CMD "064760.KQ"   # 티씨케이
    $ANALYZE_CMD "035900.KQ"   # JYP Ent.
    $ANALYZE_CMD "290650.KQ"   # 엘앤씨바이오
    $ANALYZE_CMD "323280.KQ"   # 태성
    $ANALYZE_CMD "067310.KQ"   # 하나마이크론
    $ANALYZE_CMD "491000.KQ"   # 리브스메드
    $ANALYZE_CMD "098460.KQ"   # 고영
    $ANALYZE_CMD "160190.KQ"   # 하이젠알앤엠
    echo "=== 한국 주식 분석 완료 ==="
}

# ── 미국 주식 분석 함수 ───────────────────────────
analyze_us() {
    echo "=== 미국 주식 분석을 시작합니다 ==="
    $ANALYZE_CMD "NVDA"        # NVIDIA Corporation
    $ANALYZE_CMD "AAPL"        # Apple Inc.
    $ANALYZE_CMD "GOOGL"       # Alphabet Inc.
    $ANALYZE_CMD "MSFT"        # Microsoft Corporation
    $ANALYZE_CMD "AMZN"        # Amazon.com, Inc.
    $ANALYZE_CMD "TSM"         # Taiwan Semiconductor Manufacturing Company Limited
    $ANALYZE_CMD "META"        # Meta Platforms, Inc.
    $ANALYZE_CMD "AVGO"        # Broadcom Inc.
    $ANALYZE_CMD "TSLA"        # Tesla, Inc.
    $ANALYZE_CMD "BRK-B"       # Berkshire Hathaway Inc.
    $ANALYZE_CMD "WMT"         # Walmart Inc.
    $ANALYZE_CMD "LLY"         # Eli Lilly and Company
    $ANALYZE_CMD "JPM"         # JPMorgan Chase & Co.
    $ANALYZE_CMD "AZN"         # AstraZeneca PLC
    $ANALYZE_CMD "XOM"         # Exxon Mobil Corporation
    $ANALYZE_CMD "V"           # Visa Inc.
    $ANALYZE_CMD "JNJ"         # Johnson & Johnson
    $ANALYZE_CMD "ASML"        # ASML Holding N.V.
    $ANALYZE_CMD "MU"          # Micron Technology, Inc.
    $ANALYZE_CMD "MA"          # Mastercard Incorporated
    $ANALYZE_CMD "COST"        # Costco Wholesale Corporation
    $ANALYZE_CMD "ORCL"        # Oracle Corporation
    $ANALYZE_CMD "ABBV"        # AbbVie Inc.
    $ANALYZE_CMD "NFLX"        # Netflix, Inc.
    $ANALYZE_CMD "PG"          # The Procter & Gamble Company
    $ANALYZE_CMD "HD"          # The Home Depot, Inc.
    $ANALYZE_CMD "CVX"         # Chevron Corporation
    $ANALYZE_CMD "GE"          # GE Aerospace
    $ANALYZE_CMD "BAC"         # Bank of America Corporation
    $ANALYZE_CMD "KO"          # The Coca-Cola Company
    $ANALYZE_CMD "CAT"         # Caterpillar Inc.
    $ANALYZE_CMD "BABA"        # Alibaba Group Holding Limited
    $ANALYZE_CMD "PLTR"        # Palantir Technologies Inc.
    $ANALYZE_CMD "AMD"         # Advanced Micro Devices, Inc.
    $ANALYZE_CMD "NVS"         # Novartis AG
    $ANALYZE_CMD "HSBC"        # HSBC Holdings plc
    $ANALYZE_CMD "TM"          # Toyota Motor Corporation
    $ANALYZE_CMD "CSCO"        # Cisco Systems, Inc.
    $ANALYZE_CMD "MRK"         # Merck & Co., Inc.
    $ANALYZE_CMD "AMAT"        # Applied Materials, Inc.
    $ANALYZE_CMD "LRCX"        # Lam Research Corporation
    $ANALYZE_CMD "PM"          # Philip Morris International Inc.
    $ANALYZE_CMD "RTX"         # RTX Corporation
    $ANALYZE_CMD "UNH"         # UnitedHealth Group Incorporated
    $ANALYZE_CMD "MS"          # Morgan Stanley
    $ANALYZE_CMD "GS"          # The Goldman Sachs Group, Inc.
    $ANALYZE_CMD "WFC"         # Wells Fargo & Company
    $ANALYZE_CMD "SAP"         # SAP SE
    $ANALYZE_CMD "SHEL"        # Shell plc
    $ANALYZE_CMD "MCD"         # McDonald's Corporation

    # ── 보유종목 ─────────────────────
    $ANALYZE_CMD  "DOW"         # Dow Inc
    $ANALYZE_CMD  "NNDM"        # Nano Dimension Ltd
    $ANALYZE_CMD  "INUV"        # Inuvo, Inc.
    $ANALYZE_CMD  "IONQ"        # IONQ Inc
    $ANALYZE_CMD  "MVIS"        # Microvision Inc
    $ANALYZE_CMD  "ARKG"        # ARK Genomic Revolution ETF
    $ANALYZE_CMD  "SPY"         # SPDR S&P 500 Trust ETF

    # ── 배당 보유종목 ─────────────────────
    $ANALYZE_CMD  "JEPI"        # JPMorgan Equity Premium Income ETF
    $ANALYZE_CMD  "AGNC"        # AGNC Investment Corp
    $ANALYZE_CMD  "KBWY"        # Invesco KBW Premium Yield Equity REIT ETF
    $ANALYZE_CMD  "RA"          # Brookfield Real Assets Income Fund Inc
    $ANALYZE_CMD  "QYLD"        # Global X NASDAQ 100 Covered Call ETF

    # ── 종목 검토 ─────────────────────
    $ANALYZE_CMD  "MRVL"        # Marvell Technology, Inc.
    echo "=== 미국 주식 분석 완료 ==="
}

# ── 옵션 처리 로직 ───────────────────────────
# $1은 스크립트 실행 시 전달되는 첫 번째 인자를 의미합니다.
case "$1" in
    ko)
        analyze_ko
        ;;
    us)
        analyze_us
        ;;
    all|"")
        analyze_ko
        echo "" # 줄바꿈
        analyze_us
        ;;
    *)
        # 잘못된 옵션을 입력했거나 옵션이 없는 경우 안내 메시지 출력
        echo "사용법: $0 {kor|us|all}"
        echo "  ko  : 한국 주식만 분석"
        echo "  us  : 미국 주식만 분석"
        echo "  all : 모든 주식 분석"
        exit 1
        ;;
esac