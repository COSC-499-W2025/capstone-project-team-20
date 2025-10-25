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
            if (start is True): #Creating a root
                
                #Create a root folder, and add it to the dict, accessed via name
                root = ProjectFolder(file, None)
                dirs[root.name] = root

                print(root.name)

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