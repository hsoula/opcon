'''
   sys path setup
'''
# Alter the sys.path
import sys
from os import getcwd
from os.path import join

folder = join(getcwd(),'lib')
if not folder in sys.path:
    sys.path.append(folder)
    
folder = join(getcwd(),'Data')
if not folder in sys.path:
    sys.path.append(folder)
    
folder = join(getcwd(),'lib','systems')
if not folder in sys.path:
    sys.path.append(folder)
    
folder = join(getcwd(),'lib','GUI')
if not folder in sys.path:
    sys.path.append(folder)

#from random import seed
#seed(123456787)