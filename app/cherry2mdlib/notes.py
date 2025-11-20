from collections import namedtuple
from pathlib import Path
import datetime
import re
import string
import sys
import textwrap
import urllib.parse

import config as c
import cherry2mdlib.utils as utils

XMLData = namedtuple('XMLData', 'tag data attr')

class Note():
    '''
    For each fetched <node>-tag an instance of the Note class is created.

    All  useful textual material is collected in the list xml_data.
    The class provides staticmethods to format data read from the input
    XML file.

    The following tranformation services are provided:
      - convert a codebox into markdown code-block
      - convert headers (scale attribute h1 .. h6) into markdown headers 
        (# ..## .. ### etc);
        headers do not undergo successive formatting
      - convert Links (link attribute) into markdown links;
        links do not undergo successive formatting
      - convert monospace text (family attribute) into markdown code-block
      - convert lists (scanned on linefeed followed by a list-symbol) into
        markdown list items (using the dash "-")
      - convert styles heavy, italic, striketrough, super-script and sub-script
        into corresponding markdown notations (**, _, ~~, <sup> and <sub> .

        Markdown does not support underlining notation.
    '''

    all_notes = {}
    counters = {}
        
    def __init__(self, tag: str, name: str, dir_path: Path, 
                 file_prefix: int, unique_id: str, prog_lang: str, timestamp: int):
        self.tag = tag
        self.name = name
        self.file_prefix = file_prefix
        self.dir_path = dir_path # our dir path contains never bad chars
        self.prog_lang = prog_lang
        self.basename, self.file_name = Note.setup_filepaths(self.name, 
                                                             self.file_prefix)
        self.unique_id = unique_id
        self.xml_data = []
        self.offsets = []
        self.formatted = []         # contains formatted data
        self._text = None           # contains markdown-text to be exported

        self.fmtvars = {}   # dict used for substitutes in TOML-config file
        self.fmtvars['parent_title'] = self.dir_path.parts[-1]
        self.fmtvars['title'] = self.name
        self.fmtvars['unique_id'] = self.unique_id
        self.fmtvars['timestamp_exported'] = \
            utils.current_date_as_str(fmt=c.prefs['note']['fmt_timestamp_exported'],
                                      fmt_offset=False).strip()
        self.fmtvars['timestamp_created'] = \
            datetime.datetime.fromtimestamp(timestamp)\
              .strftime(c.prefs['note']['fmt_timestamp_created']).strip()
        self.update_counter('notes-initialized')

    @classmethod
    def update_counter(cls, tag, incr=1):
        '''Counters for reporting purposes.
        
        In case of the processing of images, a counter is used to create
        the suffix for each image file name.
        '''
        cls.counters[tag] = cls.counters.get(tag, 0) + incr

    @staticmethod
    def setup_filepaths(note_title, file_prefix):
        '''A note title in Cherrynote can be any kind of text.

        To use the title as the filename for the note, we must cleanse the
        title by stripping the unwanted chars.
        Maybe this can be done in one fancy regex but must hurry now...
        '''
        # replacing spaces with dashes - hate spaces in filenames
        goodchars = string.ascii_letters + string.digits + '-'
        badname = note_title
        badname = badname.replace(' ','-')
        badname = [c for c in badname if c in goodchars]
        # now replace successive dashed
        goodname = re.sub(r"(-)\1+", r"\1", ''.join(badname))
        basename = goodname
        # file_name = f'{file_prefix:03d}-{basename}.md'
        file_name = f'{file_prefix}. {basename}.md'
        return basename, file_name

    def add_tag(self, element, tag, data, attr):
        '''Populate the list 'xml_data' with raw XML-data.

        Encoded image-data are converted instantly to image-files to 
        prevend that memory becomes exhausted.
        But beware, the XML claims that everything is a encoded png, not true!

        Also pdf, ipynb and even csv is in the XML tagged as encoded_png.
        Difference is that the non-png also have a attribute "filename", this
        type must handled differently.
        '''
        c.v3 and print(f'running: {utils.get_current_function_name()} ...')
        c.v3 and print(f'tag: {tag}')
        if not data:
            c.v3 and print('no data in tag')
            return

        Note.update_counter(tag)
        
        if tag == 'encoded_png':
            dir = None
            link = None
            offset = int(attr['char_offset'])
            fname = attr.get('filename')
            excl_mark = '!'
            if fname:
                # e.g. a PDF, CSV or YPYNB
                self.update_counter('attachments')
                c.v2 and print(f'encoded_png: found attachment {fname} (uid:{self.unique_id})')
                if Path(fname).suffix == '.pdf':
                    dir = c.pdf_dir
                    link = c.prefs.get('filepaths').get('pdf_link')
                else:
                    dir = c.others_dir
                    link = c.prefs.get('filepaths').get('others_link')
                fname = f'{self.file_prefix:03d}-{c.attachment_index:04d}-{fname}'
                excl_mark = ''
            else:
                # a PNG image
                self.update_counter('png-image')
                c.v2 and print(f'encoded_png: found png (uid:{self.unique_id})')
                dir = c.images_dir
                link = c.prefs.get('filepaths').get('images_link')
                fname = f'{self.file_prefix:03d}-{c.attachment_index:04d}-{self.basename}.png'
                
            filepath = dir / fname
            # link = urllib.parse.quote(str(Path(link) / fname))
            link = str(Path(link) / fname).replace(' ', '%20')
            # link = str(Path(link) / fname)
            link = f'{excl_mark}[{fname}]({link})'
            self.offsets.append(XMLData(tag, link, {'char_offset' : offset}))
            if not c.dry_run:
                utils.makefile_decode_base64(data, filepath)
            self.update_counter('resources-created (*.png *.pdf etc)')
            c.attachment_index += 1

        elif tag == 'codebox':
            c.v3 and print('dealing with codebox')
            offset = int(attr['char_offset'])
            text = Note.format_codebox(data, attr)
            c.v3 and print(f'returning: {text}')
            self.offsets.append(XMLData(tag, text, {'char_offset' : offset}))

        elif tag == 'table':
            offset = int(attr['char_offset'])
            text = utils.xmltable_to_markdown(element)
            self.offsets.append(XMLData(tag, text, {'char_offset' : offset}))

        elif tag == 'rich_text':
            self.xml_data.append(XMLData(tag, data, attr))

        self.update_counter('tags-processed')

    @staticmethod
    def format_codebox(text, attr, lang=None):
        '''Returns a codeblock labeled with the language or just 'text'.'''
        maplang = {'python3' : 'python'}
        if not lang:
            lang = attr.get('syntax_highlighting', 'text')
        return f'\n``` {maplang.get(lang, lang)}\n{text}\n```\n'
        
    
    def insert_objects_at_offset(self, xml_specials):

        # Difficulty to overwin:
        
        # Merge into xml_data the specials tags which have char-offsets  
        # at the correct indices.

        # Insert tags with their offset into the stack of xml_data at the right
        # index. This asks for summing up characters until the offset is reached.
        
        if xml_specials:
            # xml_specials: images, tables, codeboxes

            idx = 0
            offset = 0

            # vars dedicated to 'xml_specials'
            sp_itr = iter(xml_specials)
            sp_tag, sp_data, sp_attribs = next(sp_itr)
            sp_offset = int(sp_attribs['char_offset'])

            for tlen in [len(xmld.data) for xmld in self.xml_data]:
                # print(f'start={offset} / end={offset + tlen -1}, {sp_offset=}')
                # print(f'start={offset_s} / end={offset_s + tlen -1}, {text=}')
                while offset <= sp_offset <= (offset + tlen -1):
                        # the xml-tag (e.g. image) fits here
                        # print(f'1. inserting image {sp_data}')
                        self.xml_data.insert(idx, XMLData(sp_tag, sp_data, sp_attribs))
                        sp_data = None
                        idx += 1
                        try:
                            sp_tag, sp_data, sp_attribs = next(sp_itr)
                            sp_offset = sp_attribs['char_offset']
                        except StopIteration:
                            # print('1. stop iteration')
                            break
                else:
                    offset += tlen
                    idx += 1
                    continue

                break

            if sp_data:
                # print(f'2. inserting image {sp_data}')
                self.xml_data.insert(idx, XMLData(sp_tag, sp_data, sp_attribs))
                idx += 1
                while True:
                    try:
                        sp_tag, sp_data, sp_attribs = next(sp_itr)
                        sp_offset = sp_attribs['char_offset']
                        # print(f'3. inserting image {sp_data}')
                        self.xml_data.insert(idx, XMLData(sp_tag, sp_data, sp_attribs))
                        idx += 1
                    except StopIteration:
                        # print('2. stop iteration')
                        break

    def formatter(self):
        ''' The following object need to be formatted:
            - codeboxes, completely embed text between ```...```
            - lang-nodes, completely embed text between ```...```
              these nodes never have other tags inside themselves
            - headers, prefix with # ## ### #### ##### ######
            - webs link, link to website
              file link, link to a local file
              node link, link to other node, maybe acting like file link? # TODO: check this
              fold link, link to folder  : we ignore those
            - style attribute        : italic
            - weight attribute       : heavy
            - strikethrough attribute: true/false
        '''
        c.v3 and print(f'running: {utils.get_current_function_name()} ...')
        
        # Merge into xml_data the specials tags which have char-offsets  
        # at the correct indices.
        self.insert_objects_at_offset(self.offsets)

        # At this point the list is complete and has text-fragments coming
        # from xml-tags with an offset property on the right place.
        # Now all these raw text-fragments can be formatted to markdown.

        if self.tag == 'node' and self.prog_lang != 'custom-colors':
            # This node tag will have one and only one rich_text-tag, no other 
            # childs shall exist.
            _, text, attr = self.xml_data[0]  
            text = Note.format_codebox(text, attr, self.prog_lang)
            self.formatted.append(('NODE-PROGLANG', text))
        else:
            remark = None
            for idx, xml_record in enumerate(self.xml_data):
                tag, text, attr = xml_record

                c.v3 and print('-' * 30)
                c.v3 and print(f'{tag=} :: {attr=}')
                c.v3 and print(f'raw      :>>{text}<<')

                if not text.strip():
                    self.formatted.append(('EMPTY',text))
                    continue

                if tag in ('encoded_png', 'table', 'codebox'):
                    # do not modify text-objects of these tags
                    remark = tag.upper()
                    
                elif attr.get('scale', '').startswith('h'):
                    # Dealing with a header
                    remark = 'HEADER'
                    text = Note.format_header(text, attr)

                elif attr.get('link', ''):
                    # Dealing with links
                    # This part does also images because an image is just like
                    # a link-text.
                    remark = 'LINK'
                    text = Note.format_link(text, attr)

                elif attr.get('family', '') == 'monospace':
                    # monospaced text must be paired by MS-tags
                    remark = 'MONOSPACE'
                    if (scale := attr.get('scale')) in ('sup', 'sub'):
                        text = Note.supsub_script(text, scale)
                    text = Note.sandwich(text, '<MS>','</MS>', excl_spaces=False)

                else:
                    # no special tags, check for style formats
                    # replace styles with: _ ** *** ~~
                    remark = 'DEFAULT'

                    if (scale := attr.get('scale')) in ('sup', 'sub'):
                        text = Note.supsub_script(text, scale)

                    # 4 leading spaces has a special meaning to markdown, replace this by 3
                    text = re.sub('^( ){4,}', ' '*3, text)
                    text = re.sub('\n( ){4,}', '\n   ', text)

                    # hard linefeed needs two consecutive spaces
                    # text = re.sub(r'(\S)\s{0,2}\n', r'\1  \n', text)   # TODO: was buggy, stripped also accidently leading spaces! 
                    text = Note.format_styles(text, attr)
                
                    # now dealing with lists inside the text
                    # TODO: commandline optie aftesten
                    if '\n• ' in text:
                        text = text.replace('\n• ', '\n- ')
                    if '\n☐ ' in text:
                        text = text.replace('\n☐ ', '\n- ')

                c.v3 and print(f'formatted:>>{text}<<\n')
                self.formatted.append((remark,text))


    @staticmethod
    def format_header(text, attr):
        prefix = ''
        hdr = attr.get('scale')
        if hdr in [f'h{n}' for n in range(1,7)]:
            text = f'{int(hdr[1]) * '#'} {text}'
        else:
            # print(f'cannot determine type of heading for node-id: {attribs.get('unique_id')} value: {value}  {value[1]} {len(value)}')
            # TODO: make this an exception without fatal errr
            pass
        return text


    @staticmethod
    def format_link(text, attr):
        fields = attr.get('link', '').split()
        linktype = fields[0]
        if linktype == 'fold':
            Note.update_counter('folder-link-ignored')
            pass

        elif linktype in ('webs', 'file'):
            link = fields[1]
            if fields[0] == 'webs':
                Note.update_counter('web-link')
                if text == link and len(text) > 30:
                    max_ = c.prefs['note']['missing_linklabel']['max_chars']
                    if len(text) > max_:
                        shortened = c.prefs['note']['missing_linklabel']['shortened_text']
                        text = text[:max_] + shortened
                c.v2 and print(f'LINK - found web link: {text}')
            elif fields[0] == 'file':
                Note.update_counter('file-link')
                link = utils.get_decoded_base64(str_b64=link)
                c.v2 and print(f'LINK - found file URL: {link}')
                ##
            text = f'[{text}]({link})'

        elif linktype == 'node':
            # Reference to another note, treath as a file link
            Note.update_counter('internal-node-link')
            uid = fields[1]
            ref_note = Note.all_notes.get(uid)
            if ref_note:
                link = str(ref_note.dir_path / ref_note.file_name)
                text = f'[{link}]({link})'
                c.v2 and print(f'LINK - found internal link: {link}')
                Note.update_counter('internal-link-solved')
            else:
                print(f'Error: replacing internal links -> ref note-id '
                      f'note with id {uid} was not found.')
                text = f'_reference to other note with ID {uid} not found._'
        else:
            print(f'Error: unknown link-type: {value.split()[0]}')
            # TODO: make this an exception without fatal errr
        return text

    @staticmethod
    def sandwich(text, prefix, suffix, excl_spaces=True):
        '''
        Markup like italic and bold cannot be used with spaces around the
        subject text.
        '''
        if excl_spaces:
            return re.sub(r'^( *)(.+?)( *)$', 
                          rf'\1{prefix}\2{suffix}\3', 
                          text, flags=re.DOTALL)
        else:
            return re.sub(r'^( *)(.+?)( *)$', 
                          rf'{prefix}\1\2\3{suffix}', 
                          text, flags=re.DOTALL)

    @staticmethod
    def supsub_script(text, style):
        Note.update_counter(f'format:{style}')
        try:
            d = c.prefs['markup'][f'{style}script']
            if d['method'] == 'tag':
                s = d['tag']
                text = Note.sandwich(text, f'<{s}>', f'</{s}>')
            elif d['method'] == 'translate':
                normal = d['normal']
                target = d['target']
                mapping = text.maketrans(''.join(normal), ''.join(target)) 
                text = text.translate(mapping) 
        except KeyError as ex:
            print(f' cannot find keys for {style}-script in TOML config: {ex}', file=sys.stderr)
            text = Note.sandwich(text, f'<{style}>', f'</{style}>')
        return text

    @staticmethod
    def pre_or_sufix(text, expr, table, key, default):
        '''Sandwich a string between a prefix and a suffix.'''
        if expr:
            Note.update_counter(f'format:{key}')
            try:
                s = c.prefs[table].get(key, default)
            except KeyError as ex:
                s = default
                print(f'Error: segment \'{segment}\' not found in TOML config', file=sys.stderr)
            return Note.sandwich(text, s, s)
        else:
            return text

    @staticmethod
    def format_styles(text, attr):
        prefix, suffix = '', ''
        scale = attr.get('scale')
        style = attr.get('style')
        weight = attr.get('weight')
        strikethrough = attr.get('strikethrough')
        family = attr.get('family')
        foreground = attr.get('foreground')

        # in python some words are like __dunder__, should become inline code
        text = re.sub(r'\s(__\w+__)\s', r'`\1`', text)  # TODO: this works?
        
        if foreground and not style and not family:
            Note.update_counter(f'format:foreground(!)')
            style = 'italic'
        text = Note.pre_or_sufix(text, style=='italic', 'markup', 'italic', '_')
        text = Note.pre_or_sufix(text, weight=='heavy', 'markup', 'heavy', '**')
        # # text = Note.presufix_2(text, style=='italic' and not weight=='heavy', 'italic', '_')
        # # text = Note.presufix_2(text, not style=='italic' and weight=='heavy', 'heavy', '**')
        # # text = Note.presufix(text, style=='italic' and weight=='heavy', '***','***')
        text = Note.pre_or_sufix(text, strikethrough=='true', 'markup', 'strikethrough', '~~')
        return text


    def get_top_text(self):
        '''
        The very last step in the export is the adding of an optional text to
        top of the note.
        '''
        text = ''
        if c.prefs['note']['title']['print']:
            text = c.prefs['note']['title']['text'].format(**self.fmtvars)
            text = textwrap.dedent(text)
        return text
            

    def get_bottom_text(self):
        '''
        The very last step in the export is the adding of an optional text to
        bottom of the note.
        '''
        text = ''
        if c.prefs['note']['closing']['print']:
            text = c.prefs['note']['closing']['text'].format(**self.fmtvars)
            text = '\n\n' + textwrap.dedent(text)
        return text


    @property
    def text(self):
        '''Creates the markdown text.'''
        c.v3 and print(f'running: {utils.get_current_function_name()} ...')
        c.v3 and print(f'self._text: \n{self._text}')
        c.v3 and print(f'self.xml_data: \n{self.xml_data}')

        if self._text is None:
            if not self.xml_data and not self.offsets:
                c.v3 and print('no xml_data and offsets')
                self._text = ''
            else:
                self._text = self._get_text()
        return self._text

        
    def _get_text(self):

        c.v3 and print(f'running: {utils.get_current_function_name()} ...')
        self.formatter()
        text = ''.join([txt[1] for txt in self.formatted])

        if c.v3:
            print('-'*30)
            print(f'>>>text after formatter:\n\n{text}')

        # beautify the monospace-tag structure in the text

        # remove leading spaces
        text = re.sub('^ *<MS>', '<MS>', text)
        text = re.sub('^ *</MS>', '</MS>', text)

        # remove trailing spaces
        text = re.sub('<MS> *$', '<MS>', text)
        text = re.sub('</MS> *$', '</MS>', text)

        # start-monospace tag never at line ending
        text = re.sub('<MS>\n', '\n<MS>', text)

        # ending-monospace tag never at line begin
        text = re.sub('\n</MS>', '</MS>', text)

        # remove empty monospace tags
        text = re.sub('<MS> *?</MS>', '', text)

        # remove ending-tag preceeding starting tag, these are not nessecarry
        # and even disturb the reformatting
        text = re.sub('</MS> *?\n *?<MS>', '\n', text)
        text = re.sub('</MS> *?<MS>', '', text)

        # print('-'*30)
        # print(text)

        # Processing <MONOSPACE> tags:
       
        # there is one monospace tag pair using the entire line
        # replace this pair with an inline-code tag
        #
        # source: <MS> aaa bbb </MS>
        #
        # target: ``` aaa bbb```

        # text = re.sub(r'^ *<MS>(((?!<MS>).)+)</MS> *$',
        #               r'```\1```\n', 
        #               text, flags=re.MULTILINE)
        text = re.sub(r'^ *<MS>(((?!<MS>).)+)</MS> *$',
                      r'```\1```\n', 
                      text, flags=re.MULTILINE)

                # text = re.sub(r'^( *)(.+?)( *)$', 
                #               rf'\1{prefix}\2{suffix}\3', 
                #               text, flags=re.DOTALL)

        # print('1.', '-'*30)
        # print(text)

        # there is only one monospace tag pair using the entire line
        # replace this with a code block
        #
        # source: <MS> aa \n 
        #              bb \n 
        #              cc </MS>
        #
        # target: ``` python
        #         aa 
        #         bb 
        #         cc
        #         ```

        text = re.sub(r'^ *<MS>(((?!<MS>).)+)</MS> *$', r'\n``` python\n\1\n```', text, flags=re.MULTILINE | re.DOTALL)

        # print('2.', '-'*30)
        # print(text)
        # there one or more monospace tag pairs with leading or trailing text
        # replace these pair with bold and keep also the other text
        #
        # source: aaa <MS> bbb </MS> ccc <MS> dddd </MS> eee
        #
        # target: aaa **bbb** ccc **dddd** eee

        text = re.sub(r'<MS>(.+?)</MS>', r'**\1**', text, flags=re.MULTILINE | re.DOTALL)

        if c.v3:
            print('-'*30)
            print(f'>>>text after regex-substitutions:\n\n{text}')

        # hard linefeed needs two consecutive spaces
        if (end := c.prefs['note']['linebreak']['append_each_line']):
            text = re.sub(r'^(.*)$', rf'\1{end}', text, flags=re.MULTILINE)
            if c.v3:
                print('-'*30)
                print(f'>>>text after adding 2 spaces each line:\n\n{text}')

        if c.prefs['note']['linebreak']['replace_empty_line_with']:
            text = re.sub(r'^( *)$', r'\\', text, flags=re.MULTILINE)
            if c.v3:
                print('-'*30)
                print(f'>>>text after replacing empty lines:\n\n{text}')
                
        return text.lstrip()

    def __str__(self):
        return (f'Note: "{self.name}", ID: "{self.unique_id}", '
                f'#datacells: {len(self.xml_data)}')

