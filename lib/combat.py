
import syspathsys

from math import log

from vector import vect_3D
import sandbox_geometry as geom
import intelligence

import Renderer_html as html

import system_base

class system_combat(system_base.system_base):
  ''' This model is overhauled so profoundly that I will duplicate the class instead of overwriting the code.
  
      This module deal with the abstracted tactical situation.
  '''
  # Constructor and operators
  # In meters
  frontages = {'':1000.0, 'Team':10.0, 'Sqd':30.0, 'Sec':30.0, 'Plt':100.0, 'Coy':300.0,'Bn':1000.0}
  def __init__(self, skill_level='untrained'):
    # Training level
    self.skillmap = {}
    
    # The default training level for the unit to do everything that is not mapped.
    self.unit_skill = skill_level
    
  def fromXML(self, doc, node):
    ''' Read the data from a XML document
    '''
    # Read in the default training level
    x = doc.Get(node, 'training_level')
    if x:
      self.unit_skill = x
    
    # Read in specific tasks
    x = doc.Get(node, 'training_levels')
    if x:
      for action in doc.Get(x, 'action', True):
        name = doc.Get(action, 'name')
        level = doc.Get(action)
        self.skillmap[name] = level
    
  # Accessor methods.
  def GetSkill(self, skillname):
    ''' Returns the skill level for a given skill, or the unit's default.
    '''
    return self.skillmap.get(skillname, self.unit_skill)
  
  def GetWeaponSystems(self, E, wpn_range=None, max_range=False):
    '''
        Returns a list of weapon systems for entity E.
        Option: wpn_range: The range in meters which must be included in the effective
                           range of the weapon system.
        Returns, a dictionary indexed by the weapon system and containing the number of items in E.
    '''
    # The out put list, which will be a list of net count and systems
    out = []
    
    # The personel-born weapons, counted only if the unit is dismounted
    if E.IsDismounted():
      for personel in E.personel:
        cnt = E.personel[personel].GetCount()
        wpn_list = E.personel[personel].GetKit().GetWeapons()
        for i in wpn_list:
          cntw = cnt * i.GetAllowance('personel')
          out.append( [cntw, i] )

    # The vehicle-born weapons, should be consitional to be crewed.
    for vehicle in E.vehicle:
      cnt = E.vehicle[vehicle].GetCount()
      wpn_list = E.vehicle[vehicle].GetKit().GetWeapons()
      for i in wpn_list:
        cntw = cnt * i.GetAllowance('vehicle')
        out.append( [cntw, i] )
    
    # Performs the filtering #######################################
    filtered_out = []
    for i in out:
      addme = True
      # Fetch the weapon
      wpn = i[1]
      
      # Range Filter 
      if wpn_range != None:
        if max_range:
          mr = wpn.GetMaxRange()
        else:
          mr = wpn.GetEffectiveRange()
        if wpn_range < wpn.GetMinRange() or wpn_range > mr:
          addme = False
          
      # Add only if it didn't fail all tests
      if addme:
        filtered_out.append(i)
      
      
    
    # Out you go
    return filtered_out
  

  def GetRCP(self, E, area=True, wpn_range=None, max_range=False):
    ''' Returns the Expected number of critical hits per hour.
    '''
    # Weapon's list
    wpns = self.GetWeaponSystems(E,wpn_range,max_range)
    
    # Sum up the E-values
    Eval = 0.0
    for w in wpns:
      # Eval for w
      ev = 0
      if area:
        ev += w[1].payload['base'].RCParea
      else:
        ev += w[1].payload['base'].RCPpoint
        
      # Weapon count times the Eval
      Eval += w[0] * ev
    
    # Return the total
    return Eval
    
  # Controler methods
  def GetFootprint(self, E):
    ''' Returns the footprint of E
    '''
    return geom.circle(E.Position().AsVect(),self.GetFrontage(E['size']))
    
  def GetFrontage(self, unit_size):
    ''' Returns a frontage (or radius) as a function of the units size '''
    return system_combat.frontages.get(unit_size, '')
    
  
  def GetExpectedKillsPerMinute(self, E):
    ''' Process the raw expected kills per minute for entity E.
        Sum over all weapon_system for all personel (dismounted) and vehicles. 
    '''
    pass
  
  # Modeling
  def terrain_rcp(self,terrain):
    if terrain == 'unrestricted':
      out = 1.0
    elif terrain == 'restricted':
      out = 1.10
    elif terrain == 'severely restricted':
      out = 1.25
    elif terrain == 'urban':
      out = 1.5
    else:
      out = 1.0
    return out
  
  def terrain_stance_rcp(self, terrain, stance):
    out = self.terrain_rcp(terrain)
      
    if stance == 'deployed' or stance == 'withdrawal' or stance == 'security' or stance == 'offense':
      return out
    elif stance == 'transit':
      return out * 0.5
    elif stance == 'hasty defense':
      return out * 1.15
    elif stance == 'deliberate defense':
      return out * 1.25
    elif stance == 'retreat':
      return out * 0.75
    
  # Refactoring placeholder, these must be removed eventually
  def RawRCP(self):
    raise
  
