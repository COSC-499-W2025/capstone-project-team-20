import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import GraphPrint

def test_graph_incorrect_format_abort():
    '''All of these should return -1'''
    #list where a name doesnt have a corresponding value:
    errlist = [['Python'],['Java', 6904]]
    assert GraphPrint.graph('',errlist,'') == -1

    #list where values are the wrong type:
    errlist = [[1830, 'Python'],['Java', 6904]]
    assert GraphPrint.graph('',errlist,'') == -1

    #list that is not nested:
    errlist = ['Python', 1830,'Java', 6904]
    assert GraphPrint.graph('',errlist,'') == -1

    #list where extra values are given:
    errlist = [['Python', 1830],['Java', 6904, 7]]
    assert GraphPrint.graph('',errlist,'') == -1

def test_fillprint_incorrect_fill_character_abort():
    '''Should return -1 in the case that a fill character is more than 1 character or is no character'''
    #fill character is blank:
    errchar = ''
    assert GraphPrint.fillprint('',10,errchar) == -1

    #fill character is more than 1 character:
    errchar = '01'
    assert GraphPrint.fillprint('',10,errchar) == -1

def test_fillprint_incorrect_fill_length_abort():
    '''Should return -1 in the case the length of fill is negative or 0'''
    #fill length is zero:
    errlen = 0
    assert GraphPrint.fillprint('',errlen,' ') == -1

    #fill length is negative:
    errlen = -94
    assert GraphPrint.fillprint('',errlen,' ') == -1