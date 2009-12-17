'''
   sys path setup
'''
# Alter the sys.path so the code can run locally
import sys
from os import getcwd
from os.path import join, split
if not join(getcwd(),'systems') in sys.path:
    sys.path.append(join(getcwd(),'systems'))
if not join(getcwd(),'GUI') in sys.path:
    sys.path.append(join(getcwd(),'GUI'))
if not join(split(getcwd())[0],'Data') in sys.path:
    sys.path.append(join(split(getcwd())[0],'Data'))
if not split(getcwd())[0] in sys.path:
    sys.path.append(split(getcwd())[0])