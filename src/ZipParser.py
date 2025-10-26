from zipfile import ZipFile

from ProjectFile import ProjectFile
from ProjectFolder import ProjectFolder

def parse(path):
    '''Traverses zipped folder and creates a tree of ProjectFolder and ProjectFile objects, returns the root of the tree as an object'''
    with ZipFile(path, 'r') as z:

        start=True

        root: ProjectFolder

        dirs: dict[str,ProjectFolder] = {}

        for file in z.infolist():
            if (start is True): #Creating a root

                #Create a root folder, and add it to the dict, accessed via name
                root = ProjectFolder(file, None)
                dirs[root.name] = root

                start = False

            else:
                if file.is_dir():
                    #determine parent's name
                    parent = file.filename.split("/")
                    parent = parent[len(parent)-3]

                    #create the object
                    temp = ProjectFolder(file,dirs[parent])

                    #add this subfolder to its parent's list
                    dirs[parent].subdir.append(temp)

                    #create new dict entry for this file
                    dirs[temp.name] = temp

                else:
                    #determine parent's name
                    parent = file.filename.split("/")
                    parent = parent[len(parent)-2]

                    #create the object
                    temp = ProjectFile(file,dirs[parent])

                    #add this file to its parent's list
                    dirs[parent].children.append(temp)

    return (root)

def zip_print(root:ProjectFolder):
    '''Runs printHelper with an empty string for organizing file structure'''
    print_helper(root,'')

def print_helper(folder:ProjectFolder, indent:str):
    '''Recursively explores the full tree of subfiles and subfolders under "root", prints them in an easy to read format'''
    # print name of folder
    print(indent+"["+folder.name+"]")

    # traverse child files, printing their names
    if len(folder.children)>0:
        for child in folder.children:
            print(indent+'   '+child.file_name)

    # a recursive call for each subfolder
    if len(folder.subdir)>0:
        for subfolder in folder.subdir:
            print_helper(subfolder,indent+'   ')