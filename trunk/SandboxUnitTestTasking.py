import unittest
import datetime

import syspath
import sandbox_comm
import sandbox_world
import sandbox_tasks
import sandbox_entity

from vector import vect_3D

class SandBoxEmptyWorld(unittest.TestCase):
  def setUp(self):
    self.W = sandbox_world.sandbox()
    # Create a single unit.
    self.W.AddEntity( sandbox_entity.sandbox_entity(template='FireTeam', sim=self.W) )
    
  def GetUnit(self):
    return self.W.OOB[0]
  
  def GetOPORD(self):
    return sandbox_comm.OPORD(self.GetUnit(), self.GetUnit())
    
  def testRedeployTask(self):
    # Redeploy task
    import sandbox_tasks
    task = sandbox_tasks.taskRedeploy()
    task['final_stance'] = 'transit'
    
    # Make and opord
    opord = self.GetOPORD()
    
    # Add a task
    opord.AddTask(task)
    
    # Issue Order
    self.GetUnit().IssueOrder(opord)
    
    # 1 hour simulate
    self.W.Simulate(datetime.timedelta(hours=2.0))
    
    self.assertEqual(self.GetUnit().GetStance(),'transit')
    
  def testRedeployTwoTask(self):
    # Redeploy task
    import sandbox_tasks
    task = sandbox_tasks.taskRedeploy()
    task['final_stance'] = 'transit'

    task2 = sandbox_tasks.taskRedeploy()
    task2['final_stance'] = 'offense'
    
    # Make and opord
    opord = self.GetOPORD()
    
    # Add a task
    opord.AddTask(task)
    opord.AddTask(task2)
    
    # Issue Order
    self.GetUnit().IssueOrder(opord)
    
    # 1 hour simulate
    self.W.Simulate(datetime.timedelta(hours=2.0))
    
    self.assertEqual(self.GetUnit().GetStance(),'offense')
    
  def testRedeployAbortSecondTask(self):
    # Redeploy task
    import sandbox_tasks
    task = sandbox_tasks.taskRedeploy()
    task['final_stance'] = 'transit'

    task2 = sandbox_tasks.taskRedeploy()
    task2['final_stance'] = 'offense'
    
    # Make and opord
    opord = self.GetOPORD()
    
    # Add a task
    opord.AddTask(task)
    opord.AddTask(task2)
    
    # Issue Order
    self.GetUnit().IssueOrder(opord)
    
    # 1 hour simulate
    self.W.Simulate(datetime.timedelta(hours=.5))
    
    # cancel the future order
    mytask = self.GetUnit()['OPORD'].GetCurrentTask()
    cursor = self.GetUnit()['OPORD']['EXECUTION']['MANEUVER TASKS']['cursor'] + 1
    mytask = self.GetUnit()['OPORD']['EXECUTION']['MANEUVER TASKS']['sequence'][cursor]
    
    self.GetUnit()['OPORD'].CancelTask(mytask)
    
    # 1.5 hour simulate
    self.W.Simulate(datetime.timedelta(hours=1.5))
    self.assertEqual(self.GetUnit().GetStance(),'transit')

  def testRedeployAbortTask(self):
    # Redeploy task
    import sandbox_tasks
    task = sandbox_tasks.taskRedeploy()
    task['final_stance'] = 'transit'
    
    # Make and opord
    opord = self.GetOPORD()
    
    # Add a task
    opord.AddTask(task)
    
    # Issue Order
    self.GetUnit().IssueOrder(opord)
    
    # 1/2 hour simulate
    self.W.Simulate(datetime.timedelta(hours=.5))
    
    # Send a Cancel order
    mytask = self.GetUnit()['OPORD'].GetCurrentTask()
    self.GetUnit()['OPORD'].CancelTask(mytask)

    # 1 1/2 hour simulate
    self.W.Simulate(datetime.timedelta(hours=1.5))    
    
    self.assertEqual(self.GetUnit().GetStance(),'deliberate defense')
    

  def testRelocateTask1step(self):
    # Set stance to transit
    self.GetUnit().SetStance('transit')
    
    # Redeploy task
    import sandbox_tasks
    task = sandbox_tasks.taskRelocate()
    task['destination'] = vect_3D(20,20)
    
    # Make and opord
    opord = self.GetOPORD()
    
    # Add a task
    opord.AddTask(task)
    
    # Issue Order
    self.GetUnit().IssueOrder(opord)
    
    # 1 hour simulate
    self.W.Simulate(datetime.timedelta(hours=2.0))
    
    self.assertEqual(self.GetUnit()['position'].x,20.0)
  
  def testRelocateTask3step(self):
    
    # Redeploy task
    import sandbox_tasks
    task = sandbox_tasks.taskRelocate()
    task['destination'] = vect_3D(20,20)
    task['final_stance'] = 'deliberate defense'
    task['stance'] = 'transit'
    
    # Make and opord
    opord = self.GetOPORD()
    
    # Add a task
    opord.AddTask(task)
    
    # Issue Order
    self.GetUnit().IssueOrder(opord)
    
    # 1 hour simulate
    self.W.Simulate(datetime.timedelta(hours=3.0))
    
    self.assertEqual(self.GetUnit()['position'].x,20.0)
    
if __name__ == '__main__':
  # suite
  testsuite = []
  
  # Task testing
  testsuite.append(unittest.makeSuite(SandBoxEmptyWorld))
  testsuite.append(unittest.makeSuite(SandBoxThreeUnitsWorld))
  # collate all and run
  allsuite = unittest.TestSuite(testsuite)
  unittest.TextTestRunner(verbosity=2).run(allsuite)