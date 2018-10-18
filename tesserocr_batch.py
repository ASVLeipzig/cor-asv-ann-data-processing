from __future__ import absolute_import

import click

@click.command()
@click.option('-l', '--language', default='eng', help='specify language(s) used for OCR')
@click.option('-x', '--extension', help='filename base extension to use for outputs (.txt/.prob)')
@click.option('-Q', '--nprocs', default=1, type=int, help='number of processes to run in parallel')
@click.argument('input_files', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def process(language, extension, nprocs, input_files):
    import locale
    locale.setlocale(locale.LC_ALL, 'C') # circumvent tesseract-ocr issue 1670 (which cannot be done on command line because Click requires an UTF-8 locale in Python 3)
    
    from tesserocr import RIL, PSM, PyTessBaseAPI, PyResultIterator, get_languages
    import os, logging
    from io import open

    TESSDATA_PREFIX = os.environ['TESSDATA_PREFIX'] if 'TESSDATA_PREFIX' in os.environ else get_languages()[0]
    CHOICE_THRESHOLD_NUM = 6 # maximum number of choices to query and annotate
    CHOICE_THRESHOLD_CONF = 0.2 # maximum score drop from best choice to query and annotate
    MAX_ELEMENTS = 500 # maximum number of lower level elements embedded within each element (for word/glyph iterators)

    # todo: implement nprocs by multiprocessing.Pool(processes=nprocs).map(func, params)
    logging.basicConfig()
    log = logging.getLogger('')
    log.setLevel(logging.INFO)
    if language not in get_languages()[1]:
        raise Exception("configured language " + language + " is not installed")
    with PyTessBaseAPI(path=TESSDATA_PREFIX, lang=language) as tessapi:
        #tessapi.SetVariable("tessedit_create_txt", "1")
        #tessapi.SetVariable("glyph_confidences", "2")        
        for n, input_file in enumerate(input_files):
            tessapi.SetImageFile(input_file)
            psm = PSM.SINGLE_LINE if language == 'deu-frak' else PSM.RAW_LINE # RAW_LINE fails with Tesseract 3 models and is worse with Tesseract 4 models
            tessapi.SetPageSegMode(psm)
            if not extension:
                extension = u'.' + language
            output_file = os.path.splitext(input_file)[0] + extension + u'.txt'
            log.info(u'processing "%s" -> "%s"', input_file, output_file)
            tessapi.Recognize()
            with open(output_file, mode='w', encoding='utf-8') as output:
                output.write(tessapi.GetUTF8Text().rstrip(u"\f"))
            output_file = os.path.splitext(input_file)[0] + extension + u'.prob'
            log.info(u'processing "%s" -> "%s"', input_file, output_file)
            with open(output_file, mode='w', encoding='utf-8') as output:
                result_it = tessapi.GetIterator()
                for word_no in range(0,MAX_ELEMENTS): # iterate until IsAtFinalElement(RIL.LINE, RIL.WORD)
                    if result_it.Empty(RIL.WORD):
                        break
                    #word_bbox = result_it.BoundingBox(RIL.WORD)
                    #word_attributes = result_it.WordFontAttributes()
                    # do sth on word result
                    for glyph_no in range(0,MAX_ELEMENTS): # iterate until IsAtFinalElement(RIL.WORD, RIL.SYMBOL)
                        if result_it.Empty(RIL.SYMBOL):
                            break
                        glyph_symb = result_it.GetUTF8Text(RIL.SYMBOL) # equals first choice?
                        glyph_conf = result_it.Confidence(RIL.SYMBOL)/100 # equals first choice?
                        #glyph_bbox = result_it.BoundingBox(RIL.SYMBOL)
                        # do sth on glyph result
                        output.write(u"%s\t%f\n" % (glyph_symb, glyph_conf))
                        # choice_it = result_it.GetChoiceIterator()
                        # for (choice_no, choice) in enumerate(choice_it):
                        #     alternative_symb = choice.GetUTF8Text()
                        #     alternative_conf = choice.Confidence()/100
                        #     if (glyph_conf-alternative_conf > CHOICE_THRESHOLD_CONF or
                        #         choice_no > CHOICE_THRESHOLD_NUM):
                        #         break
                        #     # do sth on choice result
                        if result_it.IsAtFinalElement(RIL.WORD, RIL.SYMBOL):
                            if not result_it.IsAtFinalElement(RIL.TEXTLINE, RIL.WORD):
                                output.write(u" \t1.0\n")
                            break
                        else:
                            result_it.Next(RIL.SYMBOL)
                    if result_it.IsAtFinalElement(RIL.TEXTLINE, RIL.WORD):
                        break
                    else:
                        result_it.Next(RIL.WORD)

            tessapi.Clear()
            #tessapi.ClearAdaptiveClassifier()

