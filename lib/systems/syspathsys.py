'''
   sys path setup
'''
# Alter the sys.path
import sys
from os import getcwd
from os.path import join, split

# Folders
here = getcwd()
lib = split(here)[0]
GUI = join(lib,'GUI')
home = split(lib)[0]
data = join(home,'Data')

sys.path.append(lib)
sys.path.append(GUI)
sys.path.append(home)
sys.path.append(data)