'''
   Test Suite file
'''
import syspath
import unittest
import datetime
import sandbox_graphics
import sandbox_geometry
import sandbox_entity
import sandbox_world

from vector import vect_5D

class SandboxTest(unittest.TestCase):
  def setUp(self):
    pass
  
  def testLoadBasicWorldDefault(self):
    sbox = sandbox_world.sandbox()
    self.assertTrue(sbox.OS['gametag'],'Blank World')
    
  def testLoadBasicWorld(self):
    sbox = sandbox_world.sandbox('blankworld.xml')
    self.assertTrue(sbox.OS['gametag'],'Blank World')
    
  def testLoadOneFireTeamNamedLoc(self):
    sbox = sandbox_world.sandbox('testOneFireTeamNameLoc.xml')
    self.assertTrue(sbox.OS['gametag'],'One Fire Team with Named Location')
    
  def testLoadOneFireTeamUTM(self):
    sbox = sandbox_world.sandbox('testOneFireTeamUTM.xml')
    self.assertTrue(sbox.OS['gametag'],'One Fire Team with Named Location')


# suite
testsuite = []

# basic tests on sandbox instance
testsuite.append(unittest.makeSuite(SandboxTest))

# testing OPORD/ COMM tests
import sandbox_comm
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_comm))

# Tasking
import sandbox_tasks
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_tasks))

# Main simulator
import sandbox_world
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_world))

# Entities
import sandbox_entity
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_entity))

# Agents
import sandbox_agent 
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_agent))

# Geometry
import sandbox_geometry
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_geometry))

# Graphics
import sandbox_graphics
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_graphics))

# Infrastructure
import sandbox_infrastructure
#testsuite.append(unittest.TestLoader().loadTestsFromModule(InfrastructureTest))

# Combat
import combat
testsuite.append(unittest.TestLoader().loadTestsFromModule(combat))

# Combat
import C4I
testsuite.append(unittest.TestLoader().loadTestsFromModule(C4I))

# Overall testing of tasks
import SandboxUnitTestTasking
testsuite.append(unittest.TestLoader().loadTestsFromModule(SandboxUnitTestTasking))

import sandbox_TOEM
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_TOEM))

# collate all and run
allsuite = unittest.TestSuite(testsuite)
unittest.TextTestRunner(verbosity=2).run(allsuite)

#unittest.main()
  
  
  
