import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.ProgressBar import Bar
from unittest.mock import patch

def test_too_small_abort():
    '''Bars created with 7 or less bytes (including negative numbers) should abort (create an already completed bar where STAGES is 1)'''

    #we will test this with values -1, 0, 1, 7
    bytes_to_test = [-1,0,1,7]
    for n in bytes_to_test:
        testbar = Bar(n)
        #Check the bar will display as: |█| (n Bytes/n Bytes)
        assert testbar.bar_complete == '█'
        assert testbar.bar_remaining == ''
        assert testbar.sub_stage_idx == 8
        assert testbar.TOTAL_BYTES == n
        assert testbar.current_total == n

        #Check that the bar is incomplete
        assert testbar.stages_completed == 1
        assert testbar.stages_remaining == 0

def test_bars_have_correct_length():
    '''Bars created with bytes in the range [8-15] should create a bar of length 1'''
    #we will test this with values 8,15
    bytes_to_test = [8,15]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == ''
        assert testbar.stages_remaining == 1
        assert testbar.STAGES == 1

    '''Bars created with bytes in the range [16-31] should create a bar of length 2'''
    #we will test this with values 16,31
    bytes_to_test = [16,31]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == ' '
        assert testbar.stages_remaining == 2
        assert testbar.STAGES == 2

    '''Bars created with bytes in the range [32-63] should create a bar of length 4'''
    #we will test this with values 32,63
    bytes_to_test = [32,63]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == '   '
        assert testbar.stages_remaining == 4
        assert testbar.STAGES == 4

    '''Bars created with bytes in the range [64-127] should create a bar of length 8'''
    #we will test this with values 64,127
    bytes_to_test = [64,127]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == '       '
        assert testbar.stages_remaining == 8
        assert testbar.STAGES == 8

    '''Bars created with bytes in the range [128-255] should create a bar of length 16'''
    #we will test this with values 128-255
    bytes_to_test = [128,255]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == '               '
        assert testbar.stages_remaining == 16
        assert testbar.STAGES == 16

    '''Bars created with bytes in the range [256-511] should create a bar of length 32'''
    #we will test this with values 256,511
    bytes_to_test = [256,511]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == '                               '
        assert testbar.stages_remaining == 32
        assert testbar.STAGES == 32

    '''Bars created with 512 or more bytes should create a bar of length 64'''
    #we will test this with values 512, 9999999
    bytes_to_test = [512,9999999]
    for n in bytes_to_test:
        testbar = Bar(n)
        #check general variables are correct
        assert testbar.TOTAL_BYTES == n
        assert testbar.stages_completed == 0
        assert testbar.sub_stage_idx == 0
        assert testbar.bar_complete == ''
        assert testbar.current_total == 0

        #check variables that will change between sizes
        assert testbar.bar_remaining == '                                                               '
        assert testbar.stages_remaining == 64
        assert testbar.STAGES == 64

def test_update_overflow():
    '''Updating a bar with more bytes than remain in the bar should result in a completed bar with correct values i.e (x bytes/x bytes)'''
    testbar = Bar(8)
    testbar.update(16)
    assert testbar.current_total == 8
    assert testbar.bar_complete == '█'
    assert testbar.sub_stage_idx == 8
    assert testbar.bar_remaining == ''

def test_negative_update():
    '''Updating a bar with negative values should not impact the current progress'''
    testbar = Bar(8)

    #test after update, then test same changes after subtracting -1
    testbar.update(1)
    assert testbar.SUB_CHARS[testbar.sub_stage_idx] == '▏'
    assert testbar.current_total==1
    testbar.update(-1)
    assert testbar.SUB_CHARS[testbar.sub_stage_idx] == '▏'
    assert testbar.current_total==1


def test_update_completed_bar():
    '''Updating a bar which is already complete should not impact the progress'''
    testbar = Bar(8)

    testbar.update(8)
    assert testbar.SUB_CHARS[testbar.sub_stage_idx] == ''
    assert testbar.bar_complete == '█'
    assert testbar.current_total==8

    testbar.update(35783849)
    assert testbar.SUB_CHARS[testbar.sub_stage_idx] == ''
    assert testbar.bar_complete == '█'
    assert testbar.current_total==8

def test_auto_complete():
    '''Bars not evenly divisible into stages will auto complete (adding the remainder) when the visual progress completes'''
    testbar = Bar(9)

    #update 8 so 1 remaining until complete
    testbar.update(8)

    #should auto complete to be at 9
    assert testbar.current_total == 9

def test_substage_cycle():
    '''Test that substages are correctly cycled through producing the correct string at each point'''
    testbar = Bar(8)

    sub_stages = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉",""]

    for s in sub_stages:
        assert testbar.SUB_CHARS[testbar.sub_stage_idx] == s
        testbar.update(1)

def test_output_call_count_is_bounded():
    '''output() should only be called on stage/substage completions, not on every tiny update.
    Max calls = STAGES * 8 substages + 1 final = 513. Should never equal update count when updates >> stages.'''
    testbar = Bar(512000)  # 64 stages

    with patch.object(testbar, 'output') as mock_output:
        for _ in range(512000):  # one byte at a time — far more updates than stages
            testbar.update(1)

    assert mock_output.call_count <= 513       # bounded by stage structure
    assert mock_output.call_count < 512000     # definitely not once per update

def test_output_calls_scale_with_stages_not_updates():
    '''output() call count should be proportional to STAGES, not update count.'''
    testbar = Bar(9999999)  # 64 stages

    with patch.object(testbar, 'output') as mock_output:
        for _ in range(10000):
            testbar.update(1)  # 1 byte at a time, far smaller than a stage

    assert mock_output.call_count <= 513
    assert mock_output.call_count < 10000

def test_zero_byte_updates_dont_regress_progress():
    '''Updating with 0 bytes repeatedly should not change bar state or trigger extra output calls'''
    testbar = Bar(512)
    testbar.update(256)  # get to 50%

    state_before = (testbar.current_total, testbar.stages_completed, testbar.sub_stage_idx)

    for _ in range(1000):
        testbar.update(0)

    state_after = (testbar.current_total, testbar.stages_completed, testbar.sub_stage_idx)
    assert state_before == state_after

def test_large_bar_completes_from_many_small_updates():
    '''A 64-stage bar fed many small updates should reach full completion correctly'''
    total = 9082926429  # realistic large ZIP size
    testbar = Bar(total)

    chunk = 1_000_000
    sent = 0
    while sent < total:
        to_send = min(chunk, total - sent)
        testbar.update(to_send)
        sent += to_send

    assert testbar.current_total == total
    assert testbar.bar_complete == '█' * testbar.STAGES
    assert testbar.sub_stage_idx == 8
    assert testbar.stages_remaining == 0