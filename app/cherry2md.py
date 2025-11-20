#!/bin/python
# app/cherry2md.py
'''
Runner file.
'''
from contextlib import redirect_stdout
import sys

# import cherry2mdlib.config as c
import config as c
import cherry2mdlib.exporter as exp    
from cherry2mdlib.notes import Note
from cherry2mdlib.utils import StdOutToFile, Cherry2mdException,\
                               get_current_function_name


def start():
    '''Main routine; calls the parser, writes the files and prints results.'''
    c.v3 and print(f'running: {get_current_function_name()} ...')
    exp.start_parser(c.xml_filepath)
    # covnversion is ready, print results:
    print(f'\n  Notes converted to markdown: {Note.counters.get('notes-written', 0)}\n')
    if c.dry_run:
        print('  Conversion ran in dry-run mode, no files were actually written.\n')
    if c.v1:
        print(f'  {"="*30}\n')
        for name, count in Note.counters.items():
            print(f'  {name:22} : {count:5}')
        print(f'\n  {"="*30}\n')
    if c.v2:
        print(f'  using data dir   : {c.get_data_dir()}')
        print(f'  the markdown dir : {c.markdown_dir}')
        print(f'  the images dir   : {c.images_dir}')
        print(f'  the pdf dir      : {c.pdf_dir}')
        print(f'  the others dir   : {c.others_dir}')
        print(f'  logfile created  : {c.get_logpath()}')
        print(f'  XML-path (input) : {c.xml_filepath}\n')

if __name__ == '__main__':

    # if option 'quiet' was applicated on the commandline, then the 
    # contextmanager StdOutToFile will deal with this
    try:
        c.init_config()
        with StdOutToFile(c._stdout_filepath , c.quiet):
            start()
    except Cherry2mdException as ex:
        print(f'Error: {ex}', file=sys.stderr)
