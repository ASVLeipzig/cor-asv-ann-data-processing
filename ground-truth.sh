#!/bin/bash
mkdir -p ground-truth
cd ground-truth
rm -f IndexGT.html
wget http://www.ocr-d.de/sites/all/GTDaten/IndexGT.html
for file in $(grep -o '"[^"]*[.]zip"' IndexGT.html | tr -d '"')
do
    test -f $file || wget http://www.ocr-d.de/sites/all/GTDaten/$file
done
test -d assets || git clone https://github.com/OCR-D/assets