class old_system_combat(system_base.system_base):
  # default attrition level per hour
  attrition_level = 0.5
  def __init__(self, RCP = 1.0, stance = 'deliberate defense', footprint = 1.0, minrange = 0.0, maxrange = 0.0):
    system_base.system_base.__init__(self)
    self.SetRCP(RCP)
    
    # These are states and shouldn't be in the model
    self['stance'] = stance
    self['readiness'] = 1.0 # min time in hour to redeploy 
    self['footprint'] = footprint
    
    # These are weapon system dependent and are not hard variables anymore.
    self['minrange'] = minrange
    self['maxrange'] = maxrange
    
  def SetRCP(self, RCP):
    self['RCP'] = RCP
    self['RCP loss'] = 0.0
    self['TOE RCP'] = RCP
  def fromXML(self, doc, node):
    # RCP issues
    n = doc.Get(node, 'RCP')
    if n:
      temp = doc.Get(n)
      if temp:
        self['RCP'] = temp
      temp = doc.Get(n,'TOE')
      if temp:
        self['TOE RCP'] = temp
      temp = doc.Get(n, 'recoverable')
      if temp:
        self['RCP loss'] = temp
    # Stance
    if doc.Get(node,'stance'):
      self['stance'] = doc.Get(node, 'stance')
      
    # Readiness
    if doc.Get(node,'readiness'):
      self['readiness'] = doc.Get(node, 'readiness')
      
    # Readiness
    if doc.Get(node,'radius'):
      self['footprint'] = doc.Get(node, 'radius')
      
    # Indirect Fire
    if doc.Get(node,'indirectFire'):
      IF = doc.Get(node,'indirectFire')
      temp = doc.Get(IF,'RCP')
      if temp:
        self['IF RCP'] = temp
      temp = doc.Get(IF,'minrange')
      if temp:
        self['minrange'] = temp
      temp = doc.Get(IF,'maxrange')
      if temp:
        self['maxrange'] = temp
    self['readiness'] = doc.Get(node, 'readiness')
    
  #
  # Interface
  def IFRCP(self):
    '''! \brief returns the Indirect Fire RCP
    '''
    if 'IF RCP' in self:
      return self['IF RCP']
    return 0.0
  def IFranges(self):
    '''! \brief Returns the ranges for indirect fire. Return None otherwise.
    '''
    return [self['minrange'], self['maxrange']]
   
  def GetFootprint(self, E):
    # Generate a circular footprint based on the radius
    return geom.circle(E.Position().AsVect(),self['footprint'])
  
  def AlterUnderwayTime(self, val): #del
    '''
       change the underway time by val. Bounded at the min by 0h of course.
    '''
    self['readiness'] = max(self['readiness'] + val,0.0)
    
  def InflictDestruction(self, dmg):
    if self['RCP']-dmg > 0.0:
      out = dmg
    else:
      out = self['RCP']
    
    self['RCP'] = max(0.0, self['RCP']-dmg)
    
    return out
      
    
  def InflictCasualties(self, dmg):
    if self['RCP']-dmg > 0.0:
      out = dmg
    else:
      out = self['RCP']
    
    self['RCP loss'] = self['RCP loss'] + out
    self['RCP'] = max(0.0, self['RCP']-out)
    
    return out
    
    
  def FootprintRadius(self, stance = None):
    if stance == None:
      stance = self['stance']
      
    # return a radius
    footprint = self['footprint']
    
    if stance.find('defense') != -1:
      return footprint * 1.25
    elif stance == 'transit':
      return footprint * 0.75
    else:
      return footprint
    
  
  def RCP(self, command = 0.0, terrain = 'unrestricted', stance = 'deployed', supply = 1.0):
    '''
       suppression [0-1.0] : modifier for RCP 
       terrain + stance [string] : modifiers for the RCP
       supply [0-1.0] : levels of ammunition
    '''
    rcp = self['RCP'] * self.logictics_rcp(supply)
    rcp = rcp * (command)**0.5
    rcp = rcp * self.terrain_stance_rcp(terrain, stance)
    
    return rcp
    
  def SetStance(self, stance):
    ''' 
       Does what it claims
    '''
    self['stance'] = stance
  def RawRCP(self):
    return self['RCP']
  def UnavailableRCP(self):
    # Return the RCP loss item (WIA/dammaged)
    return self['RCP loss']
  #
  # models
  def terrain_rcp(self,terrain):
    if terrain == 'unrestricted':
      out = 1.0
    elif terrain == 'restricted':
      out = 1.10
    elif terrain == 'severely restricted':
      out = 1.25
    elif terrain == 'urban':
      out = 1.5
    else:
      out = 1.0
    return out
  
  def terrain_stance_rcp(self, terrain, stance):
    out = self.terrain_rcp(terrain)
      
    if stance == 'deployed' or stance == 'withdrawal' or stance == 'security' or stance == 'offense':
      return out
    elif stance == 'transit':
      return out * 0.5
    elif stance == 'hasty defense':
      return out * 1.15
    elif stance == 'deliberate defense':
      return out * 1.25
    elif stance == 'retreat':
      return out * 0.75
    
    
  def logictics_rcp(self, supply):
    if supply >= 0.80:
      return 1.0
    elif supply >= 0.75:
      return 0.9
    elif supply >= 0.50:
      return 0.8
    elif supply >= 0.33:
      return 0.6
    elif supply >= 0.25:
      return 0.5
    
    return 0.33
   
