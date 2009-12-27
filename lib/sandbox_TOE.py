'''
    OPCON sandbox entity components
'''

'''
   A container for the equipment and other details about personel. Not meant to keep 
   state information.
'''
from sandbox_exception import SandboxException

class sandbox_personel:
    def __init__(self):
        # List of pointers to weapons
        self.weapon_systems = []
        
        # Kit name (if any)
        self.name = ''
        
        # Allowance count
        self.count = 0
        
        # Logistic model
        self.logistics = None
    
    def fromXML(self, doc, node):
        # Kit name
        self.kit = doc.Get(node, 'name')
        
        # Read in kit's weapons
        for x in doc.Get(node, 'weapon_system',True):
            self.weapon_systems.append(self.datasource.Get('weapon_system',doc.Get(x,'template')))
            
        # Read in logistics parameters
        temp = doc.Get(node, 'logistics')
        if temp:
            template = doc.Get(temp, 'template')
            if not template:
                template = 'base'
            self.logistics = self.datasource.Get('logistics', template)
    
    def GetWeapons(self):
        return self.weapon_systems
    
class sandbox_vehicle(dict):
    def __init__(self):
        self['defense_system'] = None
        self['movement'] = None
        self['criticals'] = {'penetrating':[], 'non penetrating':[]}
        # Logistics
        self.logistics = None
    
    def fromXML(self, doc, node):
        # defense
        x = doc.Get(node,'defense_system')
        if x:
            self['defense_system'] = self.datasource.Get('defense_system', doc.Get(x,'template'))
        
        # Movement
        x = doc.Get(node, 'movement')
        if x:
            template = doc.Get(x,'template')
            if not template:
                template = 'base'
        self['movement'] = self.datasource.Get('movement', template)
        
        # Criticals
        x = doc.Get(node, 'criticals')
        if x:
            for item in doc.ElementAsList(x):
                if item.tagName == 'critical':
                    # Get the data
                    pen = bool(doc.Get(item, 'penetrating'))
                    effect = doc.Get(item, 'effect')
                    wt = doc.Get(item, 'weight')
                    if not wt:
                        wt = 1.0
                    # Ensure that there is data
                    if None in [pen,effect] or '' in [pen,effect]:
                        raise SandboxException('CriticalParseError')
                    if pen:
                        pen = 'penetrating'
                    else:
                        pen = 'non-penetrating'
                    self['criticals'][pen].append((effect, float(wt)))
                    
        # Read in logistics parameters
        temp = doc.Get(node, 'logistics')
        if temp:
            template = doc.Get(temp, 'template')
            if not template:
                template = 'base'
            self.logistics = self.datasource.Get('logistics', template)
            

    def GetMode(self):
        return self['movement']['mode']
class sandbox_weapon_system(dict):
    def __init__(self):
        # Range
        #max_range = 0.0
        #effective_range = 0.0
        #min_range = 0.0
        #allowance.personel
        #allowance.vehicle
        self['allowance'] = {'vehicle':0.0, 'personel':0.0}
        self.sensors = []
        self['logistics'] = {'lift':0.0, 'breakdown':0.0, 'consumption_rate':None}
        self.payload = {}
    
    def fromXML(self, doc, node):
        # Ranges
        for item in ['max_range', 'effective_range', 'min_range']:
            x = doc.Get(node, item)
            if x or x == 0.0:
                self[item] = x
                
        # Allowance
        x = doc.Get(node, 'allowance')
        if x:
            for z in ['personel', 'vehicle']:
                y = doc.Get(x,z)
                if y != None:
                    self['allowance'][z] = y
                    
        # Sensors
        for sensor in doc.Get(node, 'sensor', True):
            mode = doc.Get(sensor,'mode')
            active = bool(doc.Get(sensor,'active'))
            self.sensors.append([mode,active])
            
        # Logistics
        log = doc.Get(node,'logistics')
        if log:
            for x in ['lift','breakdown','consumption_rate']:
                temp = doc.Get(log, x)
                self['logistics'][x] = temp
        
        # Payloads
        for pay in doc.ElementAsList(node):
            if pay.tagName == 'payload':
                x = sandbox_payload()
                x.name = str(doc.Get(pay,'name'))
                x.blast_radius = float(doc.Get(pay,'blast_radius'))
                x.casualty_radius = float(doc.Get(pay,'casualty_radius'))
                x.demolition_points = float(doc.Get(pay,'demolition_points'))
                x.penetration_steel = float(doc.Get(pay,'penetration_steel'))
                # RCP
                temp = doc.Get(pay,'RCP')
                if temp != None:
                    x.RCParea = float(doc.Get(temp,'area'))
                    x.RCPpoint = float(doc.Get(temp,'point'))
                    
                # Effects
                eff = doc.Get(pay,'effect')
                if eff != None:
                    x.effect = doc.AttributesAsDict(eff)
                    
                # Store the instance
                self.payload[x.name] = x

    def GetAllowance(self, x):
        return self['allowance'][x]
    
class sandbox_defense_system(dict):
    def __init__(self):
        self['armor'] = {'top':0.0, 'bottom':0.0, 'front':0.0, 'back':0.0, 'flank':0.0}
    
    def fromXML(self, doc, node):
        # Armor
        x = doc.Get(node, 'armor')
        if x:
            self['armor'] = doc.AttributesAsDict(x)
    
class sandbox_payload:
    def __init__(self):
        self.name = 'base'
        self.RCParea = 0.0
        self.RCPpoint = 0.0
        self.blast_radius = 0.0
        self.casualty_radius = 0.0
        self.demolition_points = 0.0
        self.penetration_steel = 0.0
        self.effect = {}