'''
   sys path setup
'''
# Alter the sys.path so the code can run locally
import sys
from os import getcwd
from os.path import join, split

home = split(getcwd())[0]
lib = join(home,'lib')
systems = join(lib,'systems')
gui = join(lib,'GUI')

pth = [home,lib,systems,gui]
for i in pth:
    if not i in sys.path:
        sys.path.append(i)
