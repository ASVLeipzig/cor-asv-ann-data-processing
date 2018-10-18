#!/bin/bash
# OCR single-line images...
declare -A tesserfiles
declare -A ocrofiles
for file in traindata/*.png testdata/*.png
do
    test $(jobs -r | wc -l) -ge 4 && wait # no more than 4 running jobs in parallel
    for ocr in deu-frak3 Fraktur4 foo4
    do
        test -e ${file%png}${ocr}.prob -a -e ${file%png}${ocr}.txt || {
            tesserfiles[$ocr]="${tesserfiles[$ocr]} $file"
            # if [[ $ocr =~ 3 ]]; then
            #     tesseract --oem 0 --psm 7 -l ${ocr%?} $file ${file%png}$ocr &
            # elif [[ $ocr =~ 4 ]]; then
            #     tesseract --psm 13 -l ${ocr%?} $file ${file%png}$ocr &
            # else
            #     echo "need model version in last digit for Tesseract" >&2
            # fi
        }
    done
    for ocr in ocrofraktur ocrofraktur-jze #fraktur19-00050000
    do
        test -e ${file%png}${ocr}.prob -a -e ${file%png}${ocr}.txt || {
            ocrofiles[$ocr]="${ocrofiles[$ocr]} $file"
        }
    done
done
for ocr in deu-frak3 Fraktur4 foo4
do
    eval tesserocr-batch -Q4 -l ${ocr%?} -x .$ocr ${tesserfiles[$ocr]}
done
for ocr in ocrofraktur ocrofraktur-jze #fraktur19-00050000
do
    eval ocropus-rpred -Q4 -q -n -m ${ocr#ocro}.pyrnn.gz --probabilities ${ocrofiles[$ocr]}
    for file in ${ocrofiles[$ocr]}
    do
        mv ${file%png}txt ${file%png}${ocr}.txt
        mv ${file%png}prob ${file%png}${ocr}.prob
    done
done

# concatenate to csv files (input tab output newline)...
for ocr in deu-frak3 Fraktur4 foo4 ocrofraktur ocrofraktur-jze #fraktur19-00050000
do
    for data in traindata testdata
    do
        out=${data}.${ocr}-gt.pkl
        test -s "$out" && echo "skipping $out" || {
                echo "collecting $out"
                # does not work with python 2 (csv...)
                python <<EOF - $out ${data}/*.${ocr}.prob
import sys
import csv
from io import open
import pickle
lines = []
for ocrname in sys.argv[2:]:
    gtname = u".".join(ocrname.split(u".")[:-2]) + u".gt.txt"
    with open(ocrname, mode='r', encoding='utf-8') as ocr:
        ocrprobs = csv.reader(ocr, delimiter=str(u'\t'), strict=True, quoting=csv.QUOTE_NONE)
        ocrline = []
        for row in ocrprobs:
            p = float(row[1])
            for c in (row[0]):
                ocrline.append((c,p))
        ocrline.append((u'\n', 1.0))
    with open(gtname, mode='r', encoding='utf-8') as gt:
        gtline = gt.read()
    lines.append((ocrline, gtline))
pickle.dump(lines, open(sys.argv[1], mode='wb'))
EOF
            }
        out=${data}.${ocr}-gt.txt
        test -s "$out" && echo "skipping $out" && continue
        echo "collecting $out"
        touch $out
        for file in ${data}/*.${ocr}.txt
        do
            # insert numerically sorted by length of ocr line:
            sort -n -o "$out" -m <({
                                      wc -c < "$file"; # sort key
                                      # only needed with normal tesseract CLI:
                                      #tr -d '\f\r' < "$file"# OCR result without formfeed
                                      #wc -l "$file" | { read n name; test $n -eq 0 && echo; } # ensure newline
                                      # faster, enough for ocropus-rpred and tesserocr-batch:
                                      cat "$file" # OCR result
                                      test -s "$file" || echo; # ensure newline
                                      cat ${file%.${ocr}.txt}.gt.txt # GT
                                  } | tr '\t\n' ' \t') "$out" # as one line
        done
        # remove length column and trailing tab:
        sed -i 's/^[^	]*	//;s/	$//' "$out"
        echo "filtering ${out%.txt}.filtered.txt"
        # filter failed OCR lines:
        egrep -v -e '(.)\1{4,}' -e '[[:punct:]]{6,}' <"$out" | while IFS=$'\t' read source target; do
            if test $((2*${#source})) -lt ${#target} -a $((${#target}-${#source})) -gt 5; then : #echo "$source      $target" >&2;
            else echo "${source@E}	${target@E}"; fi;
        done >"${out%.txt}.filtered.txt"
        #echo "augmenting ${out%.txt}.filtered.augmented.txt"
        ## augment by more true pairs:
        #sed 'h;s/^[^	]*	//;s/^.*$/&	&/;p;p;p;p;g' <"${out%.txt}.filtered.txt" >"${out%.txt}.filtered.augmented.txt"
        ## make another file with character counts:
        #while IFS=$'\t' read source target; do echo "${#source} ${#target}"; done <"${out%.txt}.filtered.augmented.txt" >"${out%.txt}.filtered.augmented.len"
    done
done
exit
# concatenate to single files (one file per ocr)...
for ocr in gt foo4 Fraktur4 deu-frak3 ocrofraktur ocrofraktur-jze #fraktur19-00050000
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
              wc -l $realfile | { read n name; test $n -eq 0 && echo; } # ensure newline
            } >> $out
        done
    done
done
