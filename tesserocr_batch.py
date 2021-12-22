from __future__ import absolute_import

import os, logging
import pickle
import multiprocessing as mp
import click

@click.command()
@click.option('-l', '--language', default='eng', help='specify language(s) used for OCR')
@click.option('-x', '--extension', help='filename base extension to use for outputs (.txt/.prob)')
@click.option('-Q', '--nprocs', default=1, type=int, help='number of processes to run in parallel')
@click.argument('input_files', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def process(language, extension, nprocs, input_files):
    from tesserocr import get_languages
    TESSDATA_PREFIX = os.environ['TESSDATA_PREFIX'] if 'TESSDATA_PREFIX' in os.environ else get_languages()[0]
    logging.basicConfig()
    log = logging.getLogger('')
    log.setLevel(logging.INFO)
    for sublanguage in language.split('+'):
        if sublanguage not in get_languages()[1]:
            raise Exception("configured language " + sublanguage + " is not installed")
    
    def init_worker(worker, log, tessdata_prefix, language, extension):
        from tesserocr import PyTessBaseAPI
        worker.log = log
        worker.language = language
        worker.tessapi = PyTessBaseAPI(path=tessdata_prefix, lang=language)
        worker.extension = extension
        #worker.tessapi.SetVariable("tessedit_create_txt", "1")
        worker.tessapi.SetVariable("lstm_choice_mode", "2")
    with mp.Pool(processes=nprocs,
                 initializer=init_worker,
                 initargs=(process_file, log, TESSDATA_PREFIX, language, extension)) as pool:
        result = pool.map_async(process_file, input_files, error_callback=log.error)
        result.wait()
        if result.successful():
            log.info('all done')
        else:
            log.error('error during processing')
            exit(1)

def process_file(input_file):
    from tesserocr import RIL, PSM, PyResultIterator
    from io import open
    
    CHOICE_THRESHOLD_NUM = 6 # maximum number of choices to query and annotate
    CHOICE_THRESHOLD_CONF = 0.2 # maximum score drop from best choice to query and annotate
    MAX_ELEMENTS = 500 # maximum number of lower level elements embedded within each element (for word/glyph iterators)
    
    # get globals
    log = process_file.log
    language = process_file.language
    tessapi = process_file.tessapi
    extension = process_file.extension
    
    # recognize
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
    output_file = os.path.splitext(input_file)[0] + extension + u'.confmat'
    log.info(u'processing "%s" -> "%s"', input_file, output_file)
    line = []
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
            glyph = []
            glyph_symb = result_it.GetUTF8Text(RIL.SYMBOL) # equals first choice?
            glyph_conf = result_it.Confidence(RIL.SYMBOL)/100 # equals first choice?
            #glyph_bbox = result_it.BoundingBox(RIL.SYMBOL)
            # do sth on glyph result
            choice_it = result_it.GetChoiceIterator()
            for (choice_no, choice) in enumerate(choice_it):
                alternative_symb = choice.GetUTF8Text()
                alternative_conf = choice.Confidence()/100
                if (glyph_conf-alternative_conf > CHOICE_THRESHOLD_CONF or
                    choice_no > CHOICE_THRESHOLD_NUM):
                    break
                glyph.append((alternative_symb, alternative_conf))
            line.append(glyph)
            if result_it.IsAtFinalElement(RIL.WORD, RIL.SYMBOL):
                if not result_it.IsAtFinalElement(RIL.TEXTLINE, RIL.WORD):
                    line.append([(' ', 1.0)])
                else:
                    line.append([('\n', 1.0)])
                break
            else:
                result_it.Next(RIL.SYMBOL)
        if result_it.IsAtFinalElement(RIL.TEXTLINE, RIL.WORD):
            break
        else:
            result_it.Next(RIL.WORD)
    pickle.dump(line, open(output_file, mode='wb'))
    
    tessapi.Clear()
    #tessapi.ClearAdaptiveClassifier()

if __name__ == '__main__':
    process()
