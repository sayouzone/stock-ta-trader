#!/bin/bash

ANALYZE_CMD="python main.py analyze --save-chart --save-report --save-csv"

# ── 옵션 처리 로직 ───────────────────────────
# $1은 스크립트 실행 시 전달되는 첫 번째 인자를 의미합니다.
case "$1" in
    KOSPI)
        $ANALYZE_CMD --style swing KOSPI
        echo "" # 줄바꿈
        $ANALYZE_CMD --style position KOSPI
        echo "" # 줄바꿈
        $ANALYZE_CMD --style growth KOSPI
        echo "" # 줄바꿈
        $ANALYZE_CMD --style value KOSPI
        ;;
    KOSDAQ)
        $ANALYZE_CMD --style swing KOSDAQ
        echo "" # 줄바꿈
        $ANALYZE_CMD --style position KOSDAQ
        echo "" # 줄바꿈
        $ANALYZE_CMD --style growth KOSDAQ
        echo "" # 줄바꿈
        $ANALYZE_CMD --style value KOSDAQ
        ;;
    KRX)
        $ANALYZE_CMD --style swing KRX
        echo "" # 줄바꿈
        $ANALYZE_CMD --style position KRX
        echo "" # 줄바꿈
        $ANALYZE_CMD --style growth KRX
        echo "" # 줄바꿈
        $ANALYZE_CMD --style value KRX
        ;;
    US|"")
        $ANALYZE_CMD --style swing US
        echo "" # 줄바꿈
        $ANALYZE_CMD --style position US
        echo "" # 줄바꿈
        $ANALYZE_CMD --style growth US
        echo "" # 줄바꿈
        $ANALYZE_CMD --style value US
        ;;
    *)
        # 잘못된 옵션을 입력했거나 옵션이 없는 경우 안내 메시지 출력
        echo "사용법: $0 {KOSPI|KOSDAQ|US|KRX}"
        echo "  KOSPI  : 한국 KOSPI 주식만 분석"
        echo "  KOSDAQ : 한국 KOSDAQ 주식만 분석"
        echo "  KRX    : 한국 주식만 분석"
        echo "  US     : 미국 주식만 분석"
        exit 1
        ;;
esac