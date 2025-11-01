import sys
from pathlib import Path
import ZipParser
import tempfile
from zipfile import ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

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

def test_toString():
    '''Generate Tree using ZipParser.parse(), using root, request a string representation, compare directly to expected result'''
    root = ZipParser.parse(path)

    result = ZipParser.toString(root)
    expected = "■[testzip]\n└──testfile.txt\n└──■[testsub]\n   └──testsubfile.txt\n└──■[asubfolder]\n   └──wingydingy.txt\n   └──■[subberfolder]\n"

    #Expected:
#       ■[testzip]
#       └──testfile.txt
#       └──■[testsub]
#          └──testsubfile.txt
#       └──■[asubfolder]
#          └──wingydingy.txt
#          └──■[subberfolder]

    print(expected)
    print(result)
    assert expected == result

def create_test_zip(filename, structure):
    """
    Helper to create test zip files.
    structure: list of tuples (path, is_dir)
    """
    temp_dir = tempfile.gettempdir()
    zip_path = Path(temp_dir) / filename
    with ZipFile(zip_path, 'w') as z:
        for path, is_dir in structure:
            if is_dir:
                z.writestr(path + '/', '')
            else:
                z.writestr(path, 'test content')
    return str(zip_path)


def test_missing_intermediate_folders():
    """Test handling zip files without explicit parent directory entries"""
    zip_path = create_test_zip('missing_parents.zip', [
        ('project', True),
        # Note: 'project/deeply/' and 'project/deeply/nested/' are NOT included
        ('project/deeply/nested/deep/file.txt', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert root.name == 'project'
    # Should have created synthetic 'deeply' folder
    assert len(root.subdir) == 1
    deeply = root.subdir[0]
    assert deeply.name == 'deeply'
    # Should have created synthetic 'nested' folder
    assert len(deeply.subdir) == 1
    nested = deeply.subdir[0]
    assert nested.name == 'nested'
    # Should have created synthetic 'deep' folder
    assert len(nested.subdir) == 1
    deep = nested.subdir[0]
    assert deep.name == 'deep'
    # File should be in the deepest folder
    assert len(deep.children) == 1
    assert deep.children[0].file_name == 'file.txt'


def test_ignore_macosx_metadata():
    """Test filtering __MACOSX metadata folders"""
    zip_path = create_test_zip('macos.zip', [
        ('project', True),
        ('project/file.txt', False),
        ('__MACOSX', True),
        ('__MACOSX/project', True),
        ('__MACOSX/project/._file.txt', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert root.name == 'project'
    assert len(root.children) == 1
    assert len(root.subdir) == 0  # __MACOSX should be ignored


def test_ignore_ds_store():
    """Test filtering .DS_Store files"""
    zip_path = create_test_zip('ds_store.zip', [
        ('project', True),
        ('project/file.txt', False),
        ('project/.DS_Store', False),
        ('project/subfolder', True),
        ('project/subfolder/.DS_Store', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert len(root.children) == 1  # Only file.txt
    assert root.children[0].file_name == 'file.txt'


def test_ignore_apple_double_files():
    """Test filtering AppleDouble ._ files"""
    zip_path = create_test_zip('apple_double.zip', [
        ('project', True),
        ('project/file.txt', False),
        ('project/._file.txt', False),
        ('project/subfolder', True),
        ('project/subfolder/._metadata', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert len(root.children) == 1  # Only file.txt
    assert root.children[0].file_name == 'file.txt'


def test_nested_macosx_in_path():
    """Test __MACOSX appearing anywhere in the path"""
    file_info = ZipInfo('some/path/__MACOSX/file.txt')
    assert ZipParser.ignore_file_criteria(file_info) == True
    
    file_info2 = ZipInfo('__MACOSX/deep/path/file.txt')
    assert ZipParser.ignore_file_criteria(file_info2) == True


def test_empty_folders():
    """Test handling zip with empty folders"""
    zip_path = create_test_zip('empty_folders.zip', [
        ('project', True),
        ('project/empty_folder', True),
        ('project/src', True),
        ('project/src/main.py', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert len(root.subdir) == 2
    empty_folder = next(f for f in root.subdir if f.name == 'empty_folder')
    assert len(empty_folder.children) == 0
    assert len(empty_folder.subdir) == 0


def test_files_at_root_level():
    """Test zip with files directly at root"""
    zip_path = create_test_zip('root_files.zip', [
        ('project', True),
        ('project/README.md', False),
        ('project/LICENSE', False),
        ('project/src', True),
        ('project/src/main.py', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert len(root.children) == 2  # README.md and LICENSE
    assert len(root.subdir) == 1  # src folder


def test_complex_real_world_structure():
    """Test a complex structure similar to real coding projects"""
    zip_path = create_test_zip('complex.zip', [
        ('my-project', True),
        ('my-project/.git', True),  # Git folder
        ('my-project/.git/config', False),
        ('my-project/src', True),
        ('my-project/src/__init__.py', False),
        ('my-project/src/module1.py', False),
        ('my-project/src/utils', True),
        ('my-project/src/utils/__init__.py', False),
        ('my-project/src/utils/helper.py', False),
        ('my-project/tests', True),
        ('my-project/tests/test_module1.py', False),
        ('my-project/README.md', False),
        ('my-project/.gitignore', False),
        ('my-project/__MACOSX', True),
        ('my-project/__MACOSX/._README.md', False),
    ])
    
    root = ZipParser.parse(zip_path)
    assert root.name == 'my-project'
    # Should have .git, src, tests (no __MACOSX)
    assert len(root.subdir) == 3
    # Should have README.md and .gitignore at root
    assert len(root.children) == 2


def test_generate_missing_folder_single_level():
    """Test generating a single missing folder"""
    from src.ProjectFolder import ProjectFolder
    
    dirs = {}
    root = ProjectFolder(ZipInfo('root/'), None)
    dirs['root/'] = root
    
    result = ZipParser.generate_missing_folder('root/missing/', dirs)
    
    assert 'root/missing/' in dirs
    assert result.name == 'missing'
    assert len(root.subdir) == 1


def test_generate_missing_folder_multiple_levels():
    """Test generating multiple missing nested folders"""
    from src.ProjectFolder import ProjectFolder
    
    dirs = {}
    root = ProjectFolder(ZipInfo('root/'), None)
    dirs['root/'] = root
    
    result = ZipParser.generate_missing_folder('root/a/b/c/', dirs)
    
    assert 'root/a/' in dirs
    assert 'root/a/b/' in dirs
    assert 'root/a/b/c/' in dirs
    assert result.name == 'c'
    assert len(root.subdir) == 1
    assert root.subdir[0].name == 'a'


def test_add_to_tree_with_existing_parent():
    """Test adding file when parent exists"""
    from src.ProjectFolder import ProjectFolder
    
    dirs = {}
    root = ProjectFolder(ZipInfo('root/'), None)
    dirs['root/'] = root
    
    file_info = ZipInfo('root/test.txt')
    ZipParser.add_to_tree(file_info, 'root/', dirs)
    
    assert len(root.children) == 1
    assert root.children[0].file_name == 'test.txt'


def test_add_to_tree_with_missing_parent():
    """Test adding file when parent doesn't exist"""
    from src.ProjectFolder import ProjectFolder
    
    dirs = {}
    root = ProjectFolder(ZipInfo('root/'), None)
    dirs['root/'] = root
    
    file_info = ZipInfo('root/missing/test.txt')
    ZipParser.add_to_tree(file_info, 'root/missing/', dirs)
    
    assert len(root.subdir) == 1
    assert root.subdir[0].name == 'missing'
    assert len(root.subdir[0].children) == 1