#!/bin/bash

interests=(
    "005930_KS"   # 삼성전자
    "000660_KS"   # SK하이닉스
    "058470_KQ"   # 리노공업
    "DOW"         # Dow, Inc.
    "NNDM"        # 
    "INUV"        # 
    "MVIS"        # 
    "ARKG"        # 
    "SPY"         # 
    "JEPI"        # 
    "KBWY"        # 
    "RA"          # 
    "QYLD"        # 
    "GOOGL"       # 
    "LITE"        # 
    "recommend"
)

for type in swing position growth value technical; do
    for prefix in "${interests[@]}"; do
        cp reports/${prefix}_${type}_"$1"*.* interests/ 2>/dev/null
    done
done

