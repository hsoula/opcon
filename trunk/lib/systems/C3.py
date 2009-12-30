#! \brief Model for Command, Control and Communication.

from random import random

SUP_to_FATG = 0.1
MORAL_FATIGUE_TRIGGER = 0.75

import system_base
import pickle


    
class system_C4I(system_base.system_base):
  '''! \brief Model Command, control and communication.
  
       This model abstract C4I into a small numbers of parameters:
       
       - fatigue : Physical fitness for a task.
       - morale  : Belief that the operation serves a purpose/can be done.
       - suppression : Ability to carry-on a task right now.
       - effectiveness : Probability to carry on a C4I task immediately in ideal conditions.
       
       Other attributes of interest:
       
       - echelon (string) The name of the unit whose entity is the HQ. A unit this get its echelon
       name from the echelon string of its HQ. Its own echelon string is the unit which the unit itself
       is the parent.
       - HQ (sandbox_entity) The unit which is controling the formation.
       - OPCON (sandbox_entity) The unit which is in OPCON for the owning entity. Use OPCON to build combat teams 
       and task force.
       - Subordinates (list, sandbox_entity) A list of entities which are directly under the owning entity.
       
       - SITREP (dict, SITREP) Caching of the most recent SITREP from each subordinates. Indexed by UIDs.
       
       STATIC attributes:
       All scales are static dictionaries which are used to verbalize the abstract numerical scales for morale, fatigue and suppression.       
   '''
  MoraleScale = {0.9:'GREEN', 0.75:'AMBER', 0.6:'RED', 0.4:'BLACK', 0.0:'Broken'}
  CommandScale = {0.9:'GREEN', 0.75:'AMBER', 0.6:'RED', 0.4:'BLACK', 0.0:'Broken'}
  FatigueScale = {0.80:'GREEN', 0.75:'AMBER', 0.6:'RED', 0.3:'BLACK', 0.0:'Exhausted'}
  SuppressionScale = {0.80:'GREEN', 0.60:'AMBER', 0.4:'RED', 0.2:'BLACK', 0.0:'Paralyzed'}  
  effectiveness = {'IDEAL': 1.0, 'EXCELLENT': 0.9, 'PROFESSIONAL': 0.8, 'SUB-STANDARD':0.7, 'DYSFUNCTIONAL': 0.5, 'INCOMPETENT':3.0**-1}
  def __init__(self, ech = ''):
    '''!
       \param ech (string) The name of the echelon that the unit is reponsible for.
    '''
    # Base class
    system_base.system_base.__init__(self)
    
  def fromXML(self, doc, node):
    '''! \brief take care only of relevant info for scenario definition.
    '''
    # Parse XML node
    for i in ['fatigue', 'morale', 'suppression']:
      if doc.Get(node, i):
        self[i] = doc.Get(node, i)
    
    
  def ToTemplate(self):
    '''! \brief Disconnect the pointers to other units and return the pickled string.
    '''
    HQ = self['HQ']
    OPCON = self['OPCON']
    subord = self['subordinates']
    
    self['HQ'] = None
    self['OPCON'] = None
    self['subordinates'] = []
    
    out = pickle.dumps( self, pickle.HIGHEST_PROTOCOL )
    
    self['HQ'] = HQ
    self['OPCON'] = OPCON
    self['subordinates'] = subord
    
    return out
  
  def PrePickle(self,sim):
    '''!
       \param sim (sandbox_world) Needed to make sure that the internal data is made of UIDs.
    '''
    if self['HQ']:
      self['HQ'] = sim.AsUID(self['HQ'])
    if self['OPCON']:
      self['OPCON'] = sim.AsUID(self['OPCON'])
    for i in range(len(self['subordinates'])):
        self['subordinates'][i] = sim.AsUID(self['subordinates'][i])
  
  def PostPickle(self, sim):
    '''!
       \param sim (sandbox_entity) Needed to reconstitute from UID to entities via the sandbox_world.AsEntity method.
    '''
    if self['HQ']:
      self['HQ'] = sim.AsEntity(self['HQ'])
    if self['OPCON']:
      self['OPCON'] = sim.AsEntity(self['OPCON'])
    for i in range(len(self['subordinates'])):
      self['subordinates'][i] = sim.AsEntity(self['subordinates'][i])

  # Interface
  # Transformative

  
  # Informative   
  def LevelHumanFactor(self):
    '''An average of three humand factors'''
    # Internal factors
    internal = ((self['morale'] + self['fatigue'] + self['suppression'])/ 3.0)
    return internal
  
  def LevelCommToHQ(self, mypos):
    '''Factor adjusting the C4I levels due to proximity to higher unit.
       TODO : Establish reasonable range levels and factors.
    '''
    if self.GetHQ():
      d = (mypos-self.GetHQ()['position']).length()
      if d <= 30.0:
        return 1.0
      elif d <= 60.0:
        return 0.80
      else:
        return 0.50
    # No higher Unit
    return 1.0
  
  def LevelDeployState(self, stance):
    '''Level modifier due to stance'''
    if stance == 'transit':
      return 0.8
    return 1.0
  
  def Report(self):
    '''
    '''
    # overall
    report = 'Overall Command and Control : %d%%. '%(100 * float(self))
    # Morale
    report = report + "Morale is at %d %%, "%(100*self['morale'])
    report = report + "fatigue is at %d %% and "%(100*(1-self['fatigue']))
    report = report + "suppression is at %d %%.\n"%(100*(1-self['suppression']))
    return report
    
      
  def KeyLowerThan(self, k, L):
    '''! \brief Return the largest element in L that is smaller than k '''
    candidate = min(L)
    for i in L:
      if i < k and i > candidate:
        candidate = i
    if candidate != -100000.0:
      return candidate
    
    
  def AsStringMorale(self, m = None):
    if m == None:
      m = self['morale']
    L = system_C4I.MoraleScale.keys()
    return system_C4I.MoraleScale[self.KeyLowerThan(m,L)]
  
  def AsStringFatigue(self, m = None):
    if m == None:
      m = self['fatigue']
    k = system_C4I.FatigueScale.keys()
    return system_C4I.FatigueScale[self.KeyLowerThan(m,k)]
  
  def AsStringSuppression(self, m = None):
    if m == None:
      m = self['suppression']
    k = system_C4I.SuppressionScale.keys()
    return system_C4I.SuppressionScale[self.KeyLowerThan(m,k)]
  
  def AsStringCommand(self, m = None):
    if m == None:
      m = self['suppression']
    k = system_C4I.CommandScale.keys()
    return system_C4I.CommandScale[self.KeyLowerThan(m,k)]
    
  def __float__(self):
    '''
       Returns a bounded value:
         0.0 --> No C4I
         1.0 --> Direct and full control
    '''
    # Internal factors
    internal = (self['morale'] + self['fatigue'] + self['suppression'])/ 3.0
      
    return internal
  
  
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
      
if __name__ == "__main__":
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(C3Test))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)  
  