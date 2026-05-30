#!/bin/bash

interests=(
    "005930.KS"   # 삼성전자
    "000660.KS"   # SK하이닉스
    "005380.KS"   # 현대차
    "000270.KS"   # 기아자동차
    "329180.KS"   # HD현대중공업
    "042700.KS"   # 한미반도체
    "009150.KS"   # 삼성전기
    "001820.KS"   # 삼화콘덴서
    "006800.KS"   # 미래에셋증권
    "034020.KS"   # 두산에너빌리티
    "012450.KS"   # 한화에어로스페이스
    "042660.KS"   # 한화오션
    "064350.KS"   # 현대로템
    "079550.KS"   # LIG디펜스앤에어로스페이스
    "066570.KS"   # LG전자
    "AMD"         # Advanced Micro Devices, Inc.
    "INTC"        # Intel Corporation
    "NVDA"        # NVIDIA Corporation
    "AAPL"        # Apple Inc.
    "GOOG"        # Alphabet Inc.
    "MSFT"        # Microsoft Corporation
    "TSM"         # Taiwan Semiconductor Manufacturing Company Limited
    "META"        # Meta Platforms, Inc.
    "AVGO"        # Broadcom Inc.
    "PLTR"        # Palantir Technologies Inc.
    "LITE"        # Lumentum Holdings, Inc.
    "MRVL"        # Marvell Technology, Inc.
    "SNDK"        # Sandisk Corporation
    "IONQ"        # IonQ, Inc.
    "DOW"         # Dow, Inc.
    "INUV"        # Inuvo, Inc.
    "MVIS"        # Microvision Inc
    "ARKG"        # ARK Genomic Revolution ETF
    "SPY"         # SPDR S&P 500 Trust ETF
    "JEPI"        # JPMorgan Equity Premium Income ETF
    "KBWY"        # Invesco KBW Premium Yield Equity REIT ETF
    "RA"          # Brookfield Real Assets Income Fund Inc
    #"QYLD"        # Global X NASDAQ 100 Covered Call ETF
    "recommend"
)

#for type in swing position growth value technical; do
for type in swing technical; do
    for prefix in "${interests[@]}"; do
        prefix="${prefix//./_}"
        cp reports/${prefix}_${type}_"$1"*.* interests/ 2>/dev/null
    done
done
