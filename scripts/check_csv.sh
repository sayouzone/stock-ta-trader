#!/bin/bash

# ── 파일명만 ──────────────────────────────────────────────
ls -1 reports/*.csv        # 한 줄씩
basename /Users/seongjungkim/data/*.csv      # 경로 제외 파일명만

for type in swing technical; do
    for prefix in '?' '??' '???' '????' '?????' '??????' '??????_K?'; do
        for FILE in reports/${prefix}_${type}_*.csv; do
            echo "$FILE"
            
            FILE1=$(echo "$FILE" | sed 's/swing/technical/')
            echo "$FILE1"
            if [ -f "$FILE" ] || [ -f "$FILE1" ]; then
                cp "$FILE" "$FILE1"
            fi

            #FILE1=$(echo "$FILE" | sed 's/technical/swing/')
            #echo "$FILE1"
            #if [ -f "$FILE" ] || [ -f "$FILE1" ]; then
            #    cp "$FILE" "$FILE1"
            #fi
        done
    done
done
