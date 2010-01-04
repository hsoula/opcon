'''
   sandbox_names: structured hiearchical unit designation.
'''

class sandbox_name:
    echelon_offset = {'Team':0,'Sec':1,'Sqd':1,'Plt':2,'Troop':2,'Coy':3,'Bn':4,'Rgt':4,'Bde':5,'Div':6,'Corps':7,'Army':8}
    def __init__(self, name, echelon='Team'):
        # create all (Team, Sec, Plt, Coy, Bn, Bde, Div, Corps, Army)
        self.tokens = ['']*8
        
        # Preprocess the name
        name = name.replace('-','/')
        temp = name.split('/')
        
        # Add empty tokens
        temp = ['']*sandbox_name.echelon_offset[echelon] + temp
        
        