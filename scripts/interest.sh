#!/bin/bash

interests=(
    "005930_KS"   # 삼성전자
    "000660_KS"   # SK하이닉스
    "058470_KQ"   # 리노공업
    "042700.KS"   # 한미반도체
    "009150.KS"   # 삼성전기
    "034020.KS"   # 두산에너빌리티
    "012450.KS"   # 한화에어로스페이스
    "042660.KS"   # 한화오션
    "064350.KS"   # 현대로템
    "079550.KS"   # LIG넥스원
    "IONQ"        # IonQ, Inc.
    "DOW"         # Dow, Inc.
    "NNDM"        # Nano Dimension Ltd
    "INUV"        # Inuvo, Inc.
    "MVIS"        # Microvision Inc
    "ARKG"        # ARK Genomic Revolution ETF
    "SPY"         # SPDR S&P 500 Trust ETF
    "JEPI"        # JPMorgan Equity Premium Income ETF
    "KBWY"        # Invesco KBW Premium Yield Equity REIT ETF
    "RA"          # Brookfield Real Assets Income Fund Inc
    "QYLD"        # Global X NASDAQ 100 Covered Call ETF
    "NVDA"        # NVIDIA Corporation
    "AAPL"        # Apple Inc.
    "GOOG"        # Alphabet Inc.
    "MSFT"        # Microsoft Corporation
    "TSM"         # Taiwan Semiconductor Manufacturing Company Limited
    "META"        # Meta Platforms, Inc.
    "AVGO"        # Broadcom Inc.
    "LITE"        # Lumentum Holdings, Inc.
    "MRVL"        # Marvell Technology, Inc.
    "recommend"
)

for type in swing position growth value technical; do
    for prefix in "${interests[@]}"; do
        cp reports/${prefix}_${type}_"$1"*.* interests/ 2>/dev/null
    done
done
