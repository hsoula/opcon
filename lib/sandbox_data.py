'''
   OPCON sandbox data server.
   
'''
if __name__ == '__main__':
    import syspathlib
    import os
    os.chdir('..')

import syspathlib
import os
import os.path

from sandbox_XML import *
from sandbox_TOE import sandbox_personel, sandbox_weapon_system, sandbox_defense_system, sandbox_vehicle
from movement import system_movement
from logistics import system_logistics

from sandbox_exception import SandboxException

class sandbox_data_server:
    def __init__(self, datahead='Data', datafiles=['base.xml']):
        # The base folder for the data
        self.datafolder = os.path.join(os.getcwd(), datahead)
        
        # The live repository
        self.data = {}
        
        # Live pointer caching
        self.pointerCache = {}
        
        # Datatypes
        self.constructor_map = {}
        self.BuildConstructorMap()
        
        # XML instance
        self.xml = None
        
        # Read in file
        for i in datafiles:
            self.ReadFile(i)
        
    def ReadFile(self, fname):
        # Read in the file and index the instances into the data dictionary
        # Test for the file's existance 
        x = os.path.join(self.datafolder,fname)
        if not os.access(x, os.R_OK):
            raise
        
        # Create a XML document
        x = sandboXML(read=x)
        if not x.root.tagName == 'templates':
            raise
        
        # Nodes
        for node in x.ElementAsList(x.root):
            # Imported file
            if node.tagName == 'import':
                self.ReadFile(x.Get(node,'name'))
            for cnode in x.ElementAsList(node):
                # Data node
                if not cnode.tagName in self.data:
                    self.data[cnode.tagName] = {}
                self.data[cnode.tagName][x.Get(cnode,'name')] = (cnode,x)

            
        
        
    def FetchData(self, obj, template_type, name):
        # Populate the data on the instance obj
        # Get the node and the xml daemon
        node, xml = self.data[template_type][name]
        
        # Solve templates
        templates = xml.Get(node, 'template', True)
        for templ in templates:
            self.FetchData(obj, template_type, templ)
            
        # Do the deed
        obj.datasource = self
        obj.fromXML(xml, node)
        del obj.datasource
    
    def Get(self, template_type, name):
        # Keep a pointer to the object for later reference. These
        # object must not contain states as they will be shared.
        # Check for pre-existence
        if template_type in self.pointerCache:
            if name in self.pointerCache[template_type]:
                return self.pointerCache[template_type][name]

        # If not there, fetch the data
        obj = self.GetInstance(template_type)
        if obj == None:
            raise 'Object cannot be cached'
        self.FetchData(obj, template_type, name)

        # Then cache the results
        if not template_type in self.pointerCache:
            self.pointerCache[template_type] = {}
        self.pointerCache[template_type][name] = obj
        return obj
        
    def BuildConstructorMap(self):
        # Store pointers to the class definition so they can be instanciated later
        x = self.constructor_map
        x['personel'] = sandbox_personel
        x['weapon_system'] = sandbox_weapon_system
        x['defense_system'] = sandbox_defense_system
        x['vehicle'] = sandbox_vehicle
        x['movement'] = system_movement
        x['logistics'] = system_logistics
        
    def GetInstance(self, template_name):
        if template_name in self.constructor_map:
            return self.constructor_map[template_name]()
        else:
            raise SandboxException('Data Server Instanciation Failure', template_name)
        
        
# ##################################################################
import unittest
class SandboxDataServer(unittest.TestCase):
    def setUp(self):
        import syspathlib
        import os
        if os.getcwd().endswith('lib'):
            os.chdir('..')
        # Create a sandbox that is empty
        self.server = sandbox_data_server()
  
    def testInitialize(self):
        # make sure there is a key
        #self.assertEqual(len(self.box.KeyGet()), 25)
        self.assert_(self.server)
        

    def testGetBaseCombat(self):
        from combat import *
        x = system_combat()
        self.server.FetchData(x,'combat','base')
        self.assertEqual(x.unit_skill,'untrained')

    def testGetBaseIntelligence(self):
        from intelligence import *
        x = system_intelligence()
        x['signature']['transit'] = 0.1
        self.server.FetchData(x,'intelligence','base')
        self.assertNotEqual(x['signature']['transit'],0.1)
    
    def testGetBaseLogistics(self):
        from logistics import *
        x = system_logistics()
        x['crew_size'] = 10
        self.server.FetchData(x,'logistics','base')
        self.assertNotEqual(x['crew_size'],10)

    def testGetBaseMovement(self):
        from movement import *
        x = system_movement()
        x['mode'] = 'boo'
        self.server.FetchData(x,'movement','base')
        self.assertNotEqual(x['mode'],'boo')

    def testGetBaseMovementAir(self):
        from movement import *
        x = system_movement()
        x['mode'] = 'boo'
        self.server.FetchData(x,'movement','air')
        self.assertEqual(x['mode'],'air')        
        
if __name__ == '__main__':    
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(SandboxDataServer))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)