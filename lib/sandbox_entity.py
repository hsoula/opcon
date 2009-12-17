'''
    Entity class -- Basic moving part in the battlefield
    OPCON Sandbox -- Extensible Operational level military simulation.
    Copyright (C) 2007 Christian Blouin

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 2 as published by
    the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
'''
if __name__ == "__main__":
  import syspathlib

# import  models
from logistics import system_logistics as logistics
from movement import system_movement as movement
from intelligence import system_intelligence as intelligence
from intelligence import sandbox_contact
from combat import system_combat as combat
from combat import sandbox_engagement as engagement
from C3 import system_C3 as C3

#import modules
from sandbox_comm import *
from sandbox_agent import *
from sandbox_map import *
from sandbox_log import *
from sandbox_scheduler import *
from sandbox_position import *
from sandbox_sensor import *
from sandbox_geometry import geometry_rubberband
import sandbox_keywords


from vector import *
from GUIMapSym import MapSym

from datetime import datetime

# function


# classes

'''
   The entity, or unit, is the item that the simulator is going to manipulate. 
   Components:
      systems:
           combat -- resolve engagements
           movement -- model movement from high-level OPORD
           C3 -- Human factors and command and control models
           logistics -- The management of logistics
           intelligence -- The detection and management of situational awareness
           
           agent -- The main interface of the entity:
                    The agent accept new OPORDs, do some planning work and make sure that the entity
                    is meeting the OPORD. Once an OPORD is received, it determine whether the 
                    COA must be executed or put on hold.
           
           position -- The coordinates, bearing and speed vector of the units
           
           
''' 
class sandbox_entity(dict):
  def __init__(self, name = '', command_echelon = 'Team', side = 'Blue', template=None, sim = None):    
    # Pointer to Simulator (non-templated)
    self.sim = sim
    
    # identity (non-templated)
    self['name'] = name
    self['side'] = side
    
    # Command echelon level
    self['command_echelon'] = command_echelon
    
    # Actual unit size
    self['size'] = 'Team'
      
    # TOE (Get rid of TOE as public variable)
    self.template = template
    self['TOE'] = ''
    self.personel = {}
    self.vehicle = {}
    self['sensors'] = []
    
    # Logistics
    self.cargo = supply_package()
    self.mounted_dismount = 0
    
    
    # Agents
    self['agent'] = agent(self)
    self.agentData = {}
    self['log'] = sandbox_log()
    self['staff queue'] = []
    self['OPORD'] = OPORD(self,self)
    self['SOP'] = SOPstd[side]
    
    # Location, heading, speed and disposition (non-templated)
    self.SetPosition( position_descriptor() ) #vect_5D()
    self['stance'] = 'deployed'
    self['dismounted'] = True
    self['readiness'] = 0.0
    
    # Blank models (In case the templates are incomplete)
    self.SetModelCombat(combat())
    self.SetModelIntelligence(intelligence())
    self.SetModelC3(C3())
    self.SetModelLogistics(logistics())
    self.SetModelMovement(movement())
    
    # Misc internal stuff
    self['ground engagements'] = []
    self['activities this pulse'] = []
    self['last pulse'] = None
    
    # Overiding Icon symbol
    self['icon'] = {}
    self['icon']['IFF'] = 'FR'
    self['icon']['type'] = MapSym[self['TOE']][1]
    self['icon']['char'] = MapSym[self['TOE']][0]
     
    # template information
    self.sim.data.FetchData(self, 'unit', self.template)

  def __getattr__(self, name):
    '''! \brief Attempt direct access to the models.
    
         Should curtail on the wasteful wrapper function in this class. 
         This should beat having the entity being a top-level class for the entity as an
         alternative solution.
         
         A special attention must be paid if there is a attribute name clash.
    '''
    # Models to scan for
    models = ['C3','combat','intelligence','logistics','movement']
    
    for M in models:
      if hasattr(self[M], name):
        return getattr(self[M], name)
      
    # All else fail  
    raise AttributeError, name
  
  # Setting models
  def SetModelCombat(self, M):
    self['combat'] = M
    self['position'].footprint = self['combat'].GetFootprint(self)
    
  def SetModelMovement(self, M):
    self['movement'] = M  
    
  def SetModelLogistics(self, M):
    self['logistics'] = M
    try:
      self['logistics']['initRCP'] = self['combat']['RCP']
    except:
      pass
    
  def SetModelC3(self, M):
    self['C3'] = M
    
  def SetModelIntelligence(self, M):
    self['intelligence'] = M
    # Initialize Sensor
    self['intelligence'].InitializeSensors(self)
    
    # 
      
  # Bookkeeping
  #
  def NewPulse(self, ctime):
    '''! Initialize for a new pulse '''
    # Adjust the stafftoom's clock
    self['agent'].clock = ctime
    # Clear the activity codes
    self['activities this pulse'] = []
    

  
  # Steps
  def Step(self, Map, clock, pulse):
    '''
       Generic Step function.
    '''
    # Update the clock for the agent -- Redundant, but what the hell.
    self['agent'].clock = clock
    
    # Unit without an OPORD do nothing
    if self['OPORD'] == {}:
      self['agent'].log('We have no OPORD today.','operations')
      return
  
    # Suppresion because of unclear OPORDs -- Suppression may be duplicated somewhere else. If so, it makes the suppression more burdensome.
    if self['OPORD'].IsSuppressed():
      self['agent'].log("Confusion with HQ incurs delays!",'operations')
      return
    
    # Get current maneuver task -- Fancy recursive method call which digs the active subtask of a task.
    mytask = self['OPORD'].GetCurrentTask()
    if mytask:
      if mytask.CanBegin(self.sim.clock,self['OPORD'].GetHhour()):
        mytask.Step(self)
    elif self['TOE'] != 'LOGPAC':
      # Weird, don't remmber why this is here -- CHECKOUT
      self['agent'].sustaintask.Step(self)
  
  def StepINTEL(self):
    '''! \brief  Decides whether and how to send INTSUM and INTREP
        \TODO Get Agent to decide whether it should be done instead of having this built-in the fn call
        
        Called by agent in the Staffwork phase.
    '''
    # Prepare Insum
    self['agent'].PrepareINTSUM()
    
    # Decide whether a SITREP should be sent.
    if self['agent'].PolicySendSITREP():
      self['agent'].PrepareSITREP()
  
  def StepRegroup(self):
    '''! \brief Implement a Regroup iteration.
        # Wraps the C3 model regroup routine.
        # Log a message
        # Adjust fatigue penalty
    '''
    s,f = self['C3'].Regroup(self.C2Level())
    if s > 0.01:
      self['agent'].log('Recovering suppression by %.2f to %.2f.'%(s,self['C3']['suppression']),'operations')
    
    # Lack of supply
    dailyload = self['logistics'].ProjectSupply(activity_dict = self['logistics']['basic load'], E=self)
    deficit  = self['logistics']['cargo'].IgnoreDeficit()
    if deficit:
      ratio = deficit / dailyload
      dmg = sum(ratio.values())
      self['agent'].log('Taking Fatigue due to a supply shortage.','personel')
      self['C3'].AdjustFatigue(dmg)
    
  # C3
  def CommonHigherEchelon(self, other):
    #! \brief Return the lowest common echelon to self and other
    
    # Simplest case, self is parent to other
    if other in self['C3'].AllSubordinates():
      return self
    
    # Recusive ascent
    hq = self.GetHQ()
    if hq:
      return hq.CommonHigherEchelon(other)
    
    # All else fail
    return None
  
  def ChainOfCommandTo(self, other):
    '''! \brief  Returns a list of unit in the chain of communication.
    '''
    # Am the end of chain
    if self == other:
      return [self]
    
    # Any of the subordinates
    for sub in self['C3']['subordinates']:
      if other == sub:
        # Shortcut
        return [self,sub]
      # Should we descend?
      for subsub in sub['C3'].AllSubordinates():
        if subsub == other:
          temp = sub.ChainOfCommandTo(other)
          if temp != [None]:
            return [self] + temp
          else:
            return [None]
      
    # Not a subordinates, go up a level and try again
    if self.GetHQ():
      temp = self.GetHQ().ChainOfCommandTo(other)
      if temp != [None]:
        return [self] + temp
      else:
        return [None]
    
    # All else fail
    return [None]
      
  def CommLevelTo(self, other):
    '''!
       Returns a Probability of obtaining a contact with a certain unit over many relaying stations.
       An abstraction of the lateral movement of communication and a measure of cooperability.
    '''
    mychain = self.ChainOfCommandTo(other)
    # No chain
    if mychain == [None]:
      return 0.0
    # Compute chain as the product of all C3 levels
    out = 1.0
    for i in mychain:
      out = out * i.C3Level()
    return out
    
  def C2Level(self):
    '''! Command and control'''
    return min( 1.0, self['C3'].LevelHumanFactor() * self['C3'].LevelDeployState(self['combat']['stance']))
  
  def C3Level(self):
    '''! Command, control and communication. Distance to HQ factored in.'''
    return min( 1.0, self.C2Level() * self['C3'].LevelCommToHQ(self['position']))
  def AddSubordinate(self, subord):
    '''!
       Will work only if subord is already connected to self. To connect, use the ReportToHQ() methods called from the subordinates, which will
       call this method.
       Return True otherwise
    '''
    if subord.GetHQ() != self:
      return False
    
    if subord not in self['C3']['subordinates']:
      self['C3']['subordinates'].append(subord)
      
    
  def DetachFromHQ(self):
    '''! \brief Detach from OPCON and resume with the echelon's HQ.
    
         Will happen only if there is an original HQ that is set in the C3 dictionary.
         
         \todo Fall back to alternate HQ if original HQ doesn't exist anymore.
    '''
    if self['C3']['OPCON']:
      self['C3']['OPCON'].DeleteSubordinate(self)
      self['C3']['OPCON'] = None
      
    # Remove from the detached list
    if self.GetHQ():
      hq = self.GetHQ()
      if hq['C3'].has_key('detached'):
        if self['uid'] in hq['C3']['detached']:
          hq['C3']['detached'].remove(self['uid'])
    
  
 
  def AttachToHQ(self, HQ):
    '''! \brief Report to HQ as OPCON attachment (keep original echelon)
    '''
    # Step 1 - Avoid circular connection
    if HQ == self:
      self['agent'].log("Can't subordinate to itself.",'personel')
      return False
      
    # Cannot subordinate to a subordinate (prevent loops in chain of command)
    if HQ in self['C3'].AllSubordinates():
      self['agent'].log("Can't subordinate to a lower echelon.",'personel')
      return False  
    
    # Disconnect self from current OPCON
    if self['C3']['OPCON'] != None:
      # Disconnect from direct control.
      self['C3']['OPCON'].DeleteSubordinate(self)
     
    # Set OPCON
    self['C3']['OPCON'] = HQ
    
    # List as detached
    hqc3 = self['C3']['HQ']['C3']
    if not hqc3.has_key('detached'):
      hqc3['detached'] = []
    
    if not self['uid'] in hqc3['detached']:
      hqc3['detached'].append(self['uid'])
      
    
    # Get the HQ to connect 
    if HQ:
      HQ.AddSubordinate(self)
      
  def ReportToHQ(self, HQ):
    '''! \brief Report to a HQ and setup the echelon
      
         Use this method to make the entity an organic component of the HQ's echelon. 
         Alternatively, use this function call to return an entity to its TOE HQ.
    '''
    # Step 1 - Avoid circular connection
    if HQ == self:
      self['agent'].log("Can't subordinate to itself.",'personel')
      return False
      
    # Cannot subordinate to a subordinate (prevent loops in chain of command)
    if HQ in self['C3'].AllSubordinates():
      self['agent'].log("Can't subordinate to a lower echelon.")
      return False  
    
    # Disconnect self from current HQ
    if self['C3']['HQ'] != None and HQ != self['C3']['HQ']:
      self['C3']['HQ'].DeleteSubordinate(self)

    # Connect to the new HQ
    self['C3']['HQ'] = HQ
    
    # Get the HQ to connect 
    if HQ:
      HQ.AddSubordinate(self)
    
      # Set the Echelon
      #self['C3']['echelon'] = HQ.Echelon()
    
    
  def IssueOrder(self, order):
    '''!
       Pass an order to an entity. The entity will dispatch it to the appropriate agent.
       Record the C3 comand level at the time of issue.
    '''
    if self.GetHQ():
      order['C3 level'] = float(self.GetHQ()['C3'])
      
    self['staff queue'].append(order)
    
  def Send(self, request, subord = None):
    '''!
       Send a request to the Higher Unit or subordinate
    '''
    request['C3 level'] = self.C3Level()
    
    # Magic teleport into subordinate
    if subord in self['C3']['subordinates']:
      subord['staff queue'].append(request)
      
    # Magic teleport into higher echelon.
    elif self.GetHQ():
      self.GetHQ()['staff queue'].append(request)
      
    # Broadcast signal (all assumed to be radio) - will be used for SIGINT routine at some point down the road.
    if self.sim:
      self.sim.BroadcastSignal(request)
    
  def GetHQ(self):
    '''! \brief Get HQ, real of OPCON. 
         Unnecessary wrapper, delete.
    '''
    return self['C3'].GetHQ()
  
  def GetSubordinates(self):
    return self['C3']['subordinates']
  
  def GetSiblingUnits(self):
    '''
       Returns direct subordinates of the HQ, but not self.
    '''
    myHQ = self.GetHQ()
    out = []
    if myHQ:
      for i in myHQ.GetSubordinates():
        if i != self:
          out.append(i)
    return out
        
  def GetLastSITREP(self, subord, echelon=True):
    '''!
       Return the last SITREP received from uid
    '''
    if type(subord) != type(12):
      subord = subord['uid']
      
    if self['C3']['SITREP'].has_key(subord):
      return self['C3']['SITREP'][subord]
    
    if subord == self['uid']:
      return self['agent'].PrepareSITREP(echelon)
    return None
  
  # Echelon code
  def DeleteEchelonFootprint(self):
    '''! \brief Remove the footprint from the C3 model so it can be recomputed.
    '''
    if self['C3'].has_key('Echelon Footprint'):
      del self['C3']['Echelon Footprint']
      
  def EchelonFootprint(self, force= False):
    '''! \brief return the footprint for the entire echelon.
         If there is no echelon, return the ordinary footprint.
         If there is no Echelon Footprint, but an echelon, compute it recursively.
         
         To get the percieved footprint, ask agent_CO.SolveFootprint()
    '''
    # Echelon Test
    if self.Echelon() and self.Subordinates():
      if self['C3'].has_key('Echelon Footprint') and not force:
        return self['C3']['Echelon Footprint']
      else:
        V = self.Footprint().vertices()
        for i in self.Subordinates():
           V += i.EchelonFootprint(force).vertices()
        
        self['C3']['Echelon Footprint'] = geometry_rubberband().Solve(V)
        return self['C3']['Echelon Footprint']
      
    return self.Footprint()
  
  def Echelon(self):
    '''! \brief Access Echelon.
    
        An echelon is the name of the formation for which the entity is the HQ.
    '''
    return self['C3']['echelon']
  
  def HigherEchelon(self):
    '''! \brief Return the formation name of the higher Echelon
    '''
    if self.GetHQ():
      return self.GetHQ().Echelon()
    else:
      return ''
  

      
    
  
  # Intelligence  
  def Detection(self, other):
    '''!
       Handle all the detection and classification as called by the simulator
    '''
    if other.has_key('delete me'):
      return
    
    # fetch the contact
    contact = self['intelligence'].Contact(other)
    if contact == None:
      contact = sandbox_contact(other)
      
    # Acquisition
    for i in self['sensors']:
      i.Acquire(self, contact)

  
  def GetDirectVisualSensor(self):
    # find the sensor
    for i in xrange(len(self['sensors'])):
      if isinstance(self['sensors'][i], SensorVisual):
        return self['sensors'][i]
    return None
  # Combat
  def GetStance(self):
    return self['combat']['stance']
  def GetRCPperPerson(self):
      return self['logistics']['initRCP'] / float(self['logistics']['Np'])
  def GetRCPperVehicle(self):
      return self['logistics']['initRCP'] / float(self['logistics']['Nv'])
  def Footprint(self):
    return self['position'].footprint
  def Position(self):
    return self['position']
  
  def SetPosition(self, pos):
    '''! pos can either be a vector or a position descriptor '''
    if not 'position' in self:
      self['position'] = position_descriptor()
    if isinstance(pos, position_descriptor):
      self['position'] = pos
    elif isinstance(pos, vect_3D):
      self['position'].Set(pos)   
    
  
  def SetFootprint(self, fp):
    '''
       Must layer to the entoty to make sure that the AoI for the direct visual IS the new 
       fp.
    '''
    # find the direct visual sensor
    dv = None
    for i in range(len(self['sensors'])):
      if self['sensors'][i].direct:
        dv = self['sensors'][i]
        
    self['position'].SetFootprint(fp)
    if dv:
      dv.AoI = self.Footprint()
        
  def PointInFootprint(self, point):
    # Geometric implementation (replacing the circle assumption from the original design)
    return self.Position().footprint.PointInside(point)
  
  def Signature(self):
    return self['intelligence'].Signature(self['combat']['stance'])
  def GetRCP(self, noterrain = False):
    if self.sim and not noterrain:
      return self['combat'].RCP(self.C2Level(),self.sim.map.TerrainUnder(self['position']),self['combat']['stance'],self['logistics'].CombatSupplyLevel())
    else:
      return self['combat'].RCP(self.C2Level(),'unrestricted',self['combat']['stance'],self['logistics'].CombatSupplyLevel())
  
  
  def InflictDammage(self, dmg, modvector = [1.,0.33333,0.166667]):
    '''!
       Implement the dmg units of dammage
       \param dmg The RCP value to inflict
       \param modvector The modifier vector for [suppression, dammage, destruction] 
    '''
    if self.GetRCP() == 0.0:
      return {'suppress':0.0,'Casualties':0.0, 'Destruction':0.0}
    
    # Terrain dammage reduction # TODO Average
    if self.sim:
      mod = self['combat'].terrain_rcp(self.sim.map.TerrainUnder(self['position']))
      dmg = dmg / mod
    
    # Break down dmg
    dv = []
    for i in modvector:
      dv.append(i*dmg)
    
    # Suppression In proportion to RCP
    sup = dv[0] / self.GetRCP()
    self['C3'].Suppress(sup)
    sup = min(1.0,sup)
    
    # Casulaties
    dmc = self['combat'].InflictCasualties(dv[1])

    # Destruction
    dmd = self['combat'].InflictDestruction(dv[2])
    
    self['agent'].log('Suppression: %.2f , Casualties: %.2f , Destruction: %.2f , RCP : %.2f'%(sup,dmc,dmd, self['combat']['RCP']),'personel')
    return {'suppress':sup,'Casualties':dmc, 'Destruction':dmd}
  
  # Movement
  # Logistics
  def GetCargo(self):
    ''' Return the state of the cargo for this unit.
    '''
    return self.cargo
  
  def CanLoad(self, other):
    '''! \brief confirms whether a unit Other can be loaded.
         \todo consider net weight for loading
    '''
    if other['TOE'] == 'LOGPAC':
      return True
    return False
  
  def AdjustSupply(self, val):
    ''' Adjust the quantity of supply to an unit by the package val.'''
    self.cargo = self.cargo + val
    self.cargo.ConvertGeneric()
    
  def ExpendPulseSupply(self, pulse = None):
    '''!
         Expand supply for a impulse
    '''
    if pulse == None:
      if self.sim:
        pulse = self.sim.Pulse()
      else:
        return
    
    # Alternative implementation
    cost = self['logistics'].SupplyExpenditure(1,self['activities this pulse']+['idle'], pulse, self)
    self.AdjustSupply(-1.0 * cost)
  
  # Files
  def fromXML(self, doc, node):
    # Read templates and data from XML to populate the data fields.
    # Name
    x = doc.Get(node,'identity')
    if x:
      self['name'] = x
      
    # Size
    x = doc.Get(node,'size')
    if x:
      self['size'] = x
      
    # Command echelon
    x = doc.Get(node,'command_echelon')
    if x:
      self['command_echelon'] = x
      
    # Combat stance
    x = doc.Get(node, 'stance')
    if x:
      self['stance'] = x
      
    # Dismount 
    x = doc.Get(node, 'dismounted')
    if x:
      self['stance'] = bool(x)
      
    # Systems
    models = doc.Get(node,'models')
    for i in ['C3','combat','intelligence','movement','logistics']:
      x = doc.Get(models,i)
      if doc.Get(x,'template'):
        self.sim.data.FetchData(self[i],i,doc.Get(x,'template'))
      else:
        self.sim.data.FetchData(self[i],i,'base')
      # Read the node itself
      self[i].fromXML(doc,x)
      
    # Systems and components
    x = doc.Get(node, 'TOE')
    if x:
      z = doc.Get(x,'category')
      if z:
        self['TOE'] = z

      # Personel
      z = doc.Get(x,'personel', True)
      for it in z:
        kit = doc.Get(it,'template')
        count = doc.Get(it,'count')
        self.personel[kit] = {'kit':self.sim.data.Get('personel',kit),'count':count}
        
      # vehicle
      z = doc.Get(x,'vehicle', True)
      for it in z:
        kit = doc.Get(it,'template')
        count = doc.Get(it,'count')
        self.vehicle[kit] = {'kit':self.sim.data.Get('vehicle',kit),'count':count}      
      self['movement'].SetVehicles(self.vehicle.values())
      
  def fileAppendLogs(self):
    fout = open(os.path.join(self['folder'],'logs.txt'),'a')
    self['log'].fileUpdate(fout)
    fout.close()
    
  def PrePickle(self):
    # No world, skip
    if self.sim == None:
      return False
    #disconnect the agent, for some reasons
    self['agent'].PrePickle()
    # OPORD
    self['OPORD'].PrePickle()
    # C3 pointers
    self['C3'].PrePickle(self.sim)
    # Contacts
    for i in self['intelligence']['contacts'].keys():
        self['intelligence']['contacts'][i].unit =  self.sim.AsUID(self['intelligence']['contacts'][i].unit)
        # remove undetected with p_right == 0.5
        if self['intelligence']['contacts'][i].Type() == 'undetected' and abs(self['intelligence']['contacts'][i].p_right - 0.5) <= 0.01:
          del self['intelligence']['contacts'][i]

    self.sim = None
    
    return True
        
    
  def PostPickle(self, sim):
    self.sim = sim
    self['agent'].PostPickle(self)
    # C3 Pointers
    self['C3'].PostPickle(self.sim)
    # contacts
    for i in self['intelligence']['contacts'].keys():
        self['intelligence']['contacts'][i].unit =  self.sim.AsEntity(self['intelligence']['contacts'][i].unit)
    # OPORD
    self['OPORD'].PostPickle(self.sim)

    
  

