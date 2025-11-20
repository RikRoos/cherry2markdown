# exporter.py
# TODO: make markdown-note with conversion results in the root of the tree

import config as c
import cherry2mdlib.utils as utils
from cherry2mdlib.notes import Note
import xml.etree.ElementTree as ET
        


def get_xmlroot(filepath_xml):
    # open the xml-file and get the root-node
    with open(filepath_xml) as xml:
        tree = ET.parse(xml)
    return tree.getroot()


def start_parser(xml_file):
    '''The parsing of the xml-file starts here.

    This function traverses the XML-file, searching for <node> tags.

    Returning: a dictionary with all created notes, keys are the found
               unique id's from cherrynote attribute [unique_id].
    '''
    c.v3 and print(f'running: {utils.get_current_function_name()} ...')
    xml_root = get_xmlroot(xml_file)
    start_path = c.markdown_dir
    prefix = 0
    for child in xml_root:
        if child.tag != 'node':
            continue
        prefix += 1
        parse_node(child, start_path, prefix)
    write_notes()
    if c.debug_bigfile:
        create_one_big_file()
    
    
def parse_node(node, dir_path, prefix):
    '''This function parses the selected tag, searching for <node> tags
    or other supported tags.

    If this node contains other <node> tags, then this node will become the
    the initiator of a new directory with it's name based on this node's name.

    In case this node also has some text in it, this text will become the first
    note in the new directory with a name starting with '000-<name of node>'.
    '''
    c.v3 and print(f'running: {utils.get_current_function_name()} ...')
    c.v3 and print(f'node ID: {node.attrib.get('unique_id')}')

    if node.find('node') is not None:
        # Child-nodes were found inside this node
        # Create a seperate note for this parent-node in a extra level deep
        #  directory named after this node
        note = make_note(node,
                         dir_path=dir_path,
                         file_prefix=0)
        # note.dir_path = note.dir_path / f'{prefix:03d}-{note.basename}'
        note.dir_path = note.dir_path / f'{prefix}. {note.basename}'
        new_node_prefix = 0
        for child in node.findall('node'):
            # do recursive call
            # new_node_prefix += 5
            new_node_prefix += 1
            parse_node(node=child, 
                       dir_path= note.dir_path,
                       prefix=new_node_prefix,)
        # now add to the notes-list
        Note.all_notes[note.unique_id] = note
    elif (not c.unique_id
          or
          node.attrib.get('unique_id') == c.unique_id
         ):
          # this is just a note without any child-notes
            note = make_note(node,
                             dir_path=dir_path,
                             file_prefix=prefix)
            # now add to the notes-list
            c.v3 and print(f'adding note to all_notes: {note} ...')
            Note.all_notes[note.unique_id] = note


def make_note(node, dir_path, file_prefix):

    unique_id = node.attrib.get('unique_id')
    c.v3 and print(f'running: {utils.get_current_function_name()} ... for ID: {unique_id}')
    note = Note(tag=node.tag,
                name=node.attrib.get('name', ''),
                dir_path=dir_path,
                file_prefix=file_prefix,
                unique_id=unique_id,
                prog_lang=node.attrib.get('prog_lang'),
                timestamp=int(node.attrib.get('ts_creation')))

    # test the commandline option 'unique_id'.

    if (not c.unique_id
        or node.attrib.get('unique_id') == c.unique_id
       ):
        # Get the textual data, codebox, tables or images for a note.
        for child in node:
            if child.tag != 'node':
                attribs = interesting_attribs(child)
                attribs['unique_id'] = note.unique_id
                if child.tag in ('rich_text', 'codebox', 'table', 'encoded_png'):
                    c.v3 and print(f'child.tag: {child.tag}')
                    c.v3 and print(f'child.text: {child.text}')
                    note.add_tag(child, child.tag, child.text, attribs)
                else:
                    # until today this never happen
                    Note.update_counter(f'not-supported:{child.tag}')
                    print(f'Warning: for node {note.unique_id} an unknown TAG was found: {child.tag}')
    return note


def interesting_attribs(node):
    '''Just collect only XML-attributes with which we have to deal.

    We could skip this step because attribute values are tested explicitly but
    I like it this way (filtering out what we don't need).
    '''
    interested = {'link', 'scale', 'family', 'style', 'weight', 'char_offset',
                  'strikethrough', 'syntax_highlighting', 'unique_id', 
                  'ts_creation', 'foreground', 'filename'}
    attribs = {}
    for k in set(node.attrib) & interested:
        attribs[k] = node.attrib[k]
    return attribs


def write_notes():
    '''Process only notes with some content otherwise only empty directories are
    created and we do not like the latter.

    Notes can only be formatted after initializing all other notes. This is
    because of the internal node references: we do not know the fully 
    qualified filepaths of other notes on forehand.
    '''
    c.v3 and print(f'running: {utils.get_current_function_name()} ...')
    # for note in [note for note in Note.all_notes.values() if note.xml_data]:
    for note in [note for note in Note.all_notes.values() if note.xml_data or note.offsets]:
        c.v2 and print(f'creating note (id:{note.unique_id:>4}): '
                       f'{note.dir_path / note.file_name}')

        # create a dir to contain this note
        if note.dir_path.exists():
            if not note.dir_path.is_dir():
                raise Exception(f'Not a directory: {note.dir_path}')
        else:
            c.v2 and print(f'creating dir: {note.dir_path}')
            if not c.dry_run:
                note.dir_path.mkdir(parents=True)
            Note.update_counter('dirs-created')
        # get the markdown-note and write it to a file
        # notetext = note.get_text()
        if not c.dry_run:
            # (note.dir_path / note.file_name).write_text(text)
            text = note.get_top_text() + note.text + note.get_bottom_text()
            (note.dir_path / note.file_name).write_text(text)
        Note.update_counter('notes-written')


def create_one_big_file():
    '''For debugging - create one big file with all notes.
    
    You can run easily a "diff" on files this way.
    Activation: $ export CH2MD_BIGFILE=1
    '''
    c.v3 and print(f'running: {utils.get_current_function_name()} ...')

    with open(c.log_dir / 'all_notes.txt', 'w') as fh:
        for note in Note.all_notes.values():
            if not note.text:
                continue
            c.v3 and print(f'[new note: {note.unique_id}]')
            fh.write(f'\n======[new note: {note.unique_id}]======\n')
            fh.write(note.text)
            # for line in [txt[1] for txt in note.formatted]:
                # fh.write(line)
