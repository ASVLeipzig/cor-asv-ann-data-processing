#!/usr/bin/python3
from __future__ import absolute_import

from io import open
import pickle
import click

@click.command()
@click.argument('output_file', nargs=1, type=click.Path(writable=True, dir_okay=False))
@click.argument('input_files', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def cli(output_file, input_files):
    '''Aggregate OCR result and GT text files into a single pickle dump.
    
    Open each .confmat file from `input_files`, along with 
    its .gt.txt file. 
    Parse the .confmat file as pickle dump.
    Make a tuple from that dump and the GT string.
    
    Put all such lines into one list and dump as `output_file`.
    '''
    lines = []
    for ocrname in input_files:
        nameparts = ocrname.split(".")[:-2]
        if nameparts[-1] in ['nrm', 'bin']:
            nameparts.pop()
        gtname = ".".join(nameparts) + ".gt.txt"
        ocrline = pickle.load(open(ocrname, mode='rb'))
        with open(gtname, mode='r', encoding='utf-8') as gt:
            gtline = gt.read()
        lines.append((ocrline, gtline))
    pickle.dump(lines, open(output_file, mode='wb'))

if __name__ == '__main__':
    cli()
