'''
   Test Suite file
'''
import syspath
import unittest
import sandbox_template
import datetime
import sandbox_graphics
import sandbox_geometry

from vector import vect_5D

class SandboxTest(unittest.TestCase):
  def setUp(self):
    pass

import sandbox_strike
class SandboxStrike(unittest.TestCase):
  def setUp(self):
    self.W = sandbox_world.sandbox()
    # Create a single unit.
    self.W.AddEntity( sandbox_template.sandbox_templates().CreateUnitArmorBn('TestUnit') )
  def AddGunner(self):
    SP = sandbox_template.sandbox_templates().CreateUnit155SPBty('Gunner')
    self.W.AddEntity(SP)
    SP.SetPosition(vect_5D(10.,0.0))
    return SP
  def CreateCCFZ(self):
    poly = [vect_5D(-2,-2), vect_5D(-2,2),vect_5D(2,2),vect_5D(2,-2)]
    return sandbox_graphics.operational_area('CCFZ', 'WHACK', sandbox_geometry.base_polygon(poly))
    
  def GetUnit(self):
    return self.W.OOB[0]

  def testCreateStrike(self):
    a = sandbox_strike.sandbox_strike(10, '105mm HE', 'HE')
    self.assertEqual(10.0, a.GetRCP())
    
  def testStrikeArmorHE(self):
    a = sandbox_strike.sandbox_strike(10, '105mm HE', 'HE')
    self.GetUnit().InflictDammage(a.GetRCP(), a.DammageDistribution(self.GetUnit()['TOE']))
    self.assertEqual(19.0, self.GetUnit().RawRCP())
    
  def testStrikeArmorICM(self):
    a = sandbox_strike.sandbox_strike(10, '105mm ICM', 'ICM')
    self.GetUnit().InflictDammage(a.GetRCP(), a.DammageDistribution(self.GetUnit()['TOE']))
    self.assertAlmostEqual(18.5, self.GetUnit().RawRCP())

  def test155mmSP(self):
    # Test the creation of a SP bty
    SP = self.AddGunner()
    self.assertEqual(len(self.W.OOB),2)
  
  def test155mmSPIFtask(self):
    # Test the creation of a SP bty
    SP = self.AddGunner()
    # Get CCFZ
    CFFZ = self.CreateCCFZ()
    # Get OPORD
    opord = SP['OPORD']
    overlay = sandbox_graphics.operational_overlay('Bombard!')
    overlay.AddElement(CFFZ)
    opord.SetOverlay(overlay)
    # Add task
    task = sandbox_tasks.taskIndirectFire()
    task['CFFZ'] = CFFZ.Name()
    opord.AddTask(task)
    SP['agent'].ProcessOPORD(opord)
    
    # Simulate 1 hour
    self.W.Simulate()
    
    self.assertEqual(len(self.W.OOB),2)
    
    
    
# suite
testsuite = []

# basic tests on sandbox instance
testsuite.append(unittest.makeSuite(SandboxTest))
#testsuite.append(unittest.makeSuite(SandboxStrike))

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
import C3
testsuite.append(unittest.TestLoader().loadTestsFromModule(C3))

# Overall testing of tasks
import SandboxUnitTestTasking
testsuite.append(unittest.TestLoader().loadTestsFromModule(SandboxUnitTestTasking))

# collate all and run
allsuite = unittest.TestSuite(testsuite)
unittest.TextTestRunner(verbosity=2).run(allsuite)

#unittest.main()
  
  
  
