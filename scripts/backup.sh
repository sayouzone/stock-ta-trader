#!/bin/bash

for type in swing position growth value technical; do
    for prefix in '?' '??' '???' '????' '?????' '??????' '??????_K?' 'recommend'; do
        mv reports/${prefix}_${type}_"$1"*.* backup/ 2>/dev/null
        rm interests/${prefix}_${type}_"$1"*.* 2>/dev/null
    done
done