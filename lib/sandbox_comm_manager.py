'''
   sandbox communication manager
   An interface to cached communications
'''

class sandbox_COMM_manager:
    ''' This class is designed to keep track of past communication by indexing, and retrieving
        these from external memory
    '''
    def __init__(self):
        # The dictionary of COMMs
        self.comms = {}
        self.comms['OPORD'] = {}
        