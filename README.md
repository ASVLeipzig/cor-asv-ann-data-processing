# Introduction

This describes steps to prepare plaintext or METS/PAGE-XML
corpora for command-line processing (as opposed to workspace
processing) on _contiguous_ texts (as opposed to _isolated_
lines) with **cor-asv-ann**.

Data files for training, validation and testing with cor-asv-ann
can be either:
- (newline-delimited) CSV files with OCR lines in the first
  column and GT lines in the second, separated by tab, or
- Python pickle dumps with line lists of OCR-GT tuples, where
  the GT part is a line string and the OCR part is a list of
  character-confidence tuples.
- Python pickle dumps with line lists of OCR-GT tuples, where
  the GT part is a line string and the OCR part is a list of
  chunks, with each chunk a list of alternatives, with each
  alternative a string-confidence tuple. (The alternatives
  among a chunk may have varying length.)

# Data

We can use both text corpora (for pretraining) and OCR ground truth
corpora (i.e. textline images with correct textual transcriptions,
where OCR results can be added for different models and setups),
both historical and contemporary.

## text corpora

- Deutsches Textarchiv (DTA): http://www.deutsches-textarchiv.de/download

## OCR GT

- GT4HistOCR: https://zenodo.org/record/1344132
  (cropped line PNG files and plaintext files,
   distributed in directories for subcorpora and
   book titles, filenames include page and line
   numbers, i.e. can be made contiguous)

- OCR-D GT: https://ocr-d-repo.scc.kit.edu/api/v1/metastore/bagit
  (OCR-D-ZIP format, i.e. BagIt with METS-XML container,
   page TIF files, and PAGE-XML annotations including
   textline layout and textline text)

# Tools

- _dta-txt.sh_: download TCF versions of DTA, extract plaintexts
- _dta-txt2gt_: ensure lines are wrapped/hyphenated in plaintexts
  (via hunspell rules), replace all tabs

- _tesserocr-batch_:
  use Tesseract to recognize multiple textline images at once
  (with CPU-parallel multiprocessing), also generate .prob files
  (character-confidence tuples) and .confmat files
  (chunk-alternative-confidence lists)
- _ocropus-rpred_ (from standard ocropy installation):
  use Ocropy to recognize multiple textline images at once
  (with CPU-parallel multiprocessing), also generate .prob files
  (character-confidence tuples)
- _prob2pkl_: zip OCR .txt / .prob files and GT .txt files into
  pickle format usable for CLI training/testing
- _confmat2pkl_: zip OCR .confmat files and GT .txt files into
  pickle format usable for CLI training/testing

- _ocrd-tesserocr-recognize_ (from ocrd_tesserocr installation):
  open METS/PAGE-XML workspace, read line GT annotation,
  use Tesseract to recognize textline image rectangles, generate
  new glyph annotation with character and confidence results
- _ocrd-cis-ocropy-recognize_ (from cis-ocrd-py installation):
  open METS/PAGE-XML workspace, read line GT annotation,
  use Ocropy to crop, scale, deskew and binarize textline image
  rectangles, then use Ocropy to recognize them, generate
  new glyph annotation with character and confidence results
- _ocrd-gt2pkl_: open METS/PAGE-XML workspace, read line GT and glyph OCR
  (with confidence and/or alternatives), concatenate with spaces and newlines,
  zip into pickle format

- _cor-asv-ann-train_ (from cor-asv-ann installation):
  pretraining and retraining of post-correction model
  (with CSV or pkl files, OCR+GT text)
- _cor-asv-ann-eval_ (from cor-asv-ann installation):
  test+evaluation of post-correction model
  (with CSV or pkl files, OCR+GT text)

# Recipes

commands to install package and setup shell:
```sh
virtualenv -p python3 .env3 # unless already done
source .env3/bin/activate # for tesserocr-batch, pyphen, ocrd, cor-asv-ann etc
pip install -e . # unless already done
shopt -s nullglob # empty glob patterns are no error
ulimit -n 5000 # for large directories
```

commands to convert (parts of) DTA into text-only GT (for pretraining):
```sh
bash dta-txt.sh # download and extract plaintexts
# take every 50th file from 19th century for training:
mkdir path/to/traindata
for file in $(ls -1 dta_komplett_2018-02-23/txt/*_18??.tcf.txt | sed -n 1~50p); do 
    # ensure short lines:
    dta-txt2gt < $file > path/to/traindata/$(basename ${file/tcf/gt})
    # convert to CSV (OCR=GT, separated by tab):
    sed 's/^.*$/&	&/' < path/to/traindata/$(basename ${file/tcf/gt}) > path/to/traindata/$(basename ${file/tcf/gt-gt})
done
# take every 200th file from 19th century for testing:
mkdir path/to/testdata
for file in $(ls -1 dta_komplett_2018-02-23/txt/*_18??.tcf.txt | sed -n 2~200p); do 
    # ensure short lines:
    dta-txt2gt < $file > path/to/testdata/$(basename ${file/tcf/gt})
    # convert to CSV (OCR=GT, separated by tab):
    sed 's/^.*$/&	&/' < path/to/testdata/$(basename ${file/tcf/gt}) > path/to/testdata/$(basename ${file/tcf/gt-gt})
done
```

commands for OCR processing of line-GT (like data from GT4HistOCR):
```sh
# Tesseract:
for ocr in Fraktur4 foo4 deu-frak3 deu4 Latin4; do
    # to avoid redoing files already processed
    # in a larger directory, control globbing:
    GLOBIGNORE=$(echo path/to/*.$ocr.prob | sed "s/$ocr.prob/png/g;s/ /:/g")
    # produce .*.txt and .*.prob and .*.confmat files:
    tesserocr-batch -Q8 -l ${ocr%?} -x .$ocr path/to/*.png
    unset GLOBIGNORE
    prob2pkl path/to/$ocr-gt.prob.pkl path/to/*.prob
    confmat2pkl path/to/$ocr-gt.confmat.pkl path/to/*.confmat
done
# ocropus:
for ocr in ocrofraktur ocrofraktur-jze #fraktur19-00050000
do
    # to avoid redoing files already processed
    # in a larger directory, control globbing:
    GLOBIGNORE=$(echo path/to/*.$ocr.prob | sed "s/$ocr.prob/png/g;s/ /:/g")
    ocropus-rpred -Q4 -q -n -m ${ocr#ocro}.pyrnn.gz --probabilities path/to/*.png
    # ocropus always uses same suffix, so rename:
    for file in path/to/*.png
    do
        mv ${file%@(nrm|bin).png}txt ${file%png}${ocr}.txt
        mv ${file%@(nrm|bin).png}prob ${file%png}${ocr}.prob
    done
    unset GLOBIGNORE
    prob2pkl path/to/$ocr-gt.pkl path/to/*.prob
done
# then split into files for traindata and testdata (symlinks)...
```

commands for OCR processing of OCR-D GT:
```sh
for file in *.zip; do 
    mets=${file%.zip}/data/mets.xml
    # skip if pre-bagit GT (no workspace):
    test -f $mets || continue
    # make workspace backup:
    ocrd workspace -d ${mets%/mets.xml} backup add
    # use glyph level, Fraktur model:
    ocrd-tesserocr-recognize -m $mets -I OCR-D-GT-SEG-LINE -O OCR-D-OCR-TESS-FRAKTUR -p - <<<'{ "textequiv_level": "glyph", "model": "Fraktur", "overwrite_lines": true }'
    # use glyph level, deu-frak model (gives true alternatives):
    ocrd-tesserocr-recognize -m $mets -I OCR-D-GT-SEG-LINE -O OCR-D-OCR-TESS-DEUFRAK -p - <<<'{ "textequiv_level": "glyph", "model": "deu-frak", "overwrite_lines": true }'
    # ...
    # use glyph level, Fraktur model, with deskewing+binarization:
    ocrd-cis-ocropy-recognize -m $mets -I OCR-D-GT-SEG-LINE -O OCR-D-OCR-OCRO-FRAKTUR -p - <<<'{ "textequiv_level": "glyph", "model": "fraktur.pyrnn", "dewarping": true, "binarization": "ocropy" }'
    # ...
    # make another workspace backup:
    ocrd workspace -d ${mets%/mets.xml} backup add
done
for mets in $(find . -name mets.xml -not -path "*/.backup/*"); do 
    ocrd-gt2pkl -G OCR-D-GT-SEG-LINE -O OCR-D-OCR-TESS-FRAKTUR $mets ${mets%/data/mets.xml}.Fraktur4-gt.pkl
    ocrd-gt2pkl -G OCR-D-GT-SEG-LINE -O OCR-D-OCR-TESS-DEUFRAK -w $mets ${mets%/data/mets.xml}.deu-frak3-gt.confmat.pkl
    ocrd-gt2pkl -G OCR-D-GT-SEG-LINE -O OCR-D-OCR-OCRO-FRAKTUR -w $mets ${mets%/data/mets.xml}.ocrofraktur-gt.pkl
done
# then split into files for traindata and testdata (symlinks)...
```

commands for training a language model of matching topology and conversion:
```sh
source env3/bin/activate # for ocrd_keraslm
# train a language model with window length 512 characters
# on 19th century DTA plaintexts:
keraslm-rate train -w WIDTH -d DEPTH -l 512 -m model_dta18_DEPTH_WIDTH_512.h5 dta_komplett_2018-02-23/txt/*_18??.tcf.txt
python transfer-dta-lm.py model_dta18_DEPTH_WIDTH_512.h5 lm-char.DEPTH.WIDTH.dta18.h5
```

commands for pretraining, retraining and evaluation:
```sh
# transfer weights from LM, pretrain on clean text, -v for each valdata file:
cor-asv-ann-train --init-model lm-char.DEPTH.WIDTH.dta18.h5 --save-model s2s.CORPUS.gt.transfer-lm.pretrained.h5 -w WIDTH -d DEPTH $(for file in path/to/CORPUS/testdata/*.gt-gt.txt; do echo -nE " -v $file"; done) path/to/CORPUS/traindata/*.gt-gt.txt
# load weights from pretrained model, then reset encoder (keep only decoder weights),
# retrain on OCR text with confidences, -v for valdata files:
cor-asv-ann-train --load-model s2s.CORPUS.gt.transfer-lm.pretrained.h5 -w WIDTH -d DEPTH --save-model s2s.CORPUS.OCR.transfer-lm.pretrained+retrained-conf.h5 $(for file in path/to/CORPUS/testdata/*.OCR-gt.pkl; do echo -nE " -v $file"; done) path/to/CORPUS/traindata/*.OCR-gt.pkl
# load model and predict on OCR text with confidences, 
# align with GT and evaluate error rates:
cor-asv-ann-eval --load-model s2s.CORPUS.OCR.transfer-lm.pretrained+retrained-conf.h5 path/to/CORPUS/testdata/*.OCR-gt.pkl
```
