'''! base class for systems
'''
import pickle

class system_base(dict):
    def __init__(self):
        self.template_name = ''
    def ToTemplate(self):
        '''! \brief remove sandbox_specific data
        
             Need a virtual method for all the system which will not overload it.
        '''
        return pickle.dumps( self, pickle.HIGHEST_PROTOCOL )
    
    def UpdateGUI(self):
        '''! \brief Set GUI to system's data.
        
             Virtual
        '''
        pass
    
    def fromXML(self, doc, node):
        '''! \brief Virtual method for loading from an XML definition
        '''
        pass
    