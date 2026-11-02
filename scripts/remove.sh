#!/bin/bash

# sh scripts/remove.sh 20260616            # $2 없음 → 전체 prefix
# sh scripts/remove.sh 20260616 KRX        # KRX만
# sh scripts/remove.sh 20260616 US         # US만
# sh scripts/remove.sh 20260616 reports    # reports 폴더만
# sh scripts/remove.sh 20260616 interests  # interests 폴더만

# $2에 따라 prefix 목록 결정
if [ -z "$2" ]; then
    prefixes=('?' '??' '???' '????' '?????' '??????' '??????_K?' 'recommend')
    reports=('reports' 'interests')
elif [ "$2" = "KRX" ]; then
    prefixes=('??????_K?')
    reports=('reports' 'interests')
elif [ "$2" = "US" ]; then
    prefixes=('?' '??' '???' '????' '?????' '??????')
    reports=('reports' 'interests')
elif [ "$2" = "reports" ]; then
    prefixes=('?' '??' '???' '????' '?????' '??????' '??????_K?' 'recommend')
    reports=('reports')
elif [ "$2" = "interests" ]; then
    prefixes=('?' '??' '???' '????' '?????' '??????' '??????_K?' 'recommend')
    reports=('interests')
else
    echo "Unknown market: $2 (KRX or US expected)"
    exit 1
fi

for type in swing position growth value park technical; do
    for prefix in "${prefixes[@]}"; do
        for report in "${reports[@]}"; do
            #echo "rm ${report}/${prefix}_${type}_"$1"*.*"
            rm ${report}/${prefix}_${type}_"$1"*.* 2>/dev/null
        done
    done
done