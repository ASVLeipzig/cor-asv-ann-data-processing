#!/bin/bash
# concatenate to csv files (input tab output newline)...
for ocr in deu-frak3 Fraktur4 foo4
do
    for data in traindata testdata
    do
        out=${data}.${ocr}-gt.txt
        test -s "$out" && echo "skipping $out" && continue
        touch $out
        for file in ${data}/*.${ocr}.txt
        do
            # insert numerically sorted by length of ocr line:
            sort -n -o "$out" -m <({ wc -c < "$file"; tr -d '\f' < "$file"; cat ${file%.${ocr}.txt}.gt.txt; } | tr '\n' '\t') "$out"
        done
        # remove length column and trailing tab:
        sed -i 's/^[^	]*	//;s/	$//' "$out"
        # ignore failed OCR lines:
        egrep -v -e '(.)\1{4,}' -e '[[:punct:]]{6,}' <"$_" >"${out%.txt}.filtered.txt"
        # augment by more true pairs:
        sed 'h;s/^[^	]*	//;s/^.*$/&	&/;p;p;p;p;g' <"$_" >"${out%.txt}.filtered.augmented.txt"
        # make another file with character counts:
        while IFS=$'\t' read source target; do echo "${#source} ${#target}"; done <"$_" >"${out%.txt}.filtered.augmented.len"
    done
done
exit
# concatenate to single files (one file per ocr)...
for ocr in gt foo4 Fraktur4 deu-frak3
do
    for data in traindata testdata
    do
        out=$data.${ocr}.txt
        test -s "$out" && echo "skipping $out" && continue
        touch $out
        for file in $data/*.gt.txt
        do
            realfile=${file%.gt.txt}.${ocr}.txt
            { tr -d '\f\r' < $realfile
              fgrep -q "$(echo)" $realfile || echo; } >> $out
        done
    done
done
