import base64
import datetime
import xml.etree.ElementTree as ET
import sys

class Cherry2mdException(Exception):
    pass

class Cherry2mdConfigError(Cherry2mdException):
    pass

class Cherry2mdConversionError(Cherry2mdException):  # TODO: assign unique_id
    pass
    

class StdOutToFile:
    ''' Redirect _optionally_ the standard-out to a file.'''
    def __init__(self, fname: str, redirect: bool):
        self._fname = fname
        self._current_stdout = sys.stdout
        self._redirect = redirect
        
    def __enter__(self):
        if self._redirect:
            self._file = open(self._fname, 'w')
            sys.stdout = self._file
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        if self._redirect:
            sys.stdout = self._current_stdout
            if self._file:
                self._file.close()
        return False

def makefile_decode_base64(str_b64, filepath):
    binstr = base64.b64decode(str_b64)
    with open(filepath, 'wb') as png_file:
        png_file.write(binstr)

def get_decoded_base64(str_b64: str) -> str:
    binstr = base64.b64decode(str_b64)
    return binstr.decode()

def current_date_as_str(UTC=True, ISO=False, fmt='%d-%m-%YT%H:%M:%S', fmt_offset=True):
    if UTC:
        dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
    else:
        dt = datetime.datetime.now()
        
    if ISO:
        res = dt.isoformat()
    else:
        if fmt_offset:
            fmt += ' %z'
        res = dt.strftime(fmt)
    return res

def get_current_function_name():
    '''Return the current function name.

    Implementation is supported by CPYTHON.
    '''
    return sys._getframe(1).f_code.co_name    
    
def xmltable_to_markdown(xml_element):
    ''' Strange fact: the header-row is always the last row.'''

    table = []
    row = []

    # Read the xml-table and convert it to a 2-dim list
    xmltable = [el for el in list(xml_element.iter())]
    for el in xmltable[1:]:  # skip "table"-tag
        if el.tag == 'row':
            if row:
                table.append(row)
            row = []
        else:
            # dealing with column-values
            el.text = el.text and el.text.replace('>','⩼') # \u2a7c
            row.append(el.text if el.text else '·')

    # last fetched row is the header row, insert as 1st row
    table.insert(0, row)

    # find max length of all values of each column
    cols = len(table[0])
    col_lengths = []
    for i in range(0, cols):
        max_col_len = max([len(r[i]) if r[i] else 0 for r in table[1:]])
        col_lengths.append(max_col_len)

    # make each colum-value width equal to the max length of that column population
    for r in table:
        for i, c in enumerate(r):
            r[i] = f'{c:{col_lengths[i]}}'
            # print(f'{i=} : {col_lengths[i]=} : {c=} : *{r[i]=}*')

    # 2nd row: generate horizontal row as divider
    row = []
    for len_ in col_lengths:
        row.append('-' * len_)
    table.insert(1, row)

    # now add vertical dividers between the columns and a newline at end
    for r in table:
        for i in range(cols-1, 0, -1):
            r.insert(i, '|')
        r.append('\n')

    # to create a text-string the 2-dim array must be flattened
    flatten =  [c if c else '' for r in table for c in r]
    return ''.join(flatten)


def read_kbd_input(msg:str , fconvert: callable, choices: list = None, max_try:int = 3):

    tempStdOut = sys.stdout
    sys.stdout = sys.__stderr__
    max_try = 1 if max_try < 0 else max_try
    try_ = 0
    try:
        while True:
            try_ += 1
            answer = input(msg)
            try:
                answer = fconvert(answer)
                if choices and not answer in choices:
                    raise ValueError
                return answer
            except ValueError:
                if try_ >= max_try:
                    raise Cherry2mdException('Wrong input.')
                print('Wrong input. Try again', flush=True)
    finally:
        sys.stdout = tempStdOut
