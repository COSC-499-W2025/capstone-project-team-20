from pathlib import Path
import sys
import zipfile
from zipfile import ZipFile
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.ProjectFolder import ProjectFolder

path = "tests/test_resource/testzip.zip"

def test_root_parent_is_self():
    '''Ensure that when a ProjectFolder object is created with None in the parent parameter its parent is set to itself'''
    testroot:object
    with ZipFile(path, 'r') as z:
        rootfolder = z.infolist()[0]
        testroot = ProjectFolder(rootfolder, None)
    
    assert testroot.parent==testroot

def test_name_extracted_correctly():
    '''Ensure that nested and non-nested folders who's ZipInfo.filename contains multiple directories (i.e folder1/folder2/folder3) has its name extracted correctly'''
    with ZipFile(path, 'r') as z:
        filelist = z.infolist()

        testzip = ProjectFolder(filelist[0], None)
        # initial: 'testzip/'
        # desired: 'testzip'
        assert testzip.name == 'testzip'

        testsub = ProjectFolder(filelist[2], None)
        # initial: 'testzip/testsub/'
        # desired: 'testsub'
        assert testsub.name == 'testsub'

        subberfolder = ProjectFolder(filelist[5], None)
        # initial: 'testzip/asubfolder/subberfolder/' 
        # desired: 'subberfolder'
        assert subberfolder.name == 'subberfolder'

