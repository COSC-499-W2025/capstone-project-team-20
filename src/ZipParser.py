import shutil
import tempfile
import zipfile
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


def ensure_directory_exists(path_str: str, dirs: dict[str, ProjectFolder], roots: dict[str, ProjectFolder]) -> ProjectFolder:
    """
    Ensures that a directory exists in the `dirs` dictionary. If not, it creates
    and adds all necessary parent directories. Returns the directory for the given path.
    """
    if path_str in dirs:
        return dirs[path_str]

    parts = PurePosixPath(path_str).parts

    # Find the root this path belongs to
    root_key = parts[0] + "/" if parts else ""
    if root_key not in roots:
        # This case should ideally not be hit if the logic is correct
        # Create a synthetic root if it's missing
        synthetic_info = ZipInfo(filename=root_key)
        root_folder = ProjectFolder(synthetic_info, parent=None)
        roots[root_key] = root_folder
        dirs[root_key] = root_folder

    # Start from the root and build down
    current_folder = roots[root_key]
    current_path_str = root_key

    # Iterate through parts of the path, skipping the root part
    for part in parts[1:]:
        child_path_str = str(PurePosixPath(current_path_str) / part) + "/"
        if child_path_str not in dirs:
            # Create a synthetic folder for the missing part
            synthetic_info = ZipInfo(filename=child_path_str)
            new_folder = ProjectFolder(synthetic_info, parent=current_folder)
            current_folder.subdir.append(new_folder)
            dirs[child_path_str] = new_folder
            current_folder = new_folder
        else:
            current_folder = dirs[child_path_str]
        current_path_str = child_path_str

    return dirs[path_str]


def add_to_tree(file: ZipInfo, parent_path: str, dirs: dict[str, ProjectFolder], roots: dict[str, ProjectFolder]) -> None:
    """Adds a file or folder to the project tree."""
    parent_folder = ensure_directory_exists(parent_path, dirs, roots)

    # Use PurePosixPath for reliable path handling
    file_path = PurePosixPath(file.filename)
    # Ensure the key ends with a slash for directories
    dict_key = str(file_path)
    if file.is_dir() and not dict_key.endswith('/'):
        dict_key += '/'

    # Prevent re-adding an existing folder
    if file.is_dir() and dict_key in dirs:
        return

    if file.is_dir():
        temp = ProjectFolder(file, parent_folder)
        parent_folder.subdir.append(temp)
    else:
        temp = ProjectFile(file, parent_folder)
        parent_folder.children.append(temp)

    dirs[dict_key] = temp


def ignore_file_criteria(file: ZipInfo) -> bool:
    """
    Determines if a file/folder should be ignored based on various criteria.
    Returns True if the file should be skipped.
    """
    # Ignore empty filenames, which can happen with certain zip files
    if not file.filename:
        return True

    path_parts = PurePosixPath(file.filename).parts
    filename = path_parts[-1] if path_parts else ""

    # macOS specific ignores
    if "__MACOSX" in path_parts:
        return True
    if any(part.startswith("._") for part in path_parts):
        return True
    if filename.endswith(".DS_Store"):
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


def parse_zip_to_project_folders(path: str) -> list[ProjectFolder]:
    """
    Parses a zip file and creates a ProjectFolder tree for each top-level
    directory. Returns a list of root ProjectFolder objects.
    """
    if not path or not Path(path).exists() or not zipfile.is_zipfile(path):
        print(f"Warning: Invalid or non-existent zip file path provided: {path}")
        return []

    try:
        with ZipFile(path, "r") as z:
            total_bytes = sum(file.file_size for file in z.infolist())
            my_bar = Bar(total_bytes)
            infolist = sorted(z.infolist(), key=lambda f: f.filename)

            roots: dict[str, ProjectFolder] = {}
            dirs: dict[str, ProjectFolder] = {}

            # First pass: identify all top-level folders and create roots
            for file in infolist:
                if ignore_file_criteria(file):
                    continue

                path_parts = PurePosixPath(file.filename).parts
                # A file/folder needs to be in a directory to have a root.
                if len(path_parts) > 1:
                    root_name = path_parts[0] + "/"
                    if root_name not in roots:
                        synthetic_info = ZipInfo(filename=root_name, date_time=file.date_time)
                        root_folder = ProjectFolder(synthetic_info, parent=None)
                        roots[root_name] = root_folder
                        dirs[root_name] = root_folder

            # If no subdirectories are found, treat the whole zip as one project.
            if not roots:
                synthetic_info = ZipInfo(filename=Path(path).stem + "/")
                root_folder = ProjectFolder(synthetic_info, parent=None)
                roots[root_folder.name] = root_folder
                dirs[root_folder.name] = root_folder

                for file in infolist:
                    if ignore_file_criteria(file):
                        continue
                    parent_path_str = str(PurePosixPath(file.filename).parent)
                    # Normalize parent path for root files
                    if parent_path_str == '.':
                         parent_path_str = root_folder.name
                    else:
                        parent_path_str = root_folder.name + parent_path_str + "/"

                    add_to_tree(file, parent_path_str, dirs, roots)
                    my_bar.update(file.file_size)
                return list(roots.values())

            # Second pass: build the tree for projects within subdirectories
            for file in infolist:
                if ignore_file_criteria(file):
                    continue

                path = PurePosixPath(file.filename)
                # We only need to add files that are not roots themselves
                if len(path.parts) > 1:
                    parent_path = str(path.parent) + "/"
                    add_to_tree(file, parent_path, dirs, roots)

                my_bar.update(file.file_size)

            return list(roots.values())
    except Exception as e:
        print(f"An error occurred during zip parsing: {e}")
        # Return an empty list or re-raise, depending on desired error handling
        return []

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
