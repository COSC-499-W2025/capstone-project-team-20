from zipfile import ZipFile

from ProjectFile import *
from ProjectFolder import *

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

"""
def traverse(folder:ProjectFolder):
    '''THIS IS A TEMPLATE FOR TREE TRAVERSAL'''
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
