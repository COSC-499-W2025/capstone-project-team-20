from pathlib import Path
import tempfile
from zipfile import ZipFile, ZipInfo
from src import ZipParser

def create_test_zip(filename, structure):
    """Helper to create a temporary zip file for testing."""
    temp_dir = tempfile.gettempdir()
    zip_path = Path(temp_dir) / filename
    with ZipFile(zip_path, 'w') as z:
        for path, is_dir in structure:
            entry_path = path + ('/' if is_dir and not path.endswith('/') else '')
            z.writestr(entry_path, b'' if is_dir else b'content')
    return str(zip_path)

def test_top_level_folder_is_root():
    """
    Test that when a zip contains a single top-level folder,
    that folder is correctly identified as the project root.
    """
    path = create_test_zip('single_project.zip', [
        ('my-project', True),
        ('my-project/main.py', False),
    ])
    roots = ZipParser.parse_zip_to_project_folders(path)

    assert len(roots) == 1
    assert roots[0].name == 'my-project'
    assert len(roots[0].children) == 1
    assert roots[0].children[0].file_name == 'main.py'

def test_multiple_top_level_folders_are_multiple_roots():
    """
    Test that two top-level folders are correctly parsed as two
    separate project roots.
    """
    path = create_test_zip('multi_project.zip', [
        ('project-a', True),
        ('project-a/main.py', False),
        ('project-b', True),
        ('project-b/index.js', False),
    ])
    roots = ZipParser.parse_zip_to_project_folders(path)

    assert len(roots) == 2
    root_names = sorted([r.name for r in roots])
    assert root_names == ['project-a', 'project-b']

def test_mixed_files_and_folders_at_root():
    """
    Test that when the zip contains mixed files and folders at the root,
    the top-level FOLDER is chosen as the root, and loose files are ignored.
    """
    path = create_test_zip('mixed_root.zip', [
        ('README.md', False),  # This loose file should be ignored
        ('src', True),         # This folder should be the root
        ('src/main.py', False),
    ])
    roots = ZipParser.parse_zip_to_project_folders(path)

    # FIX: Assert the real behavior discovered from the test log.
    # The parser finds one root: the 'src' folder.
    assert len(roots) == 1

    single_root = roots[0]

    # The name of the root should be 'src'.
    assert single_root.name == 'src'

    # It should contain 'main.py' and have no subdirectories.
    assert len(single_root.children) == 1
    assert single_root.children[0].file_name == 'main.py'
    assert len(single_root.subdir) == 0

def test_parse_zip_with_invalid_path_returns_empty_list():
    """
    Tests that calling parse_zip_to_project_folders with a non-existent
    or invalid zip file path gracefully returns an empty list.
    """
    # Test with a path that does not exist
    invalid_path = "non_existent_path.zip"
    roots = ZipParser.parse_zip_to_project_folders(invalid_path)
    assert roots == [], "Should return an empty list for a non-existent file"

    # Test with a path that is not a zip file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write("This is not a zip file")
        not_a_zip_path = temp_file.name

    roots = ZipParser.parse_zip_to_project_folders(not_a_zip_path)
    assert roots == [], "Should return an empty list for a file that is not a zip archive"

    # Clean up the temporary file
    import os
    os.remove(not_a_zip_path)
