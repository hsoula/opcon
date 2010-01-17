''' Setup script for the project, run once.
'''

import os

## Create the environment variable pointing to the home directory
# Installation folder
homefolder = os.getcwd() 

# Write to .bashrc (assumes the bash shell)
if not 'OPCONhome' in os.environ:
    with open('%s/.bashrc'%(os.environ['HOME']), 'w') as fout:
        fout.write('\n# OPCON sandbox home directory\nexport OPCONhome=%s\n\n'%(homefolder))