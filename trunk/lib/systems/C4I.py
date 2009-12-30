#! \brief Model for Command, Control and Communication.

from random import random

SUP_to_FATG = 0.1
MORAL_FATIGUE_TRIGGER = 0.75

import system_base
import pickle
    
class system_C4I(system_base.system_base):
  '''!
       Controler class for data transfer and storage for a unit.
  '''
  MoraleScale = {0.9:'GREEN', 0.75:'AMBER', 0.6:'RED', 0.4:'BLACK', 0.0:'Broken'}
  CommandScale = {0.9:'GREEN', 0.75:'AMBER', 0.6:'RED', 0.4:'BLACK', 0.0:'Broken'}
  FatigueScale = {0.80:'GREEN', 0.75:'AMBER', 0.6:'RED', 0.3:'BLACK', 0.0:'Exhausted'}
  SuppressionScale = {0.80:'GREEN', 0.60:'AMBER', 0.4:'RED', 0.2:'BLACK', 0.0:'Paralyzed'}  
  effectiveness = {'IDEAL': 1.0, 'EXCELLENT': 0.9, 'PROFESSIONAL': 0.8, 'SUB-STANDARD':0.7, 'DYSFUNCTIONAL': 0.5, 'INCOMPETENT':3.0**-1}
  
  def __init__(self):
    # Base class
    system_base.system_base.__init__(self)
    
    # training level
    self.training_level = 'regular'
    
    # Bandwidth
    self.bandwidth = None
    
    # Comm range
    self.wireless_range_effective = 30.0
    self.wireless_range_max = 60.0
    
    
  # File transactions
  def fromXML(self, doc, node):
    '''! \brief take care only of relevant info for scenario definition.
    '''
    # Parse XML node
    # training level
    self.training_level = doc.SafeGet(node,'training_level', self.training_level)
      
    # bandwidth
    self.bandwidth = doc.SafeGet(node,'bandwidth', self.bandwidth)
      
    # Wireless
    wir = doc.Get(node,'wireless')
    if x:
      self.wireless_range_effective = doc.Get(wir,'effective_range',self.wireless_range_effective)
      self.wireless_range_max = doc.Get(wir,'max_range',self.wireless_range_max)
      
      
      
  # Command Structure
  # Human Factors
  def AdjustHumanFactor(self, baseval, val):
    ''' Adjust a human factor such that it goes up/down slower when outside of the range
        When above 1.0, goes up very slowly but down normally.
    '''
    mod = 1.0
    if baseval < 0.50: 
      mod = 0.1
    elif baseval > 1.0 and val >= 0.0:
      mod = mod * 0.01
    val = val * mod
    return max((baseval + val),0.0)
    
  def LevelDeployState(self, stance):
    '''Level modifier due to stance'''
    if stance == 'transit':
      return 0.8
    return 1.0
  
  def LevelHumanFactor(self, E):
    '''An average of three human factors'''
    # Internal factors
    internal = ((E.GetMorale() + E.GetFatigue() + E.GetSuppression())/ 3.0)
    return internal
  
  # Communication
  def LevelCommToHQ(self, E):
    '''Factor adjusting the C4I levels due to proximity to higher unit.
       TODO : Establish reasonable range levels and factors.
    '''
    if E.GetHQ():
      d = (E.Position()-E.GetHQ().Position()).length()
      if d <= self.wireless_range_effective:
        return 1.0
      elif d > self.wireless_range_max:
        return 0.0
      else:
        return 0.50
    # No higher Unit
    return 1.0
  

  # Verbalization
  def KeyLowerThan(self, k, L):
    '''! \brief Return the largest element in L that is smaller than k '''
    candidate = min(L)
    for i in L:
      if i < k and i > candidate:
        candidate = i
    if candidate != -100000.0:
      return candidate
    
    
  def AsStringMorale(self, m):
    L = system_C4I.MoraleScale.keys()
    return system_C4I.MoraleScale[self.KeyLowerThan(m,L)]
  
  def AsStringFatigue(self, m ):
    k = system_C4I.FatigueScale.keys()
    return system_C4I.FatigueScale[self.KeyLowerThan(m,k)]
  
  def AsStringSuppression(self, m):
    k = system_C4I.SuppressionScale.keys()
    return system_C4I.SuppressionScale[self.KeyLowerThan(m,k)]
  
  def AsStringCommand(self, m):
    k = system_C4I.CommandScale.keys()
    return system_C4I.CommandScale[self.KeyLowerThan(m,k)]
 
  # Situation
  def Report(self, E):
    '''
    '''
    # overall
    report = 'Overall Command and Control : %d%%. '%(100 * self.LevelHumanFactor(E))
    # Morale
    report = report + "Morale is at %d %%, "%(100*E.GetMorale())
    report = report + "fatigue is at %d %% and "%(100*(1-E.GetFatigue()))
    report = report + "suppression is at %d %%.\n"%(100*(1-E.GetSuppression()))
    return report
    
      
 
  
import unittest
class C4ITest(unittest.TestCase):
    def testAsStringMoraleBroken(self):
      C = system_C4I()
      self.assertEqual('Broken',C.AsStringMorale(0.01))
      
    def testAsStringMoraleBLACK(self):
      C = system_C4I()
      self.assertEqual('BLACK',C.AsStringMorale(0.41))
      
    def testAsStringMoraleRED(self):
      C = system_C4I()
      self.assertEqual('RED',C.AsStringMorale(0.61))
      
    def testAsStringMoraleAMBER(self):
      C = system_C4I()
      self.assertEqual('AMBER',C.AsStringMorale(0.76))
    
    def testAsStringMoraleGREEN(self):
      C = system_C4I()
      self.assertEqual('GREEN',C.AsStringMorale(0.91))
      
    def testLevelDeployStateTransit(self):
      C = system_C4I()
      self.assertEqual(0.8, C.LevelDeployState('transit'))
      
    def testLevelDeployStateDeployed(self):
      C = system_C4I()
      self.assertEqual(1.0, C.LevelDeployState('deployed'))
      
if __name__ == "__main__":
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(C4ITest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)  
  