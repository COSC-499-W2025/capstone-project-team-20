from zipfile import ZipFile, ZipInfo

class ProjectFile():

    '''Object That represents a file in a Tree of ProjectFile and ProjectFile objects'''

    is_root: bool
    name: str
    parent: object

    def __init__(self, file: ZipInfo, parent: object):

        #file.filename is a path string, this seperates it by '/' to isolate the directory name
        namesplit = file.filename.split('/')
        self.name = namesplit[len(namesplit)-1]

        #set parent to the name of the folder this file resides in
        self.parent = parent