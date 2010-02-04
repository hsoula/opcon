#!/usr/bin/python
'''
    World -- Simulation framerwork for OPCON sandbox
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
if __name__ == '__main__':
  import syspathlib
  import os
  os.chdir('..')
  

# import
from math import log, pi

# Import everything
from sandbox_entity import *
from sandbox_scheduler import sandbox_Scheduler
from sandbox_cryptography import Encrypt
from sandbox_map import sandbox_map
from sandbox_XML import sandboXML
from sandbox_infrastructure import sandbox_network
from sandbox_exception import SandboxException
from sandbox_data import sandbox_data_server

# HTML renderer (for text)
import Renderer_html as html

# Import std python modules
import time as tm
from datetime import *
import os
import os.path
from random import randint
from sandbox_XML import sandboXML

# classes
class sandbox:
  def __init__(self, scenario='blankworld.xml'):
    # compatibility
    self.version = '0.1'
    self.OS = {}
    
    # Initialize all sorts of variables
    # The root node of the order of battle
    self.OOB = []
  
    # The Database daemon
    self.data = sandbox_data_server()
    
    # communication net
    # The communication stack
    self.COMMnets = {}
    
    # Each unit gets it own UID, this is the counter that keeps track of this
    self.next_uid = 1

    # A list of ongoing maneuver battles.
    self.engagements = []
    
    # A register of counter-battery units [ uid , uid, ...] 
    self.counterbattery = []
    self.sead = []
    
    #Strikes counter measures
    self.SEADMisions = []
    self.CounterBtyMissions = []
    self.strikeQueue = []
    
    # Infrastructure
    self.network = sandbox_network()
    
    # Clock
    self.clock = datetime.today()
    self.pulse = timedelta(minutes = 10.0)
    self.lastpulse = datetime.today()
    
    # Scheduler
    self.scheduler = sandbox_Scheduler()
    
    # Sides registration (rgb colors)
    self.sides = {}
    
    # Load the Scenario definition
    self.LoadFromFile(scenario)


  # Interface at the Unit level
  #
  # Informative
  #
  def PointInFootprintOf(self, point):
    '''!
       Return a list of unit having this point within their footprint
       INPUT : point --> a vect_5D
       OUPUT : List of entities
    '''
    out = []
    for i in range(len(self.OOB)):
      if self.OOB[i].PointInFootprint(point):
        out.append(self.OOB[i])
    return out
        
  def UnitsInFootprint(self, entity):
    '''!
       Return everything in footrpint of entity
    '''
    out = []
    for i in range(len(self.OOB)):
      if self.OOB[i] != entity:
        if entity.PointInFootprint(sekf,OOB[i]['position']):
          out.append(self.OOB[i])
    return out
   
  def UnitsInPolygon(self, poly):
    '''!
       Return everything with footprint overlapping a polygon poly
    '''
    out = []
    for i in range(len(self.OOB)):
      if poly.Overlaps(self.OOB[i].Footprint()):
        out.append(self.OOB[i])
    return out
      
  def LOGPACsInFootprint(self, entity):
    '''
       Return the LOGPACs destined to entity if its in the footprint.
    '''
    out = []
    # List of LOGPAC
    for i in self.OOB:
      if i['TOE'] == 'LOGPAC': 
        if i['recipient'] == entity['uid']:
          out.append(i)
          
    # In footprint test
    oout = []
    for i in out:
      if entity.Footprint().PointInside(i['position']):
        oout.append(i)
    return oout
  

  def Visibility(self, pos):
    # By default, returns 4000m.
    return 4.0
  

  # Infrastructure related methods
  # 
  def RelativePositionTo(self, name, bearing, distance):
    '''! \brief Provide the ability to specify position in the simulation that are relative to named positions.
          INPUT:
            name      [string] the name of a node in the network.
            bearing   [*] either a bearing string (see list b below) or an angle in radians
            distance  [float] The distance in km from the node
          OUTPUT:
            A vector instance for the requested position
    '''
    # Get the reference point in the simulator in flat coordinates.
    v = self.GetLocation(name)
    
    if type(bearing) == type(''):
      # Textual bearing are acceptable
      b = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

      if bearing in b:
        bearing = b.index(bearing) * (2*pi / 16.0)
      else:
        raise SandboxException('InvalidTextualBearing',[name,bearing,distance])
    
    # Solve vector with such bearing
    return v.ToBearing([bearing, distance])
    
    
    
  def GetLocation(self, name):
    '''! \brief Return the location as a vector designated by name in the format specified by output.
    '''
    node = self.network.GetNode(name)
    if node:
      if node.Coordinates():
        name = node.Coordinates()
      else:
        raise SandboxException('InfrastructureNodeLookupError', name)
    
    # Is it a coordinate?
    v = self.map.MGRS.AsVect(name)
    
    if v:
      return v
    
    raise SandboxException('LocationLookupError', name)
  
  def GetArea(self, name, infrastructure = ''):
    '''! \brief Retrieve the area covered by the name. If infrastructure is provided, will limit area to infrastructure named as such.
          If the infrastructure exists, but has no footprint, return the node's area instead to avoid errors.
    '''
    node = self.network.GetNode(name)
    if not node:
      raise SandboxException('InfrastructureNodeLookupError', name)
    # return the area of the node.
    if not infrastructure:
      return node.AsArea()
    else:
      for i in node.Infrastructures():
        if i.name == infrastructure:
          if i.footprint:
            return i.footprint
          else:
            raise SandboxException('InfrastructureAreaLookupError', (name, infrastructure))
          
      return node.AsArea()
  
  
  # Create/Remove Units in world
  #
  def AddEntity(self, entity):
    '''!
       Add an entity and connect it properly to the simulator
    '''
    # Add to the list
    self.OOB.append(entity)
    
    # Open the net
    self.COMMnets[entity.GetInnerCOMMnet()] = [entity]
    
    # Friction vectors
    if entity['movement']['mode']:
      entity.SetFrictions(self.map.frictions)
    
    # connect to the simulator (needed to dynamically create other entity)
    entity.sim = self
    entity['agent'].map = self.map
    entity['uid'] = self.next_uid
    self.next_uid = self.next_uid + 1
    
    # Generate a footprint
    entity.SetFootprint(entity['combat'].GetFootprint(entity))
    
    # Get some variables setup
    entity.NewPulse(self.clock)
    entity['last pulse'] = self.clock + timedelta(seconds=0)
    
    # Make folder
    self.fileNewEntity(entity)  
    
  def RemoveEntity(self, entity):
    '''!
       Remove entity
    '''
    # write final log entries
    entity.fileAppendLogs()
    
    # Disconnect HQ
    if entity.GetHQ():
      entity.GetHQ().DeleteSubordinate(entity)
      
    # Disconnect subordinates
    if entity['subordinates']:
      for i in entity['subordinates']:
        # TODO alternate HQ?
        i['HQ'] = None
        
    # Delete all contacts in OOB for entity
    self.OOB.remove(entity)
    for unit in self.OOB:
      # Contacts
      unit.DeleteContact(entity)
      # Staff queue
      toremove = []
      for comm in unit['staff queue']:
        if comm.sender == entity['uid']:
          toremove.append(comm)
      for i in toremove:
        unit['staff queue'].remove(i)
          
    # Delete the entity at last
    del entity
      

  def MakeConvoy(self):
    '''
       Make a generic convoy. TODO: right now, this is just a pair of HMVEEs (placeholder)
    '''
    return sandbox_entity(template='US-light-scout-section', sim=self)

  def MakeLOGPAC(self):
    '''
      Create a generic supply LOGPAC
    '''
    out = sandbox_entity(template='LOGPAC', sim=self)
    
    out['OPORD'] = OPORD(out,out)
    out['OPORD']['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['minimum'] = 0.01
    
    return out
  


  # Unit Access by pointer, UID and name
  #
  def AsUID(self, unit):
    if type(unit) != type(12):
      return unit['uid']
    return unit
  
  def AsEntity(self, uid):
    ''' Return ta pointer regardless of whether uid is a pointer or an integer.
    '''
    if type(uid) == type(sandbox_entity()):
      return uid
        
    # Look for the correct unit in the master OOB
    for i in range(len(self.OOB)):
      if self.OOB[i]['uid'] == uid:
        return self.OOB[i]
      
    # All else failed, return none.
    return None  

  def GetEntity(self, side, name):
    ''' Fetch an entity by side and name '''
    for i in range(len(self.OOB)):
      j = self.OOB[i]
      if j['side'] == side and j.GetName() == name:
        return self.OOB[i]
    return None
  
  def GetOOB(self, color=None, top_level =False):
    '''! \brief Return the OOB 
         \param color filter OOB for a given side.
         \param top_level Provide only the units that have no HQs.
    '''
    if not color and not top_level:
      return self.OOB
    
    out = []
    for i in self.OOB:
      if color and i['side'] == color or (not color):
        if top_level and i.GetHQ() == None or (not top_level):
          out.append(i)
    return out
  # Interface at the Umpire level  
  #
  # Informative
  
          
        
  

  

    
  # Time and simulation related methods
  #  
  def SimulateScheduled(self, delta_time = timedelta(hours = 1.0)):
    '''!
       Implementation based on Scheduler instead of fixed pulses.
    '''
    # terminate batch simulation 
    endtime = self.clock + delta_time
    ptime = self.lastpulse + self.pulse
    
    # Layout the turn cycle
    while ptime <= endtime:
      self.scheduler.PostEvent(ptime,self,self.PhaseNewPulse)
      self.scheduler.PostEvent(ptime,self,self.PhaseEngagements)
      self.scheduler.PostEvent(ptime,self,self.PhaseStepAll)
      self.scheduler.PostEvent(ptime,self,self.PhaseDetection)
      self.scheduler.PostEvent(ptime,self,self.PhaseRegroup)
      self.scheduler.PostEvent(ptime,self,self.PhaseSTAFFWORK)
      self.scheduler.PostEvent(ptime,self,self.fileWriteAllLogs)
      self.scheduler.PostEvent(ptime,self,self.PhaseRemoveUnits)
      ptime = ptime + self.pulse
      
    # Set last pulse for the next Simulate call
    if ptime != endtime:
      self.lastpulse = ptime - self.pulse
    else:
      self.lastpulse = ptime
      
    # Process all events until endtime
    nextime = self.scheduler.NextEventTimeStamp(self.clock)
    while nextime and nextime <= endtime:
      # Update the clock
      self.clock = copy(nextime)
      # Execute the queue
      for ev in self.scheduler.EventList(self.clock):
        ev.Execute()
        
      # Delete the old scheduler events
      self.scheduler.ShredUpTo(self.clock)
      
      # Fetch the next time stamp
      nextime = self.scheduler.NextEventTimeStamp(self.clock)
    
  def Simulate(self, delta_time = timedelta(hours = 1.0)):
    '''
       Run the simulation
    '''
    # Set duration of batch simulation to a time delta object
    if type(delta_time) != type(timedelta()):
      delta_time = timedelta(hours=delta_time)
    
    # Perform the Scheduler's task
    self.SimulateScheduled(delta_time)
    
    # Save to file
    return self.Save()
  def Pulse(self):
    # Return pulse time in hours
    return (self.pulse.seconds / 3600.0)
        

    
  def GetClock(self):
    return self.clock
  ## World information
  #
  def GetAtmosphericEffects(self, position):
    ''' Will eventually read the weather area and time of day.
    '''
    return ['light']
  
  def LineOfSight(self, A, B):
    ''' Returns whether there is a line of sight between A and B.
        Right now, depend entirely on the visibility.
    '''
    # Get the average visibility for A and B
    vis = (self.Visibility(A) + self.Visibility(B)) / 2.0
    
    # Get the distance.
    distance = (A-B).length()
    
    if vis >= distance:
      return True
    
    return False
    
  # Broadcast and Signals
  #
  def BroadcastSignal(self, signal, net):
    '''
       Post signal so it becomes available for interception by listeners.
    '''
    # Adds the comm to each unit tuned to the net
    for i in self.COMMnets.get(net, []):
      i['staff queue'].append(signal)
      
    # Writes the communication to the net
    side = net[:net.find('.')]
    name = net[net.find('.')+1:]
    E = self.GetEntity(side, name)
    signal['sent timestamp'] = self.clock
    filename = os.path.join(self.OS['savepath'], E['side'], E.GetName(True), 'net', signal.ArchiveName())
    
    # Write a text version 
    fout = open(filename, 'w')
    text = html.HTMLfile('COMM on net %s'%(net),signal.AsHTML())
    fout.write(text)
    fout.close()
    
  # Engagement Interface
  #
  def BroadcastStrike(self, strike):
    '''! \brief Notify the sim that a strike is launched
    
        Determine is the strike is detected by SEAD or counter Batteries.
        \todo implement COunter-batteries
    '''
    # Strike position
    pos = self.AsEntity(strike.sender).Position().AsVect()
    
    # Apply strike to target
    E_tgt = self.AsEntity(strike.target)
    if E_tgt:
      E_tgt.InflictDammage(strike.GetRCP(), strike.DammageDistribution(E_tgt['TOE']))
      
    # Counter-battery fire -- Find candidate firers
    CB_units = self.CounterBatteryOnPosition(pos, strike.delivery)
    
    # Add prosecute tag to all CB units
    for i in CB_units:
      i['OPORD'].GetCurrentTask().Prosecute(strike.sender)
      i['OPORD'].GetCurrentTask().Step(i)
    
  def CounterBatteryOnPosition(self, pos, delivery = 'artillery'):
    '''! \brief return a list of units ordered to counter strike.
    '''
    if 'shell missile'.find(delivery) != -1:
      temp = self.counterbattery
    elif delivery == 'AD':
      temp = self.SEADMisions
      
    for i in temp:
      E = self.AsEntity(i)
      tk = E['OPORD'].GetCurrentSubtask()
      if tk:
        if 'CFFZ' in tk:
          area = E['agent'].SolveArea( tk['CFFZ'] )
          if area.PointInside(pos):
            out.append(E)
          
    return out
    
  def EngagementBegin(self, A, B):
    '''
    '''
    # make sure it doesn't already exist
    for i in self.engagements:
      if i.UnitsIn([A,B]):
        return
    
    self.engagements.append(engagement(A,B))
    return self.engagements[-1]
    
  def EngagementEnd(self, E):
    '''
    '''
    # remove and exits
    self.engagements.remove(E)
  

  def EngagementFetch(self, A, B = None):
    '''
       OUTPUT : Engagement involving both A against B or None
    '''
    e = self.engagements
    if B != None:
      for i in range(len(e)):
        if e[i].UnitsIn([A,B]):
          return e[i]
      return None
    else:
      out = []
      for i in range(len(e)):
        if e[i].UnitIn(A):
          out.append(e[i])
      return out
      
  

  # Phases       
  def PhaseSTAFFWORK(self):
    '''!
       Make sure that all units in OOB are processing their OPORDs.
       #- Recompute all Echelon's footprint
       #- Write situation.
    '''
    # Delete all Echelon footprint
    for i in self.OOB:
      i['agent'].PulseStaffwork()
  
  def PhaseRessuply(self):
    '''! Unplanned resupply
    '''
    for i in self.OOB:
      # List LOGPACs in unit's footprint
      LOGPACs = self.LOGPACsInFootprint(i)
      # Ask Staff to consider thes LOGPAC(s)
      i['agent'].SolveRessuplyFromLOGPACs(LOGPACs)
      
  def PhaseStepAll(self):
    '''
       Implement a step move for all units
    '''
    for i in self.OOB:
      i.Step(self.map, self.clock, self.Pulse())
      i.ExpendPulseSupply()
      
    # Re-define the echelon footprints.  
    for i in self.GetOOB(top_level=True):
      i.EchelonFootprint(True)
      
  def PhaseStrikeResolution(self):
    '''! \brief Resolve all counter-measures (SEAD and Counter Bty) then implement strikes.
    '''
    # Create all 
    for i in self.strikeQueue:
      i.sender = self.AsEntity(i.sender)
      i.target = self.AsEntity(i.target)
      if i.delivery == 'air':
        # Find whether any of the SEAD mission can be fired up
        pass
  

  def PhaseNewPulse(self):
    for i in self.OOB:
        i.NewPulse(self.clock)
        
    # Flush the communication stack
    self.commstack = []
    
    #Strikes counter measures
    self.SEADMisions = []
    self.CounterBtyMissions = []
        
  def PhaseDetection(self):
    '''
       Perform detection on all units against all units
    '''
    # Detector
    A = 0
    B = 0
    while A < len(self.OOB):
      B = 0
      # reset this list before starting again
      self.OOB[A]['agent'].potentialengagements = []
      
      while B < len(self.OOB):
        # Suppression
        if self.OOB[A].IsSuppressed() or B == A:
          B = B + 1
          continue
        # Detection Routine
        self.OOB[A].Detection(self.OOB[B])
        B = B + 1 
      A = A + 1
      
      
  def PhaseEngagements(self):
    '''
       Solve all engagements steps.
       Step 1: Begin engagements if in footprints
              End engagements if no longer in footprints
       Step 2: Step over all engagements (resolve casualities)
    '''
    # Initiate if necessary
    for i in self.OOB:
      i['agent'].SolveInitiateEngagement()
      
    # Step over all active engagements.
    for i in self.engagements:
      i.Step(self.Pulse())
      
      
  def PhaseRegroup(self):
      for i in self.OOB:
        i.StepRegroup()
        
  def PhaseRemoveUnits(self):
      mydel = []
      for i in range(len(self.OOB)):
        if self.OOB[i].has_key('delete me'):
          mydel.append(self.OOB[i])
          
      for i in mydel:
        self.RemoveEntity(i)
  

  # 
  # Private methods
  #
  def LoadNetwork(self, fname):
    '''! \brief Load network infrastructure from the map XML file.
    '''
    if self.network == None:
      self.network = sandbox_network()
    try:
      doc = sandboXML(read=fname)
      self.network.LoadFromXML(doc)
    except:
      pass
      
    return self.network
  
  #
  # Files and OS ops
  def Save(self):
    ''' 
       Write itself as a XML file in the simulation's folder
    '''
    # define the file name to write to
    current = os.path.join(self.OS['savepath'],'current.xml')
    archive = os.path.join(self.OS['savepath'],'Autosave','%s.xml'%(self.GetClock().strftime('%H%MZ.%d%b%y')))
    
    # Get the XML string for it.
    out = self.ToXML()
    
    with open(current,'w') as cf:
      cf.write(out)
      
    with open(archive,'w') as af:
      af.write(out)
    
    
  def PrePickle(self):
    # Disconnect Map
    self.map.PrePickle()
    # Disconnect agents
    for i in self.OOB:
      i.PrePickle()
    # Disconnect Engagements
    for i in self.engagements:
      i.PrePickle()
    # Scheduler
    self.scheduler.PrePickle()
    
  def PostPickle(self):
    # Regenerate the data
    self.map.PostPickle()
    # Reconnect agents
    for i in self.OOB:
      i.PostPickle(self)
    # Reconnect Engagements
    for i in self.engagements:
      i.PostPickle(self)
    # Scheduler
    self.scheduler.PostPickle(self)
    if not self.map.data.has_key('climate'):
      self.map.data['climate'] = 'temperate'
      self.SaveMap()
  def ForkWorld(self, newname):
    '''
       Create a new folder to save the current world into.
    '''
    # Delete if newname isn't new
    temp = os.path.join(os.getcwd(),'Simulations',newname)
    self.DeleteFolder(temp)
    
    # Create base folder structure
    self.fileStructure(newname)
    
    # Add a folder for each unit
    for i in self.OOB:
      self.fileNewEntity(i)
      
    # Save the world into a new arcive
    self.Save()
  
  def SaveMap(self):
    fname = os.path.join(os.getcwd(),'maps', self.map.data['package'],'main.xml')
    fout.write(str(self.map.AsXML()))
    fout.close()
    
  def fileWriteAllLogs(self):
    for i in self.OOB:
      i.fileAppendLogs()
      
  def fileStructure(self, savegame):
    '''
    '''
    if not savegame:
      return None
    self.OS['gametag'] = savegame
    self.OS['savepath'] = os.path.join(os.getcwd(),'Simulations',savegame.replace(' ','_'))
    # Test to create the folder
    try:
      self.DeleteFolder(self.OS['savepath'])
      #os.removedirs(self.OS['savepath'])
    except:
      pass
    try:
      os.mkdir(self.OS['savepath'])
    except:
      pass
  
    try:
      # Blue
      for color in ['BLUE','RED']:
        os.mkdir(os.path.join(self.OS['savepath'],color))
        for tp in ['LOGPAC','convoy']:
          os.mkdir(os.path.join(self.OS['savepath'],color,tp))
    except:
      pass
    try:
      os.mkdir(os.path.join(self.OS['savepath'],'Autosave'))
    except:
      pass

    
  def DeleteFolder(self, folder):
    for root, dirs, files in os.walk(folder):
        if root != folder:
          continue
        for name in files:
          os.remove(os.path.join(root, name))
        for name in dirs:
          self.DeleteFolder(os.path.join(root,name))
    os.rmdir(folder)

    
  def fileNewEntity(self, entity):
    # Create the folder for this unit
    # safe file name
    tname = entity.GetName(filenamesafe=True)
    # Special folders for convoys and LOGPAC
    if entity['TOE'] == 'convoy' or entity['TOE'] == 'LOGPAC':
      entity['folder'] = os.path.join(self.OS['savepath'],entity['side'].upper(),entity['TOE'],tname)
    # All other units are in the base folder
    else:
      entity['folder'] = os.path.join(self.OS['savepath'],entity['side'].upper(),tname)

    try:
      # Unit's folder
      os.mkdir(entity['folder'])
      
      # COMM network
      os.mkdir(os.path.join(entity['folder'],'COMMnet'))
      
    except:
      print 'failure to create folder for %s'%(entity['folder'])   
      

  def LoadFromFile(self, filename):
    ''' Load a scenario and execute the command in the XML, if any. 
    '''
    # Determine whether it is a scenario or a savegame.
    if filename.endswith('.xml'):
      # This should be read from the scenario folder
      fname = os.path.join('.','scenarios',filename)
      if not os.path.exists(fname):
        raise SandboxException('ScenarioNotFound', filename)
      
      # Read from XML
      # Load the Scenario definition
      xml = sandboXML(read=fname)
      self.fromXML(xml, xml.root)

      # Create a folder structure
      pass
    
      return True
    
    else:
      # Opens and existing scenario for which there should be a folder.
      fname = os.path.join('.','Simulations', filename.replace(' ', '_'))
      if not os.path.exists(fname):
        raise SandboxException('SaveGameNotFound', filename)
      
      # Find the most recent savegame
      fname = os.path.join('.',fname, 'current.xml')
      if not os.path.exists(fname):
        raise SandboxException('SaveGameFileNotFound', fname)
      
      # Load the file
      xml = sandboXML(read=fname)
      self.fromXML(xml, xml.root)
      
      # Ensure that all COC pointers are valid
      pass
    
      return True
    
      
  def fromXML(self, doc, scenario):
    '''! \brief Either parse a XML scenario document at the scenario node level.
    '''
    # Name and file system
    self.OS['gametag'] = doc.Get(scenario,'name')
    self.OS['savepath'] = os.path.join(os.getcwd(),'Simulations',self.OS['gametag'].replace(' ','_'))
    if doc.Get(scenario,'reset'):
      self.fileStructure(self.OS['gametag'])
    
    # Set clock
    self.clock = doc.Get(scenario, 'clock')
    self.lastpulse = doc.Get(scenario, 'clock')
    
    # Map
    x = doc.Get(scenario,'map')
    self.map = sandbox_map(x)
    
    # Infrastructure to load
    inf = doc.Get(scenario,'infrastructures')
    if inf:
      self.serializeinfrastructure = True
      # Make a Copy of this node to the savegame
      if not os.path.exists(self.OS['savegame'],'infrastructure.xml'):
        fout = open(os.path.exists(self.OS['savegame'],'infrastructure.xml'),'w')
        fout.write('<?xml version="1.0"?>\n')
        fout.write(doc.WriteNode(inf))
        fout.close()
      
      # Read the data
      if doc.Get(inf,'default') == 1:
        # Load the map definition infrastructure
        if os.access(self.map.infrastructurefile,os.F_OK):
          self.network.LoadFromXML(sandboXML(read=self.map.infrastructurefile))
        else:
          raise 'DefaultInfrastructureNotFound'
        
      for n in doc.Get(inf, 'network', True):
        # Case of import network nodes
        if doc.Get(n,'import'):
          fname = os.path.join(os.getcwd(),'scenario',doc.Get(n,'import'))
          if not fname.endswith('.xml'):
            fname += '.xml'
          if os.access(fname,os.F_OK):
            self.network.LoadFromXML(sandboXML(fname))
        else:
          # Directly load node into infrastructure
          self.network.LoadFromXML(doc, n)
          
    else:
      # Load the map definition infrastructure
      if os.access(self.map.infrastructurefile,os.F_OK):
        self.network.LoadFromXML(sandboXML(read=self.map.infrastructurefile))
      else:
        raise 'DefaultInfrastructureNotFound'
      
    # Load sides and OOB
    for side in doc.Get(scenario, 'side', True):
      self.LoadSide(doc, side)

    # Check for an execute node
    exe = doc.Get(scenario, 'execute')
    if exe:
      for cmd in doc.Get(exe, 'cmd', True):
        # A list of command
        methodname = doc.Get(cmd, 'method')
        # If the method exists, call it right away.
        if hasattr(self, methodname):
          getattr(self, methodname)()
        else:
          raise SandboxException('ExecuteScenarioError',methodname)
      
      
        
  def LoadSide(self, doc, node):
    '''! \brief Load a side and all associated information into the simulator.
    '''
    # Color name
    self.sides[doc.Get(node,'name').upper()] = doc.Get(node,'color')
    
    # OOB 
    oob = doc.Get(node,'OOB')
    # Make sure that there is a OOB node in the side node
    if oob != '':
      for unit in doc.Get(oob,'unit', True):
        # CASE 1: The unit must be imported
        if doc.Get(unit, 'import'):
          name = doc.Get(unit, 'import').replace('/','.')
          # Form a correct path
          path = os.path.join(self.OS['savepath'], doc.Get(node,'name'), name, 'current.xml')
          # Read in the unit's description
          if os.path.exists(path):
            udoc = sandboXML(read=path)
            x = udoc.Get(udoc.root, 'unit')
            # Look for a template definition
            x = sandbox_entity(sim=self,template=udoc.Get(x,'template'))
            del udoc
          else:
            raise SandboxException('UnitDescriptionNotFound',path)
        
        # CASE 2: The units must be loaded from this file
        else:
          # Add Side information
          doc.AddField('side', doc.Get(node,'name').upper(), unit)
          # Build unit from template
          x = sandbox_entity(sim=self,template=doc.Get(unit,'template'))
    
        # Read in the state data
        x.fromXML(doc, unit)
  
        # Add to world
        self.AddEntity(x)
      
  def ToXML(self):
    '''! Return a XML version of the simulator
    '''
    # House keeping data
    doc = sandboXML('scenario')
    doc.root.setAttribute('simulator','sandbox')
    doc.root.setAttribute('version', self.version)

    # Identifiers
    doc.AddField('name',self.OS['gametag'],doc.root)
    
    # Map
    doc.AddField('map',self.map.mapenv, doc.root)
    
    # Clock
    doc.AddNode(doc.DateTime('clock',self.clock))
    
    # Infrastructure
    if hasattr(self, 'serializeinfrastructure'):
      infra = doc.NewNode('infrastructures')
      imprt = doc.NewNode('network')
      doc.SetAttribute('import', 'infrastructure.xml',imprt)
      doc.AddNode(imprt, infra)
      doc.AddNode(infra, doc.root)
    
    # sides
    for side_name in self.sides.keys():
      # Create side node and add a few pieces of information
      side = doc.NewNode('side')
      doc.AddField('name',side_name,side)
      doc.AddField('color',self.sides[side_name],side,type='RGB')
      # Write the OOB
      oob = doc.NewNode('OOB')
      for unit in self.GetOOB(color=side_name):
        # Create a link in the Scenario definition
        unode = doc.NewNode('unit')
        doc.SetAttribute('import', unit.GetName(),unode)
        doc.AddNode(unode,oob)
        # Triggers the writing of the unit's state
        path = os.path.join(self.OS['savepath'],side_name,unit.GetName(True),'current.xml')
        unitdoc = sandboXML('sandbox')
        unitdoc.AddNode(unit.toXML(unitdoc),unitdoc.root)
        with open(path,'w') as fout:
          fout.write(str(unitdoc))
        
        
      doc.AddNode(oob, side)
      
      # Add to the main document
      doc.AddNode(side, doc.root)
      
    
    
    return str(doc)


  
import unittest
class SandboxMain(unittest.TestCase):
  def setUp(self):
    pass
  #
  
  def testLoadScenarioSimple(self):
    try:
      self.box = sandbox()
      self.assertTrue(True)
    except:
      self.assertTrue(False)
    
    
if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(SandboxMain))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)
