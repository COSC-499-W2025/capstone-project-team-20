import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ProgressBar import Bar

def test_too_small_abort():
    '''Bars created with 7 or less bytes (including negative numbers) should abort (create an already completed bar where STAGES is 1)'''

    #we will test this with values -1, 0, 1, 7
    bytes_to_test = [-1,0,1,7]
    for n in bytes_to_test:
        testbar = Bar(n)
        #Check the bar will display as: |█| (n Bytes/n Bytes)
        assert testbar.bDone == '█'
        assert testbar.bLeft == ''
        assert testbar.sSub == 8
        assert testbar.TOTALB == n
        assert testbar.total == n

        #Check that the bar is incomplete
        assert testbar.sDone == 1
        assert testbar.sLeft == 0

def test_bars_have_correct_length():
    '''Bars created with bytes in the range [8-15] should create a bar of length 1'''
    #we will test this with values 8,15
    bytes_to_test = [8,15]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == ''
        assert testbar.sLeft == 1
        assert testbar.STAGES == 1

    '''Bars created with bytes in the range [16-31] should create a bar of length 2'''
    #we will test this with values 16,31
    bytes_to_test = [16,31]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == ' '
        assert testbar.sLeft == 2
        assert testbar.STAGES == 2

    '''Bars created with bytes in the range [32-63] should create a bar of length 4'''
    #we will test this with values 32,63
    bytes_to_test = [32,63]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == '   '
        assert testbar.sLeft == 4
        assert testbar.STAGES == 4

    '''Bars created with bytes in the range [64-127] should create a bar of length 8'''
    #we will test this with values 64,127
    bytes_to_test = [64,127]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == '       '
        assert testbar.sLeft == 8
        assert testbar.STAGES == 8

    '''Bars created with bytes in the range [128-255] should create a bar of length 16'''
    #we will test this with values 128-255
    bytes_to_test = [128,255]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == '               '
        assert testbar.sLeft == 16
        assert testbar.STAGES == 16

    '''Bars created with bytes in the range [256-511] should create a bar of length 32'''
    #we will test this with values 256,511
    bytes_to_test = [256,511]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == '                               '
        assert testbar.sLeft == 32
        assert testbar.STAGES == 32

    '''Bars created with 512 or more bytes should create a bar of length 64'''
    #we will test this with values 512, 9999999
    bytes_to_test = [512,9999999]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTALB == n
        assert testbar.sDone == 0
        assert testbar.sSub == 0
        assert testbar.bDone == ''
        assert testbar.total == 0

        #check variables that will change between sizes
        assert testbar.bLeft == '                                                               '
        assert testbar.sLeft == 64
        assert testbar.STAGES == 64

def test_update_overflow():
    '''Updating a bar with more bytes than remain in the bar should result in a completed bar with correct values i.e (x bytes/x bytes)'''
    testbar = Bar(8)
    testbar.update(16)
    assert testbar.total == 8
    assert testbar.bDone == '█'
    assert testbar.sSub == 8
    assert testbar.bLeft == ''

def test_negative_update():
    '''Updating a bar with negative values should not impact the current progress'''
    testbar = Bar(8)

    #test after update, then test same changes after subtracting -1
    testbar.update(1)
    assert testbar.BSUB[testbar.sSub] == '▏'
    assert testbar.total==1
    testbar.update(-1)
    assert testbar.BSUB[testbar.sSub] == '▏'
    assert testbar.total==1


def test_update_completed_bar():
    '''Updating a bar which is already complete should not impact the progress'''
    testbar = Bar(8)

    testbar.update(8)
    assert testbar.BSUB[testbar.sSub] == ''
    assert testbar.bDone == '█'
    assert testbar.total==8

    testbar.update(35783849)
    assert testbar.BSUB[testbar.sSub] == ''
    assert testbar.bDone == '█'
    assert testbar.total==8

def test_auto_complete():
    '''Bars not evenly divisible into stages will auto complete (adding the remainder) when the visual progress completes'''
    testbar = Bar(9)

    #update 8 so 1 remaining until complete
    testbar.update(8)

    #should auto complete to be at 9
    assert testbar.total == 9

def test_substage_cycle():
    '''Test that substages are correctly cycled through producing the correct string at each point'''
    testbar = Bar(8)

    sub_stages = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉",""]

    for s in sub_stages:
        assert testbar.BSUB[testbar.sSub] == s
        testbar.update(1)