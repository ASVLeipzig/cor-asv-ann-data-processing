#!/usr/bin/python3
from __future__ import absolute_import

import click
import pyphen

@click.command()
# 135: make sure not to touch texts that are already wrapped
@click.option('-w', '--width', default=135, type=int, help='number of characters to wrap at')
# de_DE: good enough for historic texts
@click.option('-l', '--lang', default='de_DE', help='locale to use for hyphenation')
@click.option('-h', '--hyphen', default='—', help='hyphenation character to use')
def cli(width, lang, hyphen):
    '''Wrap long lines and hyphenate according to locale.
    
    Read standard input, split lines longer than `width`,
    try to hyphenate tokens around that position by rules
    for `lang` localisation. Use `hyphen` as hyphenation
    character. Write to standard output.
    
    Also, replace tabs with spaces, and replace "¬" with
    true hyphen.
    '''
    dic = pyphen.Pyphen(lang='de_DE')
    for line in sys.stdin:
        line = line.replace('\t', ' ') # already needed as separator, not in OCR
        line = line.replace('¬', hyphen) # DTA vs OCR/GT hyphen
        tokens = line.split(' ')
        i = 0
        for token in tokens:
            if i > 0:
                print(' ', end='')
            if i < width:
                print(token, end='')
                i += len(token) + 1
            else:
                p = dic.positions(token)
                if p:
                    print(token[:p[0]] + hyphen) # including newline
                    print(token[p[0]:], end='')
                    i = len(token) - p[0]
                else:
                    print(token) # including newline
                    i = 0
        print('') # only newline