import unittest

class EntityTest(unittest.TestCase):
  def testBaseUnit(self):
    unit = sandbox_entity('defaultname','Bde','HQ')
    self.assertFalse(False)
  def testWrongEchelonLabel(self):
    unit = sandbox_entity('defaultname','bogus','HQ')
    self.assertFalse(unit['command_echelon']=='bogus')
  def testWrongTOELabel(self):
    unit = sandbox_entity('defaultname','Bde','bogus')
    self.assertFalse(unit['TOE']=='bogus')

  def testPickleWithoutWorld(self):
    unit = sandbox_entity('defaultname','Bde','HQ')
    self.assertFalse(unit.PrePickle())
  def testSendNoWorld(self):
    unit = sandbox_entity('defaultname','Bde','HQ')
    self.assertFalse(unit.Send({}))
  def testGetRCPNoworld(self):
    unit = sandbox_entity('defaultname','Bde','HQ')
    self.assert_(unit.GetRCP())
  def testInflicatDamageNoWorld(self):
    unit = sandbox_entity('defaultname','Bde','HQ')
    self.assert_(unit.InflictDammage(1.0))

  def testExpendPulseSupplyNoPulseNoWorld(self):
    unit = sandbox_entity('defaultname','Bde','HQ')
    self.assertEqual(unit.ExpendPulseSupply(), None)
    
  def testLenChainOfCommand(self):
    a = sandbox_entity()
    b = sandbox_entity()
    c = sandbox_entity()
    
    a.ReportToHQ(b)
    c.ReportToHQ(b)
    
    self.assertEqual(len(a.ChainOfCommandTo(c)),3)
  def testLenNoChainOfCommand(self):
    a = sandbox_entity(name = 'a')
    b = sandbox_entity(name = 'hq')
    c = sandbox_entity(name = 'c')
    d = sandbox_entity(name = 'd')
    
    a.ReportToHQ(b)
    c.ReportToHQ(b)
    
    self.assertEqual(a.ChainOfCommandTo(d),[None])
  def testC2LevelUnsupportedStance(self):
    # Will not matter unless implemented differently
    a = sandbox_entity()
    a['combat'].SetStance('bogus')
    self.assertEqual(a.C2Level(),1.0)
    
  def testNoAddSelfSubord(self):
    a = sandbox_entity()
    self.assertFalse(a.AddSubordinate(a))
    
  def testNoReportToSelf(self):
    a = sandbox_entity()
    a.ReportToHQ(a)
    self.assertEqual(a.GetHQ(),None)
    
if __name__ == "__main__":
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(EntityTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)