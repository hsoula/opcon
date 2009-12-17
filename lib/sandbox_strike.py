''' 
   Sandbox strike object
'''

'''
   The Strike object is all the necessary information that a target needs to process the dammage done by the 
   strike.
   SRCP -- The Strike relative Combat Point value of the strike
   type -- the type of ordnance involved.
'''

class sandbox_strike:
    def __init__(self, SRCP = 0.0, label = 'Generic HE', payload = 'HE', delivery='shell'):
        # Label
        self.label = label

        # Strike RCP
        self.SRCP = SRCP
        
        # Hard
        self._hardlist = {'HE':['armor', 'mech'],'HEAT':['armor'],'ICM':[]}
        self._penetrating = [1.0, 10**-1, 20**-1]
        self._nonpenetrating = [.6, 15**-1, 30**-1]
        
        # Payload
        if payload in self._hardlist.keys():
            self.payload = payload
        else:
            self.payload = 'HE'
        self.payload = payload
        
        # Sender
        self.sender = None
        
        # TGT Marker
        self.target = None
        
        # Delivery mode
        self.delivery = delivery
        
    def GetRCP(self):
        return self.SRCP
    
    def DammageDistribution(self, hardware):
        '''! \brief Return a dictionary of dammage.
             \param hardware -> The TOE field of the target Entity
             
             By default, distribute amongst Destruction/Dammage and Suppression.
        '''
        if hardware in self._hardlist[self.payload]:
            # Non penetrating HE on hard targets
            return self._nonpenetrating
        else:
            # Penetrating (same as maneuver)
            return self._penetrating
    





        