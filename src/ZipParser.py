import tempfile
import zipfile
import shutil
import yaml
from zipfile import ZipFile, ZipInfo
from pathlib import Path, PurePosixPath

from src.ProjectFile import ProjectFile
from src.ProjectFolder import ProjectFolder
from src.ProgressBar import Bar

CONFIG_DIR = Path(__file__).parent / "config"
IGNORE_DIR = CONFIG_DIR / "ignored_directories.yml"

with open(IGNORE_DIR, "r") as file:
    config = yaml.safe_load(file)

IGNORED_DIRS = set(config.get("ignored_dirs", []))
IGNORED_EXTS = set(config.get("ignored_extensions", []))
IGNORED_FILES = set(config.get("ignored_filenames", []))

def add_to_tree(file: ZipInfo, parent:str, dirs:dict[str, ProjectFolder]) -> None:
    "Adds a file or folder to the project tree."
    if parent not in dirs:
        parent_folder = generate_missing_folder(parent, dirs)
    else:
        parent_folder = dirs[parent]

    if file.is_dir():
        # create the folder we are adding to the tree
        temp = ProjectFolder(file, parent_folder)
        # add this new subfolder to its parent's list
        parent_folder.subdir.append(temp)
    else:
        # create the file we are adding to the tree
        temp = ProjectFile(file, parent_folder)
        # add this new file to its parent's list
        parent_folder.children.append(temp)

    dirs[file.filename] = temp

def generate_missing_folder(parent: str, dirs: dict[str, ProjectFolder]) -> ProjectFolder:
    """
    Checks that all folders for a given parent's filepath exist.
    Creates any folders missing from the filepath and returns the deepest one.
    """
    parts = PurePosixPath(parent).parts
    current_path = ""
    parent_folder = list(dirs.values())[0]  # begin search from the root folder
    for part in parts:
        current_path = f"{current_path}{part}/"
        if current_path not in dirs:
            # create synthetic ZipInfo (Python’s metadata record for each entry in a ZIP) object for missing folder
            synthetic_info = ZipInfo(filename=current_path)
            # create synthetic ProjectFolder object for missing folder
            synthetic_folder = ProjectFolder(synthetic_info, parent_folder)
            # add synthetic folder so files with missing parent folders have a somewhere to go
            parent_folder.subdir.append(synthetic_folder)
            dirs[current_path] = synthetic_folder

        parent_folder = dirs[current_path]

    return parent_folder

def ignore_file_criteria(file: ZipInfo) -> bool:
    """
    Determines if a file/folder should be ignored based on various criteria.
    Returns True if the file should be skipped.
    """
    path_parts = PurePosixPath(file.filename).parts
    filename = path_parts[-1]
    
    # macOS specific ignores
    if "__MACOSX" in path_parts:
        return True
    if any(part.startswith("._") for part in path_parts):
        return True
    if file.filename.endswith(".DS_Store"):
        return True
    
    # Ignore unwanted directories
    if any(part in IGNORED_DIRS for part in path_parts):
        return True
    
    # Ignore unwanted extensions
    if "." in filename:
        ext = filename.split(".")[-1].lower()
        if ext in IGNORED_EXTS:
            return True
        
    # Ignore unwanted files
    if filename.lower() in IGNORED_FILES:
        return True
    
    return False

def parse(path: str) -> ProjectFolder:
    """Traverses zipped folder and creates a tree of ProjectFolder and ProjectFile objects
    Returns the root of the tree as an object"""

    with ZipFile(path, 'r') as z:
        start=True
        root: ProjectFolder
        dirs: dict[str,ProjectFolder] = {}

        #-----     PROGRESS BAR     -----#
        #Get total size of files in zip folder
        total_bytes = 0
        for file in z.infolist():
            total_bytes+=file.file_size
        my_bar = Bar(total_bytes)
        #--------------------------------#

        for file in z.infolist():
            if ignore_file_criteria(file):
                continue

            if start: #Creating a root
                #Create a root folder, and add it to the dict, accessed via name
                root = ProjectFolder(file, None)
                dirs[file.filename] = root
                start = False

            else:
                parent_parts = file.filename.split("/")
                if file.is_dir():
                    parent = "/".join(parent_parts[:-2]) + "/"
                    add_to_tree(file,parent,dirs)

                else:
                    parent = "/".join(parent_parts[:-1]) + "/"
                    add_to_tree(file,parent,dirs)

            #-----     PROGRESS BAR     -----#
            my_bar.update(file.file_size)
            #--------------------------------#

    return (root)

def extract_zip(zip_path: str) -> Path:
    """
    Extracts a zip archive to a temporary directory.
    Args:
        zip_path: The path to the .zip file to be extracted.
    Returns:
        A `pathlib.Path` object pointing to the temporary directory.
    Raises:
        ValueError: If the path is invalid or the file is not a zip archive.
    """
    # Create the temporary directory path as a string first.
    temp_dir_str = tempfile.mkdtemp()
    print(f"Extracting {zip_path} to {temp_dir_str}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir_str)
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        # If extraction fails, ensure the created temp directory is cleaned up.
        shutil.rmtree(temp_dir_str)
        raise ValueError(f"Error processing zip file: {e}")

    print("Extraction complete.")
    # Return the path as a Path object to ensure type consistency.
    return Path(temp_dir_str)

def toString(root: ProjectFolder) -> str:
    '''Runs the helper method to remove the amount of arguments needed on initial call'''
    output = _StringHelper(root,'└──','',True)
    return output

def _StringHelper(folder:ProjectFolder, indent:str, output:str, first:bool) -> str:
    "Recursively explores the full tree of subfiles and subfolders under 'root', combines them into a single string to easily print the tree"
    # add name of folder to string
    if first:
        output+="■["+folder.name+"]"+'\n'
    else:
        output+=indent+"■["+folder.name+"]"+'\n'
        indent = '   ' + indent

    # traverse child files, adds their names to string
    if len(folder.children)>0:
        for child in folder.children:
            output+= indent + child.file_name + '\n'

    # a recursive call for each subfolder
    if len(folder.subdir)>0:
        for subfolder in folder.subdir:
            output = _StringHelper(subfolder,indent,output,False)

    return output

"""
def traverse(folder:ProjectFolder):
    '''THIS IS A TEMPLATE METHOD FOR TREE TRAVERSAL'''
    #[ACCESS FOLDER OBJECT]:
    #---------code---------#
    if len(folder.children)>0:
        for child in folder.children:
            #[ACCESS FILE OBJECT]
            #---------code---------#
    if len(folder.subdir)>0:
        for subfolder in folder.subdir:
            traverse(subfolder)
"""
