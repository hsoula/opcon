#! \brief Model for Command, Control and Communication.

from random import random

SUP_to_FATG = 0.1
MORAL_FATIGUE_TRIGGER = 0.75

import system_base
import pickle

class system_C3(system_base.system_base):
  '''! \brief Model Command, control and communication.
  
       This model abstract C3 into a small numbers of parameters:
       
       - fatigue : Physical fitness for a task.
       - morale  : Belief that the operation serves a purpose/can be done.
       - suppression : Ability to carry-on a task right now.
       - effectiveness : Probability to carry on a C3 task immediately in ideal conditions.
       
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
    system_base.system_base.__init__(self)
    # Human dimension
    self['fatigue'] = 1.0
    self['morale'] = 1.0
    self['suppression'] = 1.0
    
    # Effectiveness
    self['effectiveness'] = 'IDEAL'
    
    # Connections
    self['echelon'] = ech
    self['HQ'] = None
    self['OPCON'] = None
    self['subordinates'] = []
    
    # 
    self['SITREP'] = {}
    
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
 
  def AdjustMorale(self, val):
    '''! \brief Adjust the value of morale by some value
         \param val (float) A valid floating point variable.
         
         \note Morale goes some 0.1 times the rate when in the lower half and 1% the rate when above 1.0.
         No negative values are accepted.
    '''
    mod = 1.0
    if self['morale'] < 0.50: 
      mod = 0.1
    elif self['morale'] > 1.0:
      mod = mod * 0.01
    val = val * mod
    self['morale'] = max((self['morale'] + val),0.0)
  
  def AdjustFatigue(self, val):
    '''! \brief Adjust fatigue by a value.
         \param val (float) A valid float value.
         \note Fatigue is bounded [0.0,1.0]
    '''
    self['fatigue'] = max(min(self['fatigue']+val,1.0),0.0)
  def CacheSITREP(self, uid, sitrep):
    '''!
       Cache the sitrep for a subordinate unit, indexing by uid.
    '''
    self['SITREP'][uid] = sitrep    
  def DeleteSubordinate(self, sub):
    '''!
       Disconnect the subordinate and delete the last SITREP.
       \param sub (sandbox_entity) A subordinate unit to diconnect.
       \note This method is called from the entity and redirected via __getattr__ most of the time. 
    '''
    out = False
    if sub in self['subordinates']:
      self['subordinates'].remove(sub)
      out = True
    if self['SITREP'].has_key(sub['uid']):
      del self['SITREP'][sub['uid']]  
    return out
      
  def Regroup(self, mylevel):
    '''!
        Convert some suppresion into fatigue at a rate of 5% per 10 mins, and 0.5% of
        suppression is converted into fatigue.
    '''
    if self.GetHQ() != None:
      # An average of self and superior
      target = (mylevel +  self.GetHQ().C3Level()) * 0.5
    else:
      target = mylevel * 0.5
      
    if target == 1.0:
      target = 0.99999
    elif target == 0.0:
      target = 0.000001
    
    # Supre
    newsup = self['suppression'] ** (1.0 - target)
    recover = newsup - self['suppression']
    if recover > 0.05:
      recover = 0.05 + (0.1 * random() * (recover - 0.1))
      #recover = 0.1
    frecover = recover * SUP_to_FATG
   
    # recover SUP to Fatigue
    self['suppression'] = min(1.0, self['suppression'] + recover)
    self['fatigue'] = max(0.0 , self['fatigue'] - frecover)
    
    # Dampen moral high @ 0.1% per pulse
    if self['morale'] > 1.0:
      self['morale'] = max(1.0, self['morale']- 0.001)
      
    # Lose morale if fatigued
    if self['fatigue'] < MORAL_FATIGUE_TRIGGER:
      self['morale'] = max(0.0, self['morale'] - 0.001)
      
    # recover and fatigue absorbed
    return recover, frecover    
    
  def Suppress(self, val):
    '''! \brief  Adjust supression by val.
         \param val (float) A suppression value. A positive value in this case is 
         expected to be effective suppression, not unsuppress.
         \note suppression is bounded [0.0, 1.0]
    '''
    self['suppression'] = self['suppression'] - val
    self['suppression'] = min(1.0, self['suppression'])
    self['suppression'] = max(0.0, self['suppression'])
  
  # Informative
  def GetHQ(self):
    '''! \brief returns the commanding unit, regardless of who is in command.
    '''
    if self.IsOPCON():
      return self['OPCON']
    return self['HQ']
  
  def IsOPCON(self):
    '''! \brief Returns True if the unit is in OPCON
    '''
    return bool(self['OPCON'])
  
  def Subordinates(self):
    '''! \brief Access to all subordinates in OPCON.
    '''
    return self['subordinates']
  
  def EchelonSubordinates(self, OPCON_only = True):
    '''! \brief a vector of all Subordinates in the same echelon.
    
         \param OPCON_only Limit selection to those under direct control. 
    '''
    out = []
    for i in self['subordinates']:
      if not i.IsOPCON():
        out.append(i)
    
    # Add detached unitss
    if not OPCON_only:
      out += self.DetachedSubordinates()
    
    return out
  
  def AttachedSubordinates(self):
    '''! \brief A vector of subordinate unit/echelon under OPCON
    '''
    temp = self.EchelonSubordinates()
    out = []
    
    # Add if not an echelon member
    for i in self['subordinates']:
      if not i in temp:
        out.append(i)
    
    return []
  
  def DetachedSubordinates(self):
    '''! \brief A vector of echelon/units under someone else's OPCON
    '''
    # Fetch a sim
    sim = None
    if self['HQ']:
      sim = self['HQ'].sim
    elif len(self['subordinates']):
      sim = self['subordinates'].sim
    
    out = []
    # Re-hydrate the detached list
    for i in self['detached']:
      out.append(sim.AsEntity(i))
      
    return out
  
  def AllSubordinates(self):
    '''
       OUTPUT : a list of all subordinates at all lower level
    '''
    out = []
    for i in range(len(self['subordinates'])):
      out = out + [self['subordinates'][i]] + self['subordinates'][i]['C3'].AllSubordinates()
    return out
  
  def GetEffectiveness(self):
    if type(self['effectiveness']) == type('') and self['effectiveness'] in self.effectiveness:
      return self.effectiveness[self['effectiveness']]
    elif type(self['effectiveness']) == type(1.0):
      return self['effectiveness']
    else:
      return 1.0
  def GetMorale(self):
    return self['morale']
  def GetFatigue(self):
    '''! \bief Access Fatigue
    '''
    return self['fatigue']
  def IsCommandUnit(self):
    if self['subordinates']:
      return 1
    return 0
    
  def IsSuppressed(self):
    if random() > self['suppression']:
      return 1
    return 0
    
  
    
  def LevelHumanFactor(self):
    '''An average of three humand factors'''
    # Internal factors
    internal = self.GetEffectiveness() * ((self['morale'] + self['fatigue'] + self['suppression'])/ 3.0)
    return internal
  
  def LevelCommToHQ(self, mypos):
    '''Factor adjusting the C3 levels due to proximity to higher unit.
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
    L = system_C3.MoraleScale.keys()
    return system_C3.MoraleScale[self.KeyLowerThan(m,L)]
  
  def AsStringFatigue(self, m = None):
    if m == None:
      m = self['fatigue']
    k = system_C3.FatigueScale.keys()
    return system_C3.FatigueScale[self.KeyLowerThan(m,k)]
  
  def AsStringSuppression(self, m = None):
    if m == None:
      m = self['suppression']
    k = system_C3.SuppressionScale.keys()
    return system_C3.SuppressionScale[self.KeyLowerThan(m,k)]
  
  def AsStringCommand(self, m = None):
    if m == None:
      m = self['suppression']
    k = system_C3.CommandScale.keys()
    return system_C3.CommandScale[self.KeyLowerThan(m,k)]
    
  def __float__(self):
    '''
       Returns a bounded value:
         0.0 --> No C3
         1.0 --> Direct and full control
    '''
    # Internal factors
    internal = (self['morale'] + self['fatigue'] + self['suppression'])/ 3.0
      
    return internal
  
  
import unittest
class C3Test(unittest.TestCase):
    def testAsStringMoraleBroken(self):
      C = system_C3()
      self.assertEqual('Broken',C.AsStringMorale(0.01))
      
    def testAsStringMoraleBLACK(self):
      C = system_C3()
      self.assertEqual('BLACK',C.AsStringMorale(0.41))
      
    def testAsStringMoraleRED(self):
      C = system_C3()
      self.assertEqual('RED',C.AsStringMorale(0.61))
      
    def testAsStringMoraleAMBER(self):
      C = system_C3()
      self.assertEqual('AMBER',C.AsStringMorale(0.76))
    
    def testAsStringMoraleGREEN(self):
      C = system_C3()
      self.assertEqual('GREEN',C.AsStringMorale(0.91))
      
if __name__ == "__main__":
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(C3Test))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)  
  