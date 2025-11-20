import argparse
import os
from pathlib import Path
import shutil
import sys
import textwrap
import tomllib

from cherry2mdlib.utils import Cherry2mdConfigError, read_kbd_input,\
                               get_current_function_name

# global vars
                           
'Commandline option: verbosity indicator'
v1, v2, v3, = False, False, False

'Commandline option: quiet; if True stdout goes to a file .'
quiet = False

'Commandline option: dry run; if True no files are created.'
dry_run = False

'Commandline option: unique_id, convert only that note'
unique_id = None

'Commandline option: absolute_path, for references inside notes'
abs_path = False

'Environment var: write all notes in one bigfile (debugging)'
debug_bigfile = False
 
'Base dir for other dirs'
_data_dir = None

'Directory for storing the Cherrytree XML-files.'
xml_dir = None

'Directory used for the output of generated markdown notes'
target_dir = None

'Directory used for the output of generated attachments like PDF and others.'
markdown_dir, images_dir, pdf_dir, others_dir = None, None, None, None

'Directory used for log files.'
log_dir = None

'File opened for reading XML data'
xml_filepath = None

'File opened for logging'
log_filepath = None

'File opened for standard output redirection'
_stdout_filepath = None

'Start index number for numbering attachment files.'
attachment_index = 1

# TOML config file preferences

path = Path(__file__).parent / "cherry2md.toml"
with path.open(mode="rb") as fp:
    prefs = tomllib.load(fp)

if cnt := len(prefs.get('data').get('skip_notes', [])):
    print(f'warning: there are {cnt} notes excluded by your TOML config-file')

# functions

def get_data_dir():
    return _data_dir

def get_logpath():
    return log_filepath


def parse_arguments():
    '''Parse the commandline arguments.'''
    
    v3 and print(f'running: {get_current_function_name()} ...')
    
    desc = '''A Cherrytree notes converter, converting notes from XML to  markdown.
    
    Conversion of 'rich text' to markdown is a not so unambiguously job. 
    For instance, what to do when some text was marked up with monospace font
    and also marked up in italic style?  The choice that I made was to prefer
    monospace markup over all other styles that are present; monospace text will be 
    converted as 'inline code' or as a 'code block' (depending on the presence of
    newlines in the text).  Reason is that I personally choosed many times for
    monospace (just press CTRL-m in Cherrytree) over a codebox, I just found that
    easier to do (regretting my laziness afterwards).

    I have made almost 500 notes in Cherrytree and it was surprising to see that
    many notes did not match the format rules I came up with.  So this converter
    does not deal with all possible situations and I accept to modify some markdown
    notes manually after the conversion.

    Cherrytree exports all images as encoded BASE64 in 'png' file format.
    Images will  be stored together in one 'images' directory whereby each image
    will be suffixed with an unique number.
    But also embedded PDF's are stored like png-files. These will be stored
    into a 'attachments' directory, also with a unique-number.
    '''
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=argparse.RawTextHelpFormatter)
    # group1 = parser.add_mutually_exclusive_group()

    parser.add_argument(
           '-a' , '--absolute_path', action='store_true',
           help= textwrap.dedent('''\
           references inside markdown notes: use absolute path instead
           of relative paths in references to other files like images.
           Default a relative path is generated because that makes it possible 
           to move the generated notes-tree to a other place in the filesystem
           afterwards.
           
           In case you like to browse your notes-tree in a sandwiched environment,
           for example with 'jail', you can opt in for an absolute path.\n\n'''))

    # clean up / remove dirs
    parser.add_argument(
            '-c', '--clean_env', action='store_true',
            help=textwrap.dedent('''\
            clean up the output environment: purge the directory 'notes' from 
            the 'data_dir' directory. You will be prompted for confirmation [y/n].

            -> Be carefull not to run this option after having made changes 
               manually to your newly created markdown notes!\n\n'''))

    # data-dir
    parser.add_argument(
            '-d', '--data_dir', 
            help=textwrap.dedent('''\
            directory for containing the output, will be created if not existing
            already - default: '../data/_ch2md_' .
            
            For security reasons, the data directory is always followed by a 
            system generated directory called _ch2md_\n\n'''))

    # starting number unique attachments index numbers
    parser.add_argument(
            '-x', '--attachment_index', default=1,
            help=textwrap.dedent('''\
            starting number for indexing attachment files; default is 1\n\n'''))

    # quiet
    parser.add_argument(
            '-q', '--quiet', action='store_true',
            help=textwrap.dedent('''\
            no output information on screen but redirect all info to file 
            'stdout.log\n\n'''))

    # unique-id
    parser.add_argument(
            '-u', '--unique_id',
            help=textwrap.dedent('''\
            convert only the note with the specific Cherrynote unique_id (XML-attribute)\n\n'''))

    # verbosity
    parser.add_argument(
            '-v', '--verbosity', action='count', default=0,
            help=textwrap.dedent('''\
            increase output verbosity:
            -v  : show used directory paths and a table with counts
            -vv : show additionally filepaths of created notes and directories\n\n'''))

    # dry-run
    parser.add_argument(
            '-y', '--dryrun', action='store_true',
            help='fake run: disable the creation of any file on disk\n\n')

    # xml-file (positional)
    parser.add_argument(
            'xml_filepath', 
            help=textwrap.dedent('''\
            the path and filename of the Cherrytree XML file to process;
            this can be an absolute or a relative path\n'''))
    return parser.parse_args()


def clean_env():
    v3 and print(f'running: {get_current_function_name()} ...')
    print('\nYou are about to delete the complete tree with generated images '
          'and markdown files located in this directory: \n'
          f'{markdown_dir}\n', file=sys.stderr, flush=True)
    s = read_kbd_input(msg='Do you REALLY want to remove the files? [y/n]',
                       fconvert = str, choices = list('yYnN'))
    print('You answered:', s, file=sys.stderr, flush=True)

    if s.upper() == 'Y':
        shutil.rmtree(markdown_dir, ignore_errors=True)
    else:
        raise Cherry2mdConfigError('Cleanup aborted by user. Program terminated.')
    

def init_config():
    global v1, v2, v3, dry_run ,xml_dir, markdown_dir
    global _data_dir, log_dir, log_filepath, xml_filepath
    global markdown_dir, images_dir, pdf_dir, others_dir, attachment_index
    global clean, _stdout_filepath, quiet, abs_path, unique_id, debug_bigfile

    v3 = bool(os.getenv('CH2MD_VERBOSITY', False))
    v3 and print(f'running: {get_current_function_name()} ...')
    args = parse_arguments()
    debug_bigfile = bool(os.getenv('CH2MD_BIGFILE', False))

    if v3:
        args.verbosity = 2

    match args.verbosity:
        case 0: pass
        case 1: v1 = True
        case _: v1, v2 = True, True

    # init the global vars
    abs_path = args.absolute_path
    quiet = args.quiet
    dry_run = args.dryrun
    unique_id = args.unique_id
    xml_filepath = Path(args.xml_filepath)
    _data_dir = args.data_dir or Path('../data')
    _data_dir = (Path('.').absolute() / _data_dir).resolve()
    attachment_index = int(args.attachment_index)
    # to secure the users data in case of use of the clean_env option:
    _data_dir = _data_dir / '_ch2md_'
    xml_dir = _data_dir / 'xml'
    markdown_dir = _data_dir / 'markdown'
    images_dir = markdown_dir / prefs.get('filepaths').get('images_link')
    pdf_dir = markdown_dir / prefs.get('filepaths').get('pdf_link')
    others_dir = markdown_dir / prefs.get('filepaths').get('others_link')
    # logging
    log_dir = _data_dir / 'log'
    _stdout_filepath = log_dir / 'stdout.log'

    if args.clean_env:
        clean_env()

    if not (xml_filepath.exists() and xml_filepath.is_file()):
        raise Cherry2mdConfigError(
                f'file \'{xml_filepath}\' does not exist or is not a regular file')

    #  create config directories if necessary
    autocreate = [('data directory', _data_dir),
                  ('markdown directory', markdown_dir),
                  ('attachments images directory', images_dir),
                  ('attachments pdf directory', pdf_dir),
                  ('attachments others directory', others_dir),
                  ('log directory', log_dir)]

    for desc, dir in autocreate:
        if dir.exists():
            # do nothing if dir already exists 
            if not dir.is_dir():
               # but it should be a real directory
               raise Cherry2mdConfigError(
                    f'{desc}: {dir} --> exists but not a directory!')
        else:
            # dir does not exist, create it
            v2 and print(f'creating {desc} : {dir}')
            if not dry_run:
                dir.mkdir(parents=True)

    # determine the name of the new log-file, max 30 files

    max_log_files = 2  # TODO: change into 30

    i = 0
    while True:
        i += 1
        log_filepath = log_dir / f'ch2md-{i:03}.log'
        if log_filepath.exists():
            v3 and print(f'logfile {log_path} already exists')
            if i == max_log_files:
                raise Cherry2mdConfigError(
                        f'Error: maximum number of {max_log_files} logfiles '
                         'has been reached\n'
                         'please, first cleanup your log directory')
        else:
            v3 and print(f'log path: {log_filepath}')
            break

