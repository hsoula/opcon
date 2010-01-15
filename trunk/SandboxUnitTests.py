'''
   Test Suite file
'''
import syspath
import unittest
import datetime
import os
import os.path
import sandbox_graphics
import sandbox_geometry
import sandbox_entity
import sandbox_world

from vector import vect_5D

class SandboxTest(unittest.TestCase):
  def setUp(self):
    pass
  
  # Milestone 1
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

  def testCreateFileSystem(self):
    sbox = sandbox_world.sandbox('testOneFireTeamUTM.xml')
    # Check for file system override
    rootexists = os.path.exists(os.path.join('Simulations','One_Fire_Team_UTM'))
    blue = os.path.exists(os.path.join('Simulations','One_Fire_Team_UTM','BLUE'))
    self.assertEqual([rootexists,blue],[True,True])
    
  def testExecuteFromXML(self):
    sbox = sandbox_world.sandbox('testOneFireTeamUTMexec.xml')
    # Retrieve the clock 
    clock = sbox.GetClock()
    # It should be 0800 after execution
    self.assertEqual(clock, datetime.datetime(2010,1,3,8,0))

  def testExecuteBlankFromXML(self):
    sbox = sandbox_world.sandbox('blankworldexec.xml')
    # Retrieve the clock 
    clock = sbox.GetClock()
    # It should be 0800 after execution
    self.assertEqual(clock, datetime.datetime(2010,1,3,8,0))
    
  def testLoadSavedGame(self):
    # Create a blank world
    sbox = sandbox_world.sandbox('blankworld.xml')
    # Run it once for 1 hour then save
    sbox.Simulate()
    sbox.Save()
    clock1 = sbox.GetClock()
    
    # Load most recent save for this game
    sbox = sandbox_world.sandbox('Blank World')
    # Get Clock
    clock2 = sbox.GetClock()
    
    self.assertEqual(clock1, clock2)
    
  def testLoadSavedGameWithUnit(self):
    # Create a blank world
    sbox = sandbox_world.sandbox('testOneFireTeamUTM.xml')
    # Run it once for 1 hour then save
    sbox.Simulate()
    sbox.Save()
    ooblen = len(sbox.GetOOB())
    
    # Load most recent save for this game
    sbox = sandbox_world.sandbox('One Fire Team UTM')
    
    self.assertEqual(ooblen, len(sbox.GetOOB()))
    
# Suite
testsuite = []

# Basic tests on sandbox instance
testsuite.append(unittest.makeSuite(SandboxTest))

# Testing OPORD/ COMM tests
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

# Sensors
import sandbox_sensor
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_sensor))

# Combat
import combat
testsuite.append(unittest.TestLoader().loadTestsFromModule(combat))

# Combat
import C4I
testsuite.append(unittest.TestLoader().loadTestsFromModule(C4I))

import intelligence
testsuite.append(unittest.TestLoader().loadTestsFromModule(intelligence))

# Overall testing of tasks
import SandboxUnitTestTasking
#testsuite.append(unittest.TestLoader().loadTestsFromModule(SandboxUnitTestTasking))

import sandbox_TOEM
testsuite.append(unittest.TestLoader().loadTestsFromModule(sandbox_TOEM))

# Collate all and run
allsuite = unittest.TestSuite(testsuite)
unittest.TextTestRunner(verbosity=2).run(allsuite)

#unittest.main()

