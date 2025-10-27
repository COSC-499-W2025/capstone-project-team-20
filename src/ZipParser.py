import tempfile
import zipfile
from zipfile import ZipFile

from src.ProjectFile import ProjectFile
from src.ProjectFolder import ProjectFolder

def parse(path):
    '''Traverses zipped folder and creates a tree of ProjectFolder and ProjectFile objects, returns the root of the tree as an object'''
    with ZipFile(path, 'r') as z:
        start=True

        root: ProjectFolder

        dirs: dict[str,ProjectFolder] = {}

        for file in z.infolist():
            if file.filename.startswith("__MACOSX/"):
                continue

            if (start is True): #Creating a root

                #Create a root folder, and add it to the dict, accessed via name
                root = ProjectFolder(file, None)
                dirs[file.filename] = root

                start = False

            else:
                if file.is_dir():
                    #determine parent's name
                    parent = file.filename.split("/")
                    parent = "/".join(parent[:len(parent)-2])+"/"

                    #create the object
                    temp = ProjectFolder(file,dirs[parent])

                    #add this subfolder to its parent's list
                    dirs[parent].subdir.append(temp)

                    #create new dict entry for this file
                    dirs[file.filename] = temp

                else:
                    #determine parent's name
                    parent = file.filename.split("/")
                    parent = "/".join(parent[:len(parent)-1])+"/"

                    #create the object
                    temp = ProjectFile(file,dirs[parent])

                    #add this file to its parent's list
                    dirs[parent].children.append(temp)

    return (root)

def extract_zip(zip_path: str) -> str:
    """
    Extracts a zip archive to a temporary directory.
    Args:
        zip_path: The path to the .zip file to be extracted.
    Returns:
        The path to the temporary directory where files were extracted.
    Raises:
        ValueError: If the path is invalid or the file is not a zip archive.
    """
    temp_dir = tempfile.mkdtemp()
    print(f"Extracting {zip_path} to {temp_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        raise ValueError(f"Error processing zip file: {e}")

    print("Extraction complete.")
    return temp_dir
