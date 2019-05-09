#!/usr/bin/python3
from __future__ import absolute_import

import os
import pickle
import click

from ocrd.resolver import Resolver
from ocrd_modelfactory import page_from_file

@click.command()
@click.option('-G', '--gt-file-grp', default='OCR-D-GT-SEG-LINE', help='METS fileGrp holding ground truth')
@click.option('-O', '--ocr-file-grp', default='OCR-D-OCR-TESS4G', help='METS fileGrp holding OCR results')
@click.option('-w', '--with-alternatives', is_flag=True, help='read all textequiv readings, produce confmat pkl')
@click.argument('input_file', nargs=1, type=click.Path(exists=True, dir_okay=False))
@click.argument('output_file', nargs=1, type=click.Path(writable=True, dir_okay=False))
def cli(gt_file_grp, ocr_file_grp, with_alternatives, input_file, output_file):
    '''Open a METS/PAGE-XML workspace and convert into a OCR/GT pickle dump.
    
    Open each file in the file groups `gt-file-grp` and `ocr-file-grp`.
    Read TextEquiv annotation for lines from both parts respectively,
    TextLine from GT, and Glyph from OCR:
    Make a list of character-confidence tuples from OCR, by
    joining Word elements with additional spaces and
    appending newline at the end of TextLine.
    Make a tuple from that list and the GT line string.
    
    Put all such lines into one list and dump as `output_file`.
    '''
    resolver = Resolver()
    workspace = resolver.workspace_from_url(input_file)
    ocr_files = workspace.mets.find_files(fileGrp=ocr_file_grp)
    gt_files = workspace.mets.find_files(fileGrp=gt_file_grp)
    text = []
    assert len(ocr_files) == len(gt_files),\
        "workspace %s annotation inconsistent: OCR %s / GT %s" % (input_file, ocr_files, gt_files)
    for ocr_file, gt_file in zip(ocr_files, gt_files):
        ocr_pcgts = page_from_file(workspace.download_file(ocr_file))
        gt_pcgts = page_from_file(workspace.download_file(gt_file))
        ocr_regions = ocr_pcgts.get_Page().get_TextRegion()
        gt_regions = gt_pcgts.get_Page().get_TextRegion()
        assert len(ocr_regions) == len(gt_regions)
        for ocr_region, gt_region in zip(ocr_regions, gt_regions):
            ocr_lines = ocr_region.get_TextLine()
            gt_lines = gt_region.get_TextLine()
            assert len(ocr_lines) == len(gt_lines)
            for ocr_line, gt_line in zip(ocr_lines, gt_lines):
                ocr_conf = []
                ocr_words = ocr_line.get_Word()
                for ocr_word in ocr_words:
                    ocr_glyphs = ocr_word.get_Glyph()
                    if ocr_conf:
                        if with_alternatives:
                            ocr_conf.append([(' ', 1.0)])
                        else:
                            ocr_conf.append((' ', 1.0))
                    for ocr_glyph in ocr_glyphs:
                        textequiv = ocr_glyph.get_TextEquiv()
                        if with_alternatives:
                            ocr_conf.append([(alternative.Unicode, alternative.conf or 1.0)
                                             for alternative in textequiv])
                        elif textequiv:
                            ocr_conf.extend([(char, textequiv[0].conf or 1.0)
                                             for char in textequiv[0].Unicode])
                if with_alternatives:
                    ocr_conf.append([('\n', 1.0)])
                else:
                    ocr_conf.append(('\n', 1.0))
                #ocr_text = ocr_line.get_TextEquiv()[0].Unicode.rstrip() + '\n'
                #assert ocr_text == ''.join([c for c,p in ocr_conf]), \
                #    "line does not concatenate from glyphs: %s / %s" % (ocr_text, ''.join([c for c,p in ocr_conf]))
                text.append((ocr_conf, gt_line.get_TextEquiv()[0].Unicode.rstrip() + '\n'))
    pickle.dump(text, open(output_file, mode='wb'))

if __name__ == '__main__':
    cli()