'''
   The engagement class is a data structure to handle the conduct of the ground maneuvers
   in a OOP design, wich shields the simulator from the way the battle is conducted. Here is a list
   of the required interface:
   
   ::Add(E) --> Add E to the engagement.
   ::Remove(E) --> Remove E from the engagement.
   ::Step(pulse) --> Simulate the effect of a certain time of engagement.
   ::Report(E) --> Use the agent of E to prepare an engagement's report for the entity E.
   
   The battle process:
   
   Solve for Bombardment (ground) --> Counter-Bty --> Counter-Counter-Bty --> ...
   Solve for Air Strikes --> ADA --> SEAD --> Counter-Bty --> ...
   Solve for CAS --> ADA --> ...
   Agglomerate all ground maneuvering units (+ CAS) into battle formations.
   Implement effect of ground smoke and EW jamming before computing SA.
   Set the C4ILevel based on their shared comm levels and compute an Uber Situational awareness score
   Establish which units are more prone to take fire from ENY (Assaulting, Breaching).
   Implement the effect of strikes and bombardments.
   Implement the effect of ground + CAS maneuvers
   Implement the effect of combat on morale
'''
class sandbox_engagement(dict):
  def __init__(self, A, B):
    # The sim's pointer
    self.sim = None
    # The dictionary of engaged units
    self.OOB = {}
    self.AddEntity(A)
    self.AddEntity(B)
    self['begin time'] = A['agent'].clock
    
    #self.EstablishContact()
    
  def AccumulateDammage(self, E, dX):
    # Keep track for Reporting purpose
    self.OOB[E['uid']]['dammage'] += dX['Casualties']
    self.OOB[E['uid']]['destruction'] += dX['Destruction']  
    
  def ActivityCode(self):
    for i in self.OOB:
      self.sim.AsEntity(i)['activities this pulse'].append('combat')
      
  def _EstablishContact(self, E):
    # Make sure that the entity E has a contact to all units in the engagements
    # And that all have a contact to E likewise
    for i in self.OOB:
      if E['uid'] != i:
        e = self.sim.AsEntity(i)
        # E to i
        self.ForceContact(E,e)
        # i to E
        self.ForceContact(e,E)
   
  def ForceContact(self, E, e):
    # Force a direct contact of e by E
    cnt = E.Contact(e)
    # If the contact doesn't exist
    if cnt == None:
      cnt = intelligence.sandbox_contact(e)
      E['agent'].ContactUpdate(cnt)
    # Force the visual contact
    if not cnt.IsDirectObs():
      sensor = E.GetDirectVisualSensor()
      sensor.Acquire(E, cnt, True)

  
    
    
    
  
  def Ongoing(self):
    '''
       Determine whether the engagement is ongoing
       return True or False
    '''
    # Disengagement Phase
    for utgt in self.OOB.keys():
      keeper = False
      tgt = self.sim.AsEntity(utgt)
      for ueny in self.OOB.keys():
        eny = self.sim.AsEntity(ueny)
        if utgt != ueny:
          self.OOB[utgt]['Take Dammage'] = False
          if eny['agent'].CanEngage(tgt) or tgt['agent'].CanEngage(eny):
            if eny['agent'].CanEngage(tgt):
              self.OOB[utgt]['Take Dammage'] = True
            keeper = True
            break
      if keeper == False:
        self.RemoveEntity(tgt)
        
    # If no maneuvering unit remains, finsish engagements
    if len(self.OOB):
      return True
    return False
    
  def PrePickle(self):
    pass

    
  def PostPickle(self, sim):
    pass
    
  # Sub-processes
  def Bombardments(self):
    # Artillery preparative barrages
    pass
  
  def BomberStrikes(self):
    # High Altitude strikes
    pass
  
  def CAS(self):
    # Solve for contributing Close Air Support
    pass
  
  def ListTargets(self, E):
    '''
       Return a list of targets for unit E (E can engage.)
    '''
    out = []
    for i in self.OOB.keys():
      e = self.sim.AsEntity(i)
      if E['agent'].CanEngage(e):
        out.append(e)
    return out
  
  def ListActiveENY(self,E):
    # Lif of all ENY that can engage or be engaged.
    out = []
    for i in self.OOB.keys():
      e = self.sim.AsEntity(i)
      addme = False
      # E can Engage
      if E['agent'].CanEngage(e):
        addme = True
      # E can be engaged and is observed by E
      if addme == False:  
        cnt = E['agent'].GetContact(e)
        if cnt != None:
          if e['agent'].CanEngage(E) and cnt.IsDirectObs():
            addme = True
      if addme:
        out.append(e)
    return out
    
  def SituationalAwareness(self, E):
    # Prepare the two vectors of units and send to the entity

    eny = []
    fr = []
    for i in self.OOB.keys():
      e = self.sim.AsEntity(i)
      if e == E:
        continue
      # Get contact
      cnt = E['agent'].GetContact(e)
      if cnt != None:
        if cnt.GetField('side') != E['side']:
          eny.append(e)
        else:
          fr.append(e)
    
    return vect_3D(E.SituationalAwareness(eny),E.SituationalAwareness(fr))
  

  # 
  # Interface
  def AddEntity(self, E):
    self.sim = E.sim
    # Add the entity to the OOB dictionary
    temp = {}
    temp['initial RCP'] = E['combat'].RawRCP()
    temp['initial morale'] = E.GetMorale()
    temp['dammage'] = 0.0
    temp['destruction'] = 0.0
    self.OOB[E['uid']] = temp
    
    # Establish contact to all units in the engagement
    self._EstablishContact(E)
    
    # Append to log
    E['ground engagements'].append(self)
    E['agent'].log('Engaging while in %s'%(E.GetStance()),'operations')
    

    
  def RemoveEntity(self, E):
    # Most simple implementation here...

    # Log event
    E['agent'].log('Engagement has interupted.','operations')
    E['ground engagements'].remove(self)
    del self.OOB[E['uid']]
    
  def Report(self, E):
    '''
       Prepare an engagenement report from E's perpective.
    '''
    # The out string
    out = ''
    
    # The agent of the unit preparing the report
    A = E['agent']
    
    # ENY involved
    enylist = self.ListTargets(E)
    if len(enylist) == 1:
      enycnt = A.GetContact(enylist[0])
      out += 'We are engaged to %s since %s. ' %(html.italic(enycnt.TrackName()), self['begin time'].strftime('%H%MZ(%d%b%y)')) 
    else:
      out += 'We are engaged to multiple units: '
      for i in enylist:
        enycnt = A.GetContact(i)
        if enycnt != None:
          out += '%s (%s), ' %(html.italic(enycnt.TrackName()), self['begin time'].strftime('%H%MZ(%d%b%y)'))
      out = out[:-1] + '. '
        
    
    # Casualties and Fatalities.
    temp = self.OOB[E['uid']]
    if temp['initial RCP'] == E['combat'].RawRCP():
      out += 'The operation is going smoothly, with no casualties for this engagement. '
    else:
      L = E['logistics']
      # relative RCP 
      K = int(temp['destruction']/E.GetRCPperPerson())
      dstV = int(temp['destruction']/E.GetRCPperVehicle())
      W = int(temp['dammage']/E.GetRCPperPerson())
      dmgV = int(temp['dammage']/E.GetRCPperVehicle())
      
      if K or W or dstV or dmgV:
        out += 'In this engagement alone, we have suffered %d KIA/MIA, %d destroyed vehicles, %d WIA and %d dammaged vehicles. '%(K, dstV,W, dmgV)
      else:
        out += 'We are taking fire, but have no casulaties to report for this engagement. '
    
    return html.Tag('p', out)
  
  def Step(self, pulse):
    '''
       Perform a pulse's worth of battle.
       OUTPUT : False if engagement is interrupted
    '''
    # Activity code
    self.ActivityCode()
    
    # Terminate engagement if necessary
    if self.Ongoing() == False:
      # Proceed to terminate the engagement
      self.sim.EngagementEnd(self)
      return False
    
    # Bombardment
    self.Bombardments()
    
    # Bomber Strikes
    self.BomberStrikes()
    
    # CAS
    self.CAS()
    
    # Each unit fires at another
    for i in self.OOB.keys():
      e = self.sim.AsEntity(i)
      # Can act
      if e.IsSuppressed():
        continue
      
      enylist = self.ListTargets(e)
      if enylist == []:
        continue
      eny = e['agent'].SolvePriorityTarget(enylist)
      
      # GetRCP
      RCPus = e.GetRCP()
      RCPthem = eny.GetRCP()
      
      # SA
      SAus = self.SituationalAwareness(e)
      SAthem = self.SituationalAwareness(eny)
      
      # Convert into sigle values
      diff = (SAus - SAthem).length()
      if SAus.length() >= SAthem.length():
        SAus = diff
        SAthem = -diff
      else:
        SAus = -diff
        SAthem = diff
    
      # Adjust RCPs factors going from 0.07 to 13.8 (typically 0.26 to 3.71 unless very successful deception is used.)
      RCPus = RCPus * (10**(SAus-SAthem))
      RCPthem = RCPthem * (10**(SAthem-SAus))
    
      # Attrition pulse in hours.
      attus = RCPthem * system_combat.attrition_level * pulse
      attthem = RCPus * system_combat.attrition_level * pulse
    
      # Implement dammage
      dmgus = e.InflictDammage(attus)
      self.AccumulateDammage(e, dmgus)
      dmgthem = eny.InflictDammage(attthem)
      self.AccumulateDammage(eny, dmgthem)
    
      # Moral 
      if RCPus:
        relDmgus = attus / RCPus
      else:
        relDmgus = 0.0
      if RCPthem:
        relDmgthem = attthem / RCPthem
      else:
        relDmgthem = 0.0
      e.AdjustMorale(relDmgthem - relDmgus)
      eny.AdjustMorale(relDmgus - relDmgthem)

    
    # Consider Withdrawal
    for i in self.OOB.keys():
      e = self.sim.AsEntity(i)
      if e.GetStance() != 'withdrawal' and e['agent'].SolveWithdrawal(self):
        e['agent'].PrepareWithdrawal()

    return True
  

    
  def UnitsIn(self, lst):
    # All units in lst are present
    for i in lst:
      if self.UnitIn(i) == False:
        return False
    return True
  
  def UnitIn(self, other):
    if other['uid'] in self.OOB.keys():
      return True
    return False
    
    
import unittest
class EngagementTest(unittest.TestCase):
    def setUp(self):
      pass
if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(EngagementTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)