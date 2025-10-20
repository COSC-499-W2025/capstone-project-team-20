from zipfile import ZipFile, ZipInfo

class ProjectFolder():

    '''Object That represents a folder in a Tree of ProjectFile and ProjectFolder objects'''

    newID=0
    id: int

    is_root: bool
    name: str
    parent: object
    subdir: list
    children: list

    def __init__(self, file: ZipInfo, parent: object):

        #assign ID and increment shared variable
        self.id=ProjectFolder.newID
        ProjectFolder.newID += 1

        #file.filename is a path string, this seperates it by '/' to isolate the directory name
        namesplit = file.filename.split('/')
        self.name = namesplit[len(namesplit)-2]

        #create empty list for child files, subfolders
        self.children = []
        self.subdir = []

        #if input is not None, its self.parent is parent
        if (parent is not None):
            self.parent=parent
            self.is_root=False
        #if input is None, this ProjectFolder is a root
        else:
            self.parent=self
            self.is_root=True