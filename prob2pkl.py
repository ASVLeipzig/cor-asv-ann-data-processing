#!/usr/bin/python3
# does not work with python 2 (csv...)
from __future__ import absolute_import

import csv
from io import open
import os.path
import pickle
import click

@click.command()
@click.argument('output_file', nargs=1, type=click.Path(writable=True, dir_okay=False))
@click.argument('input_files', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def cli(output_file, input_files):
    '''Aggregate OCR result and GT text files into a single pickle dump.
    
    Open each .prob file from `input_files`, along with 
    its .gt.txt file. 
    Parse the .prob file as CSV with tab as delimiter. 
    Make a list of character-probability tuples from OCR.
    Make a tuple from that list and the GT string.
    
    Put all such lines into one list and dump as `output_file`.
    '''
    if os.path.exists(output_file):
        lines = pickle.load(open(output_file, mode='rb'))
    else:
        lines = []
    for ocrname in input_files:
        nameparts = ocrname.split(".")[:-2]
        if nameparts[-1] in ['nrm', 'bin']:
            nameparts.pop()
        gtname = ".".join(nameparts) + ".gt.txt"
        with open(ocrname, mode='r', encoding='utf-8') as ocr:
            ocrprobs = csv.reader(ocr, delimiter=str('\t'), strict=True, quoting=csv.QUOTE_NONE)
            ocrline = []
            for row in ocrprobs:
                p = float(row[1])
                for c in (row[0]):
                    ocrline.append((c,p))
            ocrline.append(('\n', 1.0))
        with open(gtname, mode='r', encoding='utf-8') as gt:
            gtline = gt.read()
        lines.append((ocrline, gtline))
    pickle.dump(lines, open(output_file, mode='wb'))

if __name__ == '__main__':
    cli()
