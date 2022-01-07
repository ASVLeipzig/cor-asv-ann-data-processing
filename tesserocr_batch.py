from __future__ import absolute_import

import os, logging
import pickle
import multiprocessing as mp
import click

@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-l', '--language', default='eng', type=str, help='specify language(s) used for OCR')
@click.option('-x', '--textsuf', default='.txt', type=str, help='file name suffix to use for text output (empty to use stdout)')
@click.option('-P', '--probsuf', default='.prob', type=str, help='file name suffix to use for characters probabilities (empty to disable)')
@click.option('-C', '--choicesuf', default='.confmat', type=str, help='file name suffix to use for alternative characters and their probabilities (empty to disable)')
@click.option('-Q', '--nprocs', default=1, type=int, help='number of processes to run in parallel')
@click.argument('input_files', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def process(language, textsuf, probsuf, choicesuf, nprocs, input_files):
    from tesserocr import get_languages
    TESSDATA_PREFIX = os.environ['TESSDATA_PREFIX'] if 'TESSDATA_PREFIX' in os.environ else get_languages()[0]
    logging.basicConfig()
    log = logging.getLogger('')
    log.setLevel(logging.INFO)
    for sublanguage in language.split('+'):
        if sublanguage not in get_languages()[1]:
            raise Exception("configured language " + sublanguage + " is not installed")
    
    def init_worker(worker):
        from tesserocr import PyTessBaseAPI
        worker.log = log
        worker.language = language
        worker.tessapi = PyTessBaseAPI(path=TESSDATA_PREFIX, lang=language)
        worker.text = textsuf
        worker.probabilities = probsuf
        worker.choices = choicesuf
        #worker.tessapi.SetVariable("tessedit_create_txt", "1")
        worker.tessapi.SetVariable("lstm_choice_mode", "2")
    with mp.Pool(processes=nprocs,
                 initializer=init_worker,
                 initargs=(process_file,)) as pool:
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
    
    CHOICE_THRESHOLD_NUM = 10 # maximum number of choices to query and annotate
    CHOICE_THRESHOLD_CONF = 1.0 # maximum score drop from best choice to query and annotate
    MAX_ELEMENTS = 500 # maximum number of lower level elements embedded within each element (for word/glyph iterators)
    
    # get globals
    log = process_file.log
    language = process_file.language
    tessapi = process_file.tessapi
    text = process_file.text
    prob = process_file.probabilities
    alts = process_file.choices

    basename = os.path.splitext(input_file)[0]
    # recognize
    tessapi.SetImageFile(input_file)
    psm = PSM.SINGLE_LINE if language == 'deu-frak' else PSM.RAW_LINE # RAW_LINE fails with Tesseract 3 models and is worse with Tesseract 4 models
    tessapi.SetPageSegMode(psm)
    with open(basename + text, mode='w', encoding='utf-8') if text else sys.stdout as text_output, \
         open(basename + prob, mode='w', encoding='utf-8') if prob else None as prob_output, \
         open(basename + alts, mode='wb') if alts else None as alts_output:
        log.info('processing "%s"', input_file)
        tessapi.Recognize()
        text_output.write(tessapi.GetUTF8Text().rstrip(u"\f"))
        line = []
        result_it = tessapi.GetIterator()
        for word_no, _ in enumerate(iterate_level(result_it, RIL.WORD)):
            #word_bbox = result_it.BoundingBox(RIL.WORD)
            #word_attributes = result_it.WordFontAttributes()
            # do sth on word result
            for glyph_no, _ in enumerate(iterate_level(result_it, RIL.SYMBOL)):
                glyph = []
                glyph_symb = result_it.GetUTF8Text(RIL.SYMBOL)
                glyph_conf = result_it.Confidence(RIL.SYMBOL)/100
                #glyph_bbox = result_it.BoundingBox(RIL.SYMBOL)
                # do sth on glyph result
                if alts_output:
                    choice_it = result_it.GetChoiceIterator()
                    for choice_no, choice in enumerate(choice_it):
                        alt_symb = choice.GetUTF8Text()
                        alt_conf = choice.Confidence()/100
                        if (glyph_conf - alt_conf > CHOICE_THRESHOLD_CONF or
                            choice_no > CHOICE_THRESHOLD_NUM):
                            break
                        glyph.append((alt_symb, alt_conf))
                    line.append(glyph)
                if prob_output:
                    prob_output.write("%s\t%f\n" % (glyph_symb, glyph_conf))
                if result_it.IsAtFinalElement(RIL.WORD, RIL.SYMBOL):
                    if not result_it.IsAtFinalElement(RIL.TEXTLINE, RIL.WORD):
                        line.append([(' ', 1.0)])
                        if prob_output:
                            prob_output.write(" \t1.0\n")
                    else:
                        line.append([('\n', 1.0)])
        if alts_output:
            pickle.dump(line, alts_output)
    
    tessapi.Clear()
    #tessapi.ClearAdaptiveClassifier()

def iterate_level(it, ril, parent=None):
    # improves over tesserocr.iterate_level by
    # honouring multi-level semantics so iterators
    # can be combined across levels
    if parent is None:
        parent = ril - 1
    while it and not it.Empty(ril):
        yield it
        if ril > 0 and it.IsAtFinalElement(parent, ril):
            break
        it.Next(ril)

if __name__ == '__main__':
    process()
