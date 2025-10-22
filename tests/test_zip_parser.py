import sys
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import ZipParser

#path of test zip folder
path = "tests/test_resource/testzip.zip"

def test_output_tree_structure():
    '''Generate Tree using ZipParser.parse(), navigate all elements and test that they have correct names, parents, list sizes'''
    root = ZipParser.parse(path)
    
    #FOR EACH FOLDER: 
        #Check name
        #Check parent
        #Check the amount of child directories
        #check the amount of child files

    #FOR EACH FOLDER: 
        #Check name
        #Check parent

    #Expected Structure:
        #[testzip]
            #testfile.txt
            #[testsub]
                #testsubfile.txt
            #[asubfolder]
                #wingydingy.txt
                #[subberfolder]

    #[testzip]
    assert root.name == 'testzip'
    assert root.parent is root
    assert len(root.subdir) == 2
    assert len(root.children) == 1
        #testfile.txt
    assert root.children[0].file_name=='testfile.txt'
    assert root.children[0].parent_folder==root
        #[testsub]
    assert root.subdir[0].name=='testsub'
    assert root.subdir[0].parent==root
    assert len(root.subdir[0].subdir) == 0
    assert len(root.subdir[0].children) == 1
            #testsubfile.txt
    assert root.subdir[0].children[0].file_name=='testsubfile.txt'
    assert root.subdir[0].children[0].parent_folder==root.subdir[0]
        #[asubfolder]
    assert root.subdir[1].name=='asubfolder'
    assert root.subdir[1].parent==root
    assert len(root.subdir[1].subdir) == 1
    assert len(root.subdir[1].children) == 1
            #wingydingy.txt
    assert root.subdir[1].children[0].file_name=='wingydingy.txt'
    assert root.subdir[1].children[0].parent_folder==root.subdir[1]
            #[subberfolder]
    assert root.subdir[1].subdir[0].name=='subberfolder'
    assert root.subdir[1].subdir[0].parent==root.subdir[1]
    assert len(root.subdir[1].subdir[0].subdir) == 0
    assert len(root.subdir[1].subdir[0].children) == 0
