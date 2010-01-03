'''
    Tasking module
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

   Task processing, rendering and Stepping functionality.
   This module defines the base task that the entities can perform. It provie an object-oriented 
   abstraction of procedure in a nested/recursive framework. Task specific agent routines should be implemented
   within these classes as to keep the agent baseclass decluttered from specialized code.
'''
from copy import deepcopy, copy

from logistics import supply_package
from Renderer_html import Tag, Table
from random import random, choice


import re
from datetime import timedelta, datetime
from sandbox_graphics import operational_area

# sandbox specifics
import sandbox_comm
import sandbox_geometry
import sandbox_strike
import vector

class sandbox_task(dict):
  '''! \brief Base class with the core function for a task
     
     \param type (\c string) A task identifier set by the inherited classes.
     
     The function of a task is to provide a Step() function for the entity to execute. Other core 
     elements for this class is the Process(), which ensure that self['required supply'] and self['task time']
     are set. These are needed to time the OPORD and compute projected levels of supply over time.
     Another core interface method is this that verbalize the details of the task (AsHTML()) and the 
     other method which formulate the task as an order in the OPORD (OrderHTML()). These core methods are
     likely to have override in derived classes.
     
     Under the new implementation, the task can now contain a list of subtasks which are stored as self.sequence
     and a cursor in self.cursor. The principle is the same as for the OPORD implementation. 
     
     \todo Buil-in the timing as a core method.
  '''
  def __init__(self, type = 'idle'):
    # mandatory fields
    self['type'] = type
    
    # subtasking sequence
    self.sequence = []
    self.cursor = None
    
    # Timing in hour
    self['task time'] = 0.0
    self['completion'] = None
    self['concurent'] = False
    
    # Timeing in datetime
    self['planned begin time'] = None
    self['planned end time'] = None
    self['begin time'] = None
    self['end time'] = None
    self['time conflict'] = False
    
    # Supply related
    self['supply required'] = supply_package()
    self['consumption code'] = ['idle']
    
    # Planning
    self['initial position'] = None
    self['initial readiness'] = None
    self['initial stance'] = None
    
    # Required Data, param are the minimum set of data to be provided to process the task.
    self['parameters'] = []
    
    # A connection to the OPORD
    self['opord'] = None
    
  def CanProcess(self):
    '''! \brief return True if all miminum parameters are present. False otherwise.
    '''
    for i in self['parameters']:
      if not self.has_key(i):
        return False
    
    return True
    
  def MakeConcurent(self):  
    '''! \brief A concurent task is done in parallel with the main phase tasking and 
                doesn't call NextTask() upon completion.         
    '''
    self['concurent'] = True
    
  def __str__(self):
    return 'Task :%s'%(self['type'])
  def AsHTML(self, A):
    '''! Prepare a info string for a SITREP.
         \param A The agent
         \param opord The owning OPORD, assumed to be the active opord otherwise
    '''
    return Tag('p','Task %s is ongoing (Implement a report method!)'%(self['type']))
  
  def Step(self, E):
    '''! \brief Iterate over a pulse of the task.
    
       Ensure that the BeginTask() and EndTask() are called if necessary.
       \param  E [\c sandbox_entity] the owning entity
    '''
    # Is begining?
    if self['begin time'] == None:
      self.BeginTask(E)
      
    # Task specfic routine if not suppressed
    if not E.IsSuppressed():
      if self.GetSubTask() != self:
        self.GetSubTask().Step(E)
      else:
        self._Step(E)
    
    # Is the Sub-task completed? 
    if self.GetSubTask()['completion'] == True:
      # NextSubTask Increment the cursor, if it can't, it calls EndTask()
      self.NextSubTask(E)
      
  def _Step(self, E):
    '''!\brief The overridable core of the Step function'''
    return

  def Process(self, E):
    '''! \brief Initial planning during the processing of orders.
         
       \param  E [\c sandbox_entity] The owning entity
       \return \c list of \c sandbox_task
           
       The prime function of this method is to:
            - Expand into subtasks
            - Set self['required supply'] and self['task time']
            
       Ignore processing if the task is ended or already begun then call _Process()
       
    '''
    # Not bother re-processing a completed task
    if self.IsCompleted() or self['begin time'] != None:
      return 
    
    # Check for minimal params
    if not self.CanProcess():
      return
    
    self.sequence = self._Process(E)
    return self.sequence
  
  def _Process(self, E):
    '''! \brief Overridable protected method '''
    return [self]
  
  def Cancel(self, E):
    '''! \brief forced abortion of the task
    '''
    self['completion'] = True
    self.cursor = None
    # If task already started
    if self['begin time']:
      self.EndTask(E)
  
  
  def ConsumptionCodes(self):
    '''! Get for the tasks consumption code.
         \return self['consumption code']
    '''
    return self['consumption code']
  

  def OrderHTML(self, A):
    '''!
       Prepare an Order string for OPORD/FRAGO
    '''
    return self['type']
  def OrderTimingHTML(self):
    '''!
       Generic instructions about timing.
    '''
    out = ''
    if self.has_key('set begin time') and self['set begin time']:
      # Specify a begin time
      out = out + 'You are to begin no earlier than at %s. '%(self['set begin time'].strftime('%H%M ZULU (%d %b %y)'))
      
    if self.has_key('set begin offset') and self['set begin offset']:
      out = out + 'You are to begin no earlier than at H%s. '%(self['set begin offset'])
      
    return out
  
  def HhourOffset(self):
    '''!Return a deltatime object based on the osset string.
       \return \c datetime OR None if this constraint doesn't exist.
    '''
    if not self.has_key('set begin offset'):
      return None
    
    offset = self['set begin offset']
    
    # Split the units
    pat = re.compile('[+|-][0-9]*')
    index = pat.search(offset)
    if index:
      delta = index.group()
      unit = offset[len(delta):]
      delta = int(delta)
      
      if unit == 'd':
        return timedelta(days=delta)
      elif unit == 'h':
        return timedelta(hours=delta)
      else:
        return timedelta(minutes=delta)
    return None
    
  def GetTriggerCodewords(self):
    '''
       Returns a list of trigger codewords
    '''
    if self.has_key('Trigger Codewords'):
      return self['Trigger Codewords']
    return []
  
  def GetEarliestTime(self, Hhour):
    '''! \brief Find if there is a min time contraint. 
         \return A \c datetime or None
    '''
    if self.has_key('set begin time'):
      return self['set begin time']
    elif Hhour and self.HhourOffset():
      return Hhour + self.HhourOffset()
    return None
  
  def CanBegin(self, ctime, htime):
    '''! Determine whether this task can begin.
    
       \param ctime is the current time.
       \param htime is the Hhour
    '''
    # Case of a set time
    etime = self.GetEarliestTime(htime)
    if etime and ctime < etime:
      return False
    
    # Codewords
    if self.GetTriggerCodewords() and not E['agent'].MatchCodewords(self.GetTriggerCodewords()):
      return False
    
    return True
  def IsCompleted(self):
    if self['end time'] != None:
      return True
    return False
  def PlannedEndTime(self):
    '''! \brief The End time of the last subtask
         \return The datetime instance of the timestamp or None
    '''
    if len(self.sequence):
      return self.sequence[-1]['planned end time']
    return None
    
  def PlannedBeginTime(self):
    '''! \brief The End time of the last subtask
         \return The datetime instance of the timestamp or None
    '''
    if len(self.sequence):
      return self.sequence[0]['planned begin time']   
    return None
  
  def EndTime(self):
    '''! \brief End time of all subtasks'''
    if len(self.sequence):
      return self.sequence[-1]['end time']   
    return None
    
  def BeginTime(self):
    '''! \brief Begin time of all subtasks'''
    if len(self.sequence):
      return self.sequence[0]['begin time']   
    return None
  
  def TimeFromOffset(self, offset, Hhour):
    '''! \brief Give a time from an offset and a hhour
         \param offset (\c string) of the format [+|-][0-9]*[d|h|m]
         \param Hhour (\c datetime) The H-hour from the OPORD
         \return Artificial set begin time
    '''
    # Numerical part
    TD = timedelta()
    if offset.find('d') != -1:
      i = float(offset[:offset.find('d')])
      TD = timedelta(days=i)
    elif offset.find('h') != -1:
      i = float(offset[:offset.find('h')])
      TD = timedelta(hours=i)
    elif offset.find('m') != -1:
      i = float(offset[:offset.find('m')])
      TD = timedelta(minutes=i)
    
    return Hhour + TD
    
    
  def PushPlannedBeginTime(self, T, Hhour = None):
    '''! \brief Propagate the planned timing.
         \param T (\c datetime) The earliest begin time
         \param Hhour The H-hour for the OPORD in case the task is set to an offset of this value
         \return self.PlannedEndTime()
    '''
    
    for i in self.sequence:
      if i == self:
        # Set Begin section
        setBegin = self.GetEarliestTime(Hhour)
        if setBegin != None:
          if setBegin < T:
            # Start ASAP
            setBegin = T + timedelta()
        else:
          # Set the value for the planned begin.
          self['planned begin time'] = copy(T)
          
        if self['task time']:
          self['planned end time'] = self['planned begin time'] + timedelta(hours=self['task time'])
          T = self['planned end time']
      else:
        T = i.PushPlannedBeginTime(T, Hhour)
    return T
      
    
  
  def BeginTask(self, E):
    '''
       Stuff to do to begin the task
    '''
    self['begin time'] = copy(E['agent'].clock)
    self.cursor = 0
    
  def EndTask(self, E):
    '''! \brief Tidying it up in style 
    
         Requires:
         - self.cursor == None
         
         Do:
         - Emit codewords
         - Prepare SITREP
         - Set end time
         - Call OPORD.NextTask() for non-concurent case.
         
    '''
    
    # Do NOT end task unless 
    if self.cursor != None:
      return
    
    # Emit codewords.
    if self.has_key('Emit CODEWORDS'):
      pass
    
    # Prepare SITREP
    if self.has_key('SITREP on completion'):
      E['agent'].PrepareSITREP()
    
    self['end time'] = copy(E['agent'].clock)
    
    # Step forward if part of a tasking queue
    if not self['concurent']:
      E['OPORD'].NextTask(E)
    
  def GetSubTask(self):
    '''! \brief Return the current sub-task.
         
         This function is recursive, it will solve for the deepest task in the subtasking tree.
         \return self if there is no current subtask
    '''
    if len(self.sequence) <= self.cursor:
      # This should not happen
      print "Task of type %s doesn't have a valid cursor [%d]"%(str(self.__class__),self.cursor)
      return self
    
    if self.cursor != None:

      if self.sequence[self.cursor] == self:
        return self
      else:
        # recusive call
        return self.sequence[self.cursor].GetSubTask()
        
    return self
  
  def NextSubTask(self, E):
    '''! \brief Move on to the next substask
    
         Increment the cursor in the task. If it can't, return False and Process the task's EndTask()
         Nested subtasks are calling their own End task so there is no need to do it.
         
        \note Set self.cursor to None when there is no more subtask
       
         \return True if there is a next one, False otherwise.
    '''
    # No cursor, shouldn't happen
    if self.cursor == None:
      self.EndTask(E)
      return False
    
    # Increment cursor unless it pushes the index out of range
    if self.cursor < len(self.sequence) - 1:
      self.cursor += 1
      return True
    else:
      # cursor set to None if the task is done!
      self.cursor = None
    
    # Complete the current task then return False to move on to the next OPORD phase/task
    self.EndTask(E)
    return False
  
  def TaskTime(self):
    '''! \brief compute the time taken by all subtasks
         \return time (\c float) in hours. 
    '''
    out = 0.0
    for i in self.sequence:
      if i['task time']:
        out += i['task time']
      else:
        break
    return out
  
  def SupplyRequired(self):
    '''! \brief Total amount of supply required for all subtasks.
    
         Use this method unless you want to acquire the internal task only.
         
         \return The supplu required (\c supply_package)
    '''
    out = supply_package()
    for i in self.sequence:
      if i['supply required']:
        out = out + i['supply required']
      else:
        break
    return out
  def ExpandedSubtaskList(self):
    '''! \brief Returns a fully expanded subtasks list
         \note Required recursion to perform sandbox_comm.OPORD.GetExpandedTaskList()
    '''
    out = []
    
    for i in self.sequence:
      if i != self:
        out.extend(i.ExpandedSubtaskList())
      else:
        out.append(self)
    return out
  # Convenience routines
  def GetOverlay(self):
    '''! \brief Get the overlay from the OPORD
    '''
    if self['opord']:
      return self['opord'].GetOverlay()
    else:
      return None
    
  def ResolveControlMeasure(self, CM, ovr):
    '''! \brief Does the conversion from marking to vectors.
         \param translator An FlatLand instance
         \param CM the control measure name
         \param opord The overlay
         
         \return a vector or a list of vector
    '''
    # DO nothing if already not a string or there is no overlay
    if type(CM) != type('') or ovr == None:
      return CM
    
    return ovr.GetElement(CM)
    
  
  def SpeedOnSpot(self, E):
    # Compute velocity in Km/h
    delta = E['movement'].Speed(E['agent'].map.TerrainUnder(E['position']), E.C2Level(), E.GetStance())
    
    # Has orders to advance
    delta = delta * E.CanMoveStance()
    if delta == 0.0 or self.Yield(E,delta,E['movement'].Speed(E['agent'].map.TerrainUnder(E['position']), E.C2Level(), E.GetStance())) :
      return 0.0
    
    return delta
    
  def WaypointNavigation(self, E):
    '''! \brief Naviate through waypoints.
    '''
    delta = self.SpeedOnSpot(E)
    
    # Movement suppression
    E.AdjustSuppression(E['movement'].lastNetSuppression)
  
    nwp = len(E['OPORD'].GetCurrentWaypoints()) 
    # Steer the formation
    E['position'], wp = E['agent'].navigate(delta * E.sim.Pulse(), E['position'], E['OPORD'].GetCurrentWaypoints())
    E['OPORD'].SetCurrentWaypoints(wp)
    # 
    nwp = nwp - len(E['OPORD'].GetCurrentWaypoints())
    if nwp:
      E['agent'].log('%d waypoints reached.'%(nwp),'operations')
  
#
# Sustenance
class taskSustain(sandbox_task):
  '''! \brief Maintain and upkeep the entities readiness in idle situation.
  
       Do not call Process in this task, simply call Step()
  '''
  def __init__(self):
    sandbox_task.__init__(self, 'sustain')
    
    self.ressuplytasks = []
    
    self.MakeConcurent()
    
    
  def _Process(self, E):
    '''!
    '''
    return [self]
    
  def _Step(self, E):
    '''! \brief Perform sustenance operations.
         \todo Routine SITREP
         \todo Routine INTSUM
    '''
    # The agent
    A = E['agent']
    
    # Check for the need of routine ressuply.
    A.PrepareRoutineRessuply()
    
    # Attempt to ressuply
    self.Ressuply(E)
    
  def Ressuply(self, E):
    '''! \ brief Ressuply from LOGPACS
        
         This methods does the following, in sequence:
         -# Step through all tasks already in the self.ressuplytasks list
         -# Delete complete tasks in the self.ressuplytasks list
         -# Attempt to begin a new ressuply task (which involves a Step() call) + MakeConcurent()
         -# Add it to ressuply task if valid
         
    '''
    # Case 1 - Step through all current tasks.
    for i in self.ressuplytasks:
      i.Step(E)
      if i.IsCompleted():
        self.ressuplytasks.remove(i)
        # Remove the pending SUPREQ from the agent's data
        for j in E['agent'].issuedSUPREQs:
          E['agent'].issuedSUPREQs.remove(i['SUPREQ'])
        
    # Add new ressuply tasks
    tk = taskRessuply()
    tk.MakeConcurent()
    tk.Process(E)
    tk.Step(E)
    if tk.IsActive():
      # Add to list of ressuply tasks
      self.ressuplytasks.append(tk)

    
    
    # Routine SITREP
  def OrderHTML(self, A):
    return "Maintain readiness on site until further notice."
#
# Maneuvers (Movement)
'''!
   Pertains to the transition between stances and level of readiness.
   \todo Alter the facing of a unit that isn't moving.
'''
class taskRedeploy(sandbox_task):
  def __init__(self):
    sandbox_task.__init__(self,'Redeploy')
    self['consumption code'].extend(['transit'])
    
    # Readiness targets
    self['initial readiness'] = None
    self['final readiness'] = 0.0 # Assumption
    
  def _Process(self, E):
    '''
        Transition to a new stance.
        Task data :
        stance -->          : Initial Stance
        final_stance -->    : Target Stance
        --> displacement    : The notional movement to complete the task
        --> task_time       : An estimate of the time required to complete the task
        --> supply required : Estimate of the supply required
    '''
    A = E['agent']
    A.log('| Plan redeployment from %s to %s.'%(self['initial stance'], self['final_stance']),'operations')
    
    # conceptual displacement as diagonal to bounding / 2.0 (radius)
    bbox = E.Footprint().BoundingBox()
    self['displacement'] = 0.5 * ((bbox[3]-bbox[1])**2 + (bbox[2] - bbox[0])**2)**0.5 
    
    # Encamp time
    self.SolveReadiness(E)
    encamptime = 0.0
    if self['initial readiness'] != None or self['final readiness'] != None:
      if self['initial readiness'] == None:
        self['initial readiness'] = 0.0
      if self['final readiness'] == None:
        self['final readiness'] = 0.0  
      encamptime = abs(self['initial readiness'] - self['final readiness'] )
    
    # Estimate time in pulses to do it.
    speed = E['movement'].Speed(A.map.TerrainUnder(self['initial position']), E.C2Level(), self['initial stance'])
    self['task time'] = (self['displacement']/speed) + encamptime
    A.log('|     Estimated Completion time: %.2f hour.'%(self['task time']),'operations')
    
    # Estimate Logistics cost.
    self['supply required'] = A.EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    A.log('|     Estimated Supply required: %.2f'%(self['supply required']),'operations')
    
    # Because this task doesn't require sub-tasking
    return [self]
  
  def _Step(self, E):
    '''
       Advance the time of redeployment by pulse, subject to suppression.
    '''
    # Is first step?
    # Activity code
    E['activities this pulse'].extend(self.ConsumptionCodes())
    
    # Can move by virtue of logistics
    E['agent'].log('Redeploying...','operations')
    if E.CanMoveLogitics() == 0:
      E['position'].rate = 0.0
      E['agent'].log('Redeployment aborted by supply problems.','operations')
      return
    
    # Supression cancelling the pulse
    if E.IsSuppressed():
      E['agent'].log("Pausing for 10 minutes to regroup.",'personel')
      return
    
    # convert readiness (Abort prematurely if readiness isn't at 0)
    if E['readiness'] != self['final readiness']:
      diff = self['final readiness'] - E['readiness']
      # change underway time
      if diff < 0.0:
        diff = max(diff, -1*E.sim.Pulse())
      else:
        diff = min(diff, E.sim.Pulse())
        
      # Change readiness.
      E['readiness'] += diff
      
      # Ignore small difference
      if abs(E['readiness'] - self['final readiness']) < 0.001:
        E['readiness'] = self['final readiness']
        
      # No redeployment possible for as long as the units can't move
      if E['readiness'] != self['final readiness']:
        return
                                     
    # are there interference with other units
    delta = self.MeanSpeedInFootprint(E)

    # Movement suppression
    E.AdjustSuppression(E['movement'].lastNetSuppression)
    
    
    # Deduce Displacement
    self['displacement'] = self['displacement'] - delta*(E.sim.Pulse())
    
    # Are we done?
    if self['displacement'] <= 0.0:
      # change stance at last
      E.SetStance(self['final_stance'])
      if E['readiness'] < self['final readiness']:
        E['readiness'] = min( E['readiness'] + E.sim.Pulse(), self['final readiness'])
        if E['readiness'] != self['final_stance']:
          return
      E['agent'].log("Fully redeployed to %s at time %s [Planned: %s]"%(self['final_stance'],E['agent'].clock.strftime("(%m-%d)%H%M ZULU"), self.PlannedEndTime().strftime("(%m-%d)%H%M ZULU")),'personel')
      E['agent'].log('Current position MGRS %s'%(E['agent'].map.MGRS.AsString(E['position'])),'operations')
      if E['OPORD'].NextTaskCanBegin(E['agent'].clock):
        self['completion'] = True
  
  def AsHTML(self, A):
    '''
       SITREP format
    '''
    out = 'We are redeploying from a %s to a %s stance. ' %(self['initial stance'],self['final_stance'])
    return Tag('p',out)
  
  def OrderHTML(self, A):
    '''
       As Rendered in OPORD in the HTML format.
    '''
    out = 'Redeploy to a %s stance.'%(Tag('STRONG',self['final_stance']))
    out = out + self.OrderTimingHTML()
    
    return out 
  
  def MeanFriction(self,E):
    '''
       compute the mean friction in the footprint in order to compute the displacement time.
    '''
    # Terrain profile
    terrain = E['agent'].map.SampleTerrain(E.Footprint())
    
    # Mean friction from terrain alone
    out = 0.0
    for i in terrain:
      out = out + E['movement'].friction_terrain(i) * terrain[i]
    
    return out
  
  def MeanSpeedInFootprint(self, E):
    '''
       Returns the mean speed within footprint
       OUPUT : In kph
    '''
    return E['movement'].Speed(self.MeanFriction(E),E.C2Level(),E.GetStance())

  def SolveReadiness(self, E):
    '''!
       Determine the end readiness for different stances
    '''
    if self['final_stance'] == 'Support' or self['final_stance'].find('defense') != -1:
      self['final readiness'] = 1.0
      return
    
    # All other stance require readiness at 0
    self['final readiness'] = 0.0
    
 
  # Setup Fn from GUI
  def SetFinalStance(self, fs):
    self['final_stance'] = fs
    
class taskRelocate(sandbox_task):
  '''! \brief Move from point A to Point B in a given stance and redelploy in a given stance.
  
       \param destination [\c vect_3D]
       \param route [\c list]
       \param stance [\c string]
       \param final_stance [\c stance]
  '''
  def __init__(self):
    sandbox_task.__init__(self,'Relocate')
    self['consumption code'].extend(['transit'])
    
    self['final_stance'] = None
    self['stance'] = None
    
    self['recompute path'] = True
    
    self['parameters'].append('destination')
    #self['parameters'].append('route')
  
  def _Process(self, E):
    '''
            Staffwork to get to a new position. 
            Process task details
    '''
    if self['stance'] == None:
      self['stance'] = self['initial stance']
      
    # Redeploy Before?
    if self['initial stance'] != self['stance']:
      reloc = taskRedeploy()
      reloc['stance'] = self['initial stance']
      reloc['final_stance'] = self['stance']
      reloc['initial position'] = self['initial position']
      self.sequence.extend(reloc.Process(E))
      # Set final stance to the 
      if self['final_stance'] == None:
        self['final_stance'] = reloc['final_stance']
        self['final readiness'] = reloc['final readiness']
    
    # relocate 
    A = E['agent']
    A.log('| Plan Relocate Mission')
    # Solve Path and create waypoints to follow
    self.ComputePath(A)
    
    A.log('|     Estimated Supply required: %.2f'%(self['supply required']))
    self.sequence.append(self)
    
    # Redeploy After?
    if self['stance'] != self['final_stance'] and self['final_stance']:
      reloc = taskRedeploy()
      reloc['stance'] = self['initial stance']
      reloc['final_stance'] = self['stance']
      reloc['initial position'] = self['destination']
      self.sequence.extend(reloc.Process(E))
      # Self endstate after subtasking
      self['final_stance'] = reloc['final_stance']
      self['final readiness'] = reloc['final readiness']
    
    return self.sequence
  
  def ComputePath(self, A):
    A.SolvePath(self)
    self['recompute path'] = False
    # Evaluate time requirements
    self['task time'] = A.EstimateTransitTime(self['waypoints'])
    # Evaluate supply requirements
    self['supply required'] = A.EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    self['recompute path'] = False
  
  def _Step(self, E):
    # Activity code
    E['activities this pulse'].extend(self.ConsumptionCodes())
    
    # Can move by virtue of logistics
    if E.CanMoveLogitics() == 0:
      E['position'].rate = 0.0
      E['agent'].log('Out of petrol, no movement allowed anymore.','logistics')
      return
    
    # Supression cancelling the pulse
    if E.IsSuppressed():
      E['agent'].log("Pausing for 10 minutes to regroup.",'personel')
      return
    
    # Recompute path
    if self['recompute path']:
      self.ComputePath(E['agent'])
    
    # Navigate 
    self.WaypointNavigation(E)
    
    # Check for end of task
    if E['OPORD'].GetCurrentWaypoints() == []:
      E['agent'].log("Plotted movement completed at time %s ( %s )"%(E['agent'].clock.strftime("(%m-%d) %H%M:%S"), E['OPORD'].GetCurrentTask().PlannedEndTime().strftime("(%m-%d) %H%M:%S")),'operations')
      E['agent'].log('Current position MGRS %s'%(E['agent'].map.MGRS.AsString(E['position'])),'operations')
      # Look for next task
      E['OPORD'].GetCurrentTask()['end time'] = E['agent'].clock
      if E['OPORD'].NextTaskCanBegin(E['agent'].clock):
        self['completion'] = True
        #E['OPORD'].NextTask()
      
  def AsHTML(self, A):
    dest = self.ResolveControlMeasure(self['destination'], self.GetOverlay())
    out = 'We are relocating to MGRS %s, some %.1f km from our current position. Our last reported speed was %d kph. '%(A.map.MGRS.AsString(dest,2), (A.entity['position']-dest).length(), A.entity['position'].rate * 6.0)
    out = out + 'We estimate the TOA at %s ZULU. '%(self.PlannedEndTime().strftime('%H%M'))
    return Tag('p',out)

  def OrderHTML(self, A):
    '''
       Destination must be converted to UTM
    '''
    # Write the destination as a string
    if type(self['destination']) != type(''):
      # a vector
      destination = A.map.MGRS.AsString(self['destination'])
    else:
      # was already provided as an overlay marking.
      destination = self['destination']
    out = 'Relocate to location %s'%(destination)
    
    # Stance
    if self['stance']:
      out = out + ' in %s stance. '%(self['stance'])
    else:
      out = out + ". "
      
    # Route (optional)
    if 'route'in self and self['route']:
      out += 'Proceed via '
      if type('') == type(self['route']):
        out += self['route'] + '. '
      else:
        out += 'the waypoint: '
        for i in self['route']:
          out += A.map.MGRS.AsString(i) + ', '
        out = out[:-2] + '. '
    
    # Optional final stance.
    if self.has_key('final_stance') and self['stance'] != self['final_stance']:
      out = out + 'Once on site, redeploy to a %s stance.'%(self['final_stance'])
      
    # Timing options, call the baseclass method
    out = out + self.OrderTimingHTML()
    
    return out 
  def SetStance(self, s):
    self['stance'] = s

  def SetFinalStance(self, s):
    self['final_stance'] = s
  def Yield(self, E, spfr, sp, overlap):
    ''' Simple decision for now, if speed cut in three, and timing isn't a priority over readiness, stop in 33% of the time. '''
    if sp/spfr >= 3:
      prior = E['agent'].PolicyPrioritize(['timing','readiness'])
      if prior and prior[0] == 'readiness':
        if random() < 0.5:
          return True
    return False
  def PosAsVect(self, A, pos):
    '''! \brief Force a position into a vector type.
         \A an agent
         \pos A position
    '''
    pass
  
#
# Maneuver (combat)
class taskOffense(sandbox_task):
  maneuver_types = ['recon by fire', 'assault', 'maximum effort']
  def __init__(self):
    '''
        Planning options
        
        'planned fighting time' = [float] hours (default = 1.0)
        
        'AA' -- Assembly area (point or area)
        ['Axis of Approach'] -- route [line]
        'OA' -- Objective Area
        ['LD time'] -- Launching time
        ['fall back'] -- Area, point
        
        'maneuver' ['recon by fire', 'assault', 'maximum effort']
                     recon by fire --> break off assault with minimal casualties, gain SitAwareness
                     assault --> stop if run low on supply (< 15 min) or 50% of net RCP.
                     maximum effort assault -> advance until the unit breaks.
    '''
    sandbox_task.__init__(self, 'Offense')
    # There is no systematic consumption code, it will depend on the _Step function.
    
    self['Assembly Area'] = ''
    self['Axis of Approach'] = ''
    self['OA'] = ''
    self['LD time'] = None
    self['fall back'] = None
    self['maneuver'] = 'assault'
    
    self['narrative'] = ''
    
    self['initial RCP'] = None
    
  def _Process(self, E):
    '''! \brief Prepare the execution of an assault
    
         #- Determine whether the unit needs to relocate to AA, and redeploy to offense stance.
         #- Determine whether the unit needs to ressuply up to mobility levels. [future]
         #- Set the time of launch. 
         #- Determine the Axis of approach.
         #- Set fall back area.
         #- Establish fall back criterion (supply and RCP)
         #- Estimate task time + supply required.
         #- Plan follow-up emergency ressuply.
    '''
    # LD time from set begin time
    if self['set begin time']:
      self['LD time'] = self['set begin time']
    
    # Make it to AA in offense stancee
    if not self['Assembly Area']:
      self['Assembly Area'] = self['initial position']
      if self['initial stance'] != 'offense':
        redep = taskRedeploy()
        redep['final_stance'] = 'offense'
        redep['initial stance'] = self['initial stance']
        redep['initial position'] = self['initial position']
        redep['initial readiness'] = self['initial readiness']
        self.sequence.extend( redep.Process(E) )
    else:
      # Case of a point, check to see if there is a need to relocate.
      reloc = taskRelocate()
      reloc['destination'] = self['Assembly Area']
      reloc['stance'] = copy('transit')
      reloc['initial position'] = copy(self['initial position'])
      reloc['initial stance'] = self['initial stance']
      reloc['final_stance'] = 'offensive'
      self.sequence.extend(reloc.Process(E))
      
    # Solve an approach
    temp = None
    AA = None
    if type(self['Assembly Area']) == type(''):
      temp = self['initial position']
      AA = E['OPORD'].GetOverlay().GetElement(self['Assembly Area']).Center()
    else:
      AA = self['Assembly Area']
    self['initial position'] = AA
    
    self['route'] = self['Axis of Approach']
    if E['OPORD'].GetOverlay() and E['OPORD'].GetOverlay().GetElement(self['route']):
      self['destination'] = E['OPORD'].GetOverlay().GetElement(self['OA']).Center()
    else:
      self['destination'] = self['OA']
    
    E['agent'].SolvePath(self)
    
    if AA:
      self['initial position'] = temp
      
    # A rough estimate of transit time
    self['task time'] = E['agent'].EstimateTransitTime(self['waypoints'])
    self['supply required'] = E['agent'].EstimateSupplyRequired(['combat'],self['task time'])
    
    # Adding self
    self.sequence.extend([self])
    return self.sequence
    
  def _Step(self, E):
    # Do only once, when the battle begins.
    if self['initial RCP'] == None:
      self['initial RCP'] = E.GetRCP(noterrain = True)
      
    # Reset narative
    self['narrative'] = ''
    
    # Abort Maneuver?
    if self.AbortDecision(E):
      diag = self.AbortDecision(E)
      if self['fall back']:
        tk = {'destination':E['agent'].GetControlMeasure(self['fall back'])}
      else:
        tk = {'destination':E['agent'].GetControlMeasure(self['Assembly Area'])}
      # Solve path and set waypoints for taking off. Find better then AA if none provided.
    
    # Wait for the time to go
    if self['LD time'] == None:
      self['LD time'] = E['agent'].clock
      self['narrative'] = 'Departing from assembly area for the %s toward %s.'%(self['maneuver'],self['OA'])
    if self['LD time']:
      if type(self['LD time']) == type(''):
        begin = self.TimeFromOffset(self['LD time'], E['OPORD'].GetHhour())
      else:
        begin = self['LS time']
      # Wait if not ready
      if E['agent'].clock < begin:
        if not self.has_key('start line'):
          # Log only the first time.
          E['agent'].log('Ready to begin maneuvers @ %s.'% (begin.strftime('%H%M ZULU')),'operations')
          self['narrative'] = 'We are assembled on the AA and awaiting for %s to launch the maneuvers. ' %( begin.strftime('%H%M ZULU') )
          self['start line'] = True
        E['agent'].log(self['narrative'],'operations')
        return None
      
      # Do nothing is paused
      if 'pause' in self:
        self['narrative'] = 'We are on hold on the %s maneuvers. ' %(self['maneuver'])
        E['agent'].log(self['narrative'],'operations')
        return None
      
      # Rush to Objective using transit code from Relocate
      # Navigate 
      if 'waypoints' in self and len(self['waypoints']):
        self.WaypointNavigation(E)
        self['narrative'] = 'We are approaching the OA according to '
        if self['Axis of Approach']:
          self['narrative'] += ' %s. ' %(self['Axis of Approach'])
        else:
          self['narrative'] += 'fastest route. '
        E['agent'].log(self['narrative'],'operations')
        return None
      
      # In position, now clear the OA
      myengagements = E.sim.EngagementFetch( E )
      if myengagements:
        return None
      else:
        # List all ENY to clear off.
        if self['OA'].__class__ == operational_area().__class__:
          UNT = E.sim.UnitsInPolygon(self['OA'])
        else:
          UNT = E.sim.PointInFootprintOf(self['OA'])
          
        # Keep only the ENY
        ENY = []
        for i in UNT:
          cnt = E['agent'].GetContact(i)
          if cnt and cnt.IFF() == 'ENY':
            ENY.append(i)
        
        if len(ENY) > 1:
          self['narrative'] += 'Some %d ennemy formations are occupying the OA. '
          
        # Check for ENY
        if not ENY:
          self['completion'] = True
          self['narrative'] += 'The OA appears to be all clear of ENY opposition. '
          E['agent'].log(self['narrative'],'operations')
          return
        
        # Select One eny to engage.
        ENY = self.SelectENY(ENY)
        
        # Vector to ENY
        V = E.Position() - ENY.Position()
        
        # Actual speed
        speed = self.SpeedOnSpot(E)  * E.sim.Pulse()
        
        P = E.Position()
        P.course = V.course
        P.move = min(V.length(),speed)
        P.Step()
        E.SetPosition(P)
        
  def AbortDecision(self, E):
    # Placeholder for now.
    return False
  def SelectENY(self, ENYlist):
    '''! \brief Return on ENY from the list
    '''
    if ENY:
      return choice(ENY)
    return None
    
  def TimeAsString(self, tm, A):
    # Return if its a string already
    if type(tm) == type(''):
      return tm
    # stringnify if its a datetime
    elif type(tm) == type(datetime.now()):
      return tm.strftime('%a %b %d %Y %H%M ZULU')
    return ''
      
    
  def OrderHTML(self, A):
    out = ''
    if self['LD time'] == None:
      out += 'As soon as possible, '
    else:
      out += 'At %s, '%(self.TimeAsString(self['LD time'],A))
    
    out += 'initiate a %s on %s. ' %(self['maneuver'], self['OA'])
    
    # Assembly area
    if self['Assembly Area'] and not isinstance(self['Assembly Area'], vector.vect_3D):
      out = out[:-2]
      out += ' from the assembly area designated by %s. '%( self['Assembly Area'] )
    
    # Route
    if self['Axis of Approach']:
      out += 'Follow the Axis of approach %s ' %(self['Axis of Approach'])
    else:
      out += 'Follow the fastest route '
    out += 'to the objective until you are engaging opposing formations. '  
    
    # Fall back
    if self['fall back']:
      out += 'If the maneuvers fails and you must withdraw, proceed to %s as a fall back area. ' %( self['fall back'] )
    return out
  
  def AsHTML(self, A):
    out = ''
    if self['LD time'] == None:
      out += 'As soon as possible, '
    else:
      out += 'At %s, '%(self.TimeAsString(self['LD time'],A))
    
    out += 'we initiate a %s on %s. ' %(self['maneuver'], self['OA'])
    
    # Assembly area
    if self['Assembly Area'] and not isinstance(self['Assembly Area'], vector.vect_3D):
      out = out[:-2]
      out += ' from the assembly area designated by %s. '%( self['Assembly Area'] )
    
    # Route
    if self['Axis of Approach']:
      out += 'We then follow the Axis of approach %s ' %(self['Axis of Approach'])
    else:
      out += 'We follow the fastest route '
    out += 'to the objective until we are engaging opposing formations. '  
    
    # Fall back
    if self['fall back']:
      out += 'If the maneuvers fails and we must withdraw, we\'ll proceed to %s as a fall back area. ' %( self['fall back'] )
    return Tag('p',out)
    
    
class taskWithdrawal(sandbox_task):
  '''! \brief Break off all engagements.
  
      This task largely depends on the output of sandbox_agent.SolveWithdrawalHeading() and is thus
      a rather greedy solution to a delicate problem. Much work can be done to improve this task, or 
      create better behaved task classes to acheive a more robust solution.
  '''
  def __init__(self):
    sandbox_task.__init__(self,'withdrawal')
    self['consumption code'].extend(['transit'])
    
  def _Process(self, E):
    self['begin time'] = deepcopy(E['agent'].clock)
    self['task time'] = 0
    self['supply required'] = supply_package()
    E['OPORD'].InsertToCurrentTask(self)
    
    return [self]
  
  def _Step(self, E):
    '''! \brief Impromptu and greedy avoidance of ENY opposition.
    
       Currently, terminates when the engagement is broken off.
       \bug should the transition to withdrawal be a Redeploy task?
       \todo Should we consider FR units to attempt to break off with pursuers?
    '''
    # Activity code
    E['activities this pulse'].extend(self.ConsumptionCodes())
    
    # Evaluate completion
    if E['ground engagements'] == []:
      E['agent'].log('Broke off engagements successfully.','operations')
      self['completion'] = True
      return 
    
    # Adjust threat axis
    b = E['agent'].SolveWithdrawalHeading()
      
    # Change axis
    E['position'].course = b
    
    # Change/Update stance
    E.SetStance('withdrawal')
    
    # Compute velocity in Km/h
    delta = E['movement'].Speed(E['agent'].map.TerrainUnder(E['position']), E.C2Level(), E.GetStance())
    delta = delta * -1.0 * (E.sim.Pulse())
    
    # Do the translation
    E['position'].rate = delta
    E['position'].Step()
    
  def AsHTML(self, A):
    out = 'We are withdrawing.'
    return Tag('p',out)
class taskIndirectFire(sandbox_task):
  '''! \brief Indirect fire mission.
  
       CFFZ    --> Weapon's free zone.
       ammo    --> ammo type [HE, AP, ICM]
       EFST    --> [uid]
       salvoes --> max number of salvoes.
       mission --> Type of mission [DS, CF, SEAD]
       
  '''
  ammo = ['HE', 'AP', 'ICM']
  mission = ['STRIKE', 'DS', 'CF', 'SEAD']
  def __init__(self, srcp = 5.0, ammo = 'HE', mission = 'DS'):
    sandbox_task.__init__(self, 'Indirect Fire')
    self['consumption code'].extend(['combat'])
    
    # Strike RCP
    self['SRCP'] = srcp
    
    # Call for Fire Zone (Cannot fire out ofthis area)
    self['CFFZ'] = '' # Option
    
    # Essentiona Fire Support Task
    self['EFST'] = []
    
    self.SetAmmo(ammo)
    
    self['salvoes'] = None # Option
    
    self.SetMission(mission)
      
    # Last tie fired (avoid multiple targetting on one pulse) 
    self['last fired'] = None
    
    # Counter Bty target
    self['prosecute'] = None
  
  def SetAmmo(self, ammo):
    #! Ammo must be set to one of the preset
    if ammo in taskIndirectFire.ammo:
        self['ammo'] = ammo
    else:
      self['ammo'] = 'HE' 
      
  def SetMission(self, mission):
    #! Mission must be set to one of the preset
    if mission in taskIndirectFire.mission:
        self['mission'] = mission
    else:
      self['mission'] = 'STRIKE'
  def _Process(self, E):
    '''! \brief Register the CCFZ
    '''
    # Default CFFZ if unspecified
    if not self['CFFZ']:
      self['CFFZ'] = sandbox_geometry.circle(E.Position().AsVect(), E['combat']['maxrange'])
      # WARNING -- Within minzone will count as CFFZ, but the Salvoe will not go!
      
    # Register to sim (an efficiency trick only)
    if self['mission'] == 'CF' and not E['uid'] in E.sim.counterbattery:
      E.sim.counterbattery.append( E['uid'] )
    elif self['mission'] == 'SEAD' and not E['uid'] in E.sim.sead:
      E.sim.sead.append( E['uid'] )
    return [self]
      
  def EndTask(self, E):
    '''! \brief De-register the CFFZ
    '''
    # De-register
    if E['uid'] in E.sim.counterbattery:
      E.sim.counterbattery.remove( E['uid'] )
    elif E['uid'] in E.sim.sead:
      E.sim.sead.remove( E['uid'] )
      
    # Call the baseclass 
    sandbox_task.EndTask(self, E)
    
    
  def Prosecute(self, ENY = None):
    '''! \brief Used by sim.BroadcastStrike to specify a ENY firing unit.
    '''
    self['prosecute'] = ENY
    
  def _Step(self, E):
    '''! \brief Dispatch to different Step function for different missions
    '''
    # Make sure that the task hasn't been stepped already this pulse
    # This is a necessary step because counter fire may trigger the taks prematurely.
    if self['last fired'] and self['last fired'] == E['agent'].clock:
      return None
    
    # Implement Step
    if self['mission'] == 'SRIKE':
      self.StepSTRIKE(E)
    elif self['mission'] == 'CF' and self['prosecute']:
      self.StepCF(E)
    elif self['mission'] == 'SEAD' and self['prosecute']:
      self.StepSEAD(E)
    
  def StepCF(self, E):
    '''! \brief Implement a Counter BAttery strike
    '''
    pass
  
  
  def StepSEAD(self, E):
    '''! \brief Implement a SEAD counter battery strike
    '''
    pass
  
  def StepSTRIKE(self, E):
    # Activity code
    E['activities this pulse'].extend(self.ConsumptionCodes())
    A = E['agent']
    
    # Pulse
    pulse = E.sim.Pulse()
    
    # Get all ENY in CFFZ
    CFFZ = A.SolveArea( self['CFFZ'] )
    if CFFZ == None:
      return None
    
    # Get units in CFFZ
    units = E.sim.UnitsInPolygon(CFFZ)
    
    # Make sure that the units are in range
    units = self.InRange(E, units)
    
    # Choose a target from the unit list
    tgt = self.SelectTarget(E, units)
    
    if tgt == None:
      return None
    
    # Fires up a strike
    strike = sandbox_strike.sandbox_strike(self['SRCP'], E.GetName(),self['ammo'])
    strike.sender = E['uid']
    strike.target = tgt['uid']
    
    # Flag as firing
    self['last fired'] = copy(E['agent'].clock)
    
    # Broadcast to Sim to trigger counter batteries (right away)
    E.sim.BroadcastStrike(strike)
    
    # Log Shelling activity
    A.log('| Salvo to %s at Position %s'%(tgt.GetName(), A.map.MGRS.AsString(tgt.Position().AsVect())),'operations')

  def SelectTarget(self, E, units):
    '''! \brief Chose on target over elegible.
    '''
    efst = []
    # Select preferably in the EFST list
    if self['EFST']:
      for i in units:
        if i['uid'] in self['EFST']:
          efst.append(i)
    if efst == []:
      efst = units
    
    # Random choice
    return choice(efst)
  
  def InRange(self, E, units):
    '''! \brief Remove units that are either too far or too close
    '''
    maxrange = E['combat']['maxrange']
    minrange = E['combat']['minrange']
    
    maxpoly = sandbox_geometry.circle(E.Position().AsVect() ,maxrange)
    
    out = []
    for i in units:
      if i.Position().Overlaps(maxpoly):
        # add if there is at least 1 vertex beyond the minrange
        vees = i.Position().footprint.vertices()
        me = E.Position().AsVect()
        
        for v in vees:
          if (me-v).length() >= minrange:
            out.append(i)
            break
          
    return out
  def OrderHTML(self, A):
    '''! \brief Prepare a text version of the task for the HTML OPORD.
    '''
    out = 'Perform a %s mission on the target area designated by %s. '%(self['mission'], self['CFFZ'])
    return out + self.OrderTimingHTML()
  
  def AsHTML(self, A):
    out = 'We are performing a %s mission on the target area %s (as per current overlay %s). '%(self['mission'], self['CFFZ'], A.entity['OPORD'].GetOverlay().name)
    return Tag('p', out)
  
# 
# Logistics tasks
class taskPickUp(sandbox_task):
  '''! \brief grab something as a supply package from the ground.
       \param UNIT Must be of the TOE 
       \note Use taskFieldRessuply if one want to integrate the cargo to the unit's organic assets.
       \todo Handle any type of unit
  '''
  def __init__(self):
    sandbox_task.__init__(self,'Pick-Up')
    
    self['UNIT'] = None
    
  def _Process(self, E):
    '''!
       \note set task time to one pulse
    '''
    self['task time'] = E.sim.Pulse()
    self['supply required'] = A.EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    self.sequence.append(self)
    
    return self.sequence
  
  def _Step(self, E):
    '''! \brief Wait for the unit then load it.
    '''
    # Get contact
    cnt = E['agent'].GetContact(E.sim.AsEntity(self['UNIT']))
    
    if cnt == None:
      return
    
    # In footprint
    if E.PointInFootprint(cnt.location):
      if cnt.unit['TOE'] == 'LOGPAC':
        self.LoadLOGPAC(E, cnt.unit)
      else:
        self.LoadUnit(E, cnt.unit)
      self['completion'] = True
  
  def LoadLOGPAC(self, E, U):
    '''! \brief Load the package from a LOGPAC as separate cargo as the main supply
         
        Flag LOGPAC for deletion.
    '''
    E['logistics'].LoadFreight(U.GetCargo())
    U['delete me'] = True
    
  def LoadUnit(self, E, U):
    '''! \brief Load a unit as cargo
         \todo Implement
    '''
    if E.CanLoad(U):
      # Strip cargo if TOE is 
      pass
  
class taskDropOff(sandbox_task):
  '''! \brief Drop a Freight cargo on the ground. 
  
       Superceeds the taskDeliverSupply because it is more general and flexible for adding new type
       of stuff that can be dropped.
  
       \note Will be able to take on entities, but implement here only the drop-off of supply for
       the moment.
  '''
  def __init__(self):
    sandbox_task.__init__(self,'Drop-Off')
    
    self['DP'] = None
    
    self['UNIT'] = None
    
  def _Process(self, E):
    A = E['agent']
    self['task time'] = E.sim.Pulse()
    self['supply required'] = A.EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    self.sequence.append(self)
    
    return self.sequence
  def _Step(self, E):
    '''! \brief take the freight and drop it off exactly under the center of the footprint.
         \todo If DP isn't in the footprint, displace to the right place and do it by inserting a relocate task.
    '''
    # If no DP is allowed, set right under E
    if self['DP'] == None:
      self['DP'] = E.Footprint().Centroid()
      
    # Make sure that the DP is in E's footprint
    if not E.PointInFootprint(self['DP']):
      E['agent'].Log("Can't Drop-off package because DP isn't in the footprint. Bypass task.")
      self['completion'] = True
      return
      
    # Get Freight cargo
    cargo = E['logistics'].UnloadFreight()
    
    # Is this a supply_package?
    if cargo.__class__ == supply_package().__class__:
      LOGPAC = self.SpawnLOGPAC(E,cargo)
      cntLOGPAC = LOGPAC['agent'].ContactDefineSelf()
      
      # Take note of LOGPAC
      E['agent'].ContactUpdate(cntLOGPAC)
      
      # Force a contact to recipient if in contact with recipient
      recipient = E.sim.AsEntity(self['recipient'])
      cntrecip = E['agent'].GetContact(recipient)
      if cntrecip and cntrecip.IsDirectObs():
        recipient['agent'].ContactUpdate(cntLOGPAC)
      self['completion'] = True
        
      
  
  def SpawnLOGPAC(self, E, C):
    '''! \brief Add to the sim a LOGPAC
    '''
    A = E['agent']
    A.log('Delivering supply package.','logistics')
    
    # If not, create a supply LOGPAC.
    LOGPAC = E.sim.MakeLOGPAC()
    
    # Add to world
    name = E.GetName()[E.GetName().find('SUPREQ'):]
    LOGPAC['name'] = 'LOGPAC.'+ name
    LOGPAC['side'] = E['side']
    
    E.sim.AddEntity(LOGPAC)
    self['UNIT'] = LOGPAC['uid']
    
    # transfer the supply to the LOGPAC
    LOGPAC['logistics']['capacity'] = C
    LOGPAC.AdjustSupply(C)
    LOGPAC['recipient'] = self['recipient']
    LOGPAC['SUPREQ'] = self['SUPREQ']

    # Position
    LOGPAC.SetPosition( deepcopy(E['position']) )
    
    # Remove from convoy's store.
    A.log('Unloading %.1f STON to LOGPAC.'%(C),'logistics')
    
    #Move on
    self['completion'] = True
    
    return LOGPAC
    
      
class taskFerry(sandbox_task):
  '''! \brief Pick something up at a Pick-up point and deliver to Drop-off point.
  
       This task is a transparent task since it doesn't persist in the OPORD after the processing.
      
       \param Pick-up (\c vect_3D) [None] The Position of pickup
       \param Drop-off (\c vect3D) [None] The position of drop-off
       \param * time (\c datetime) [None] Optional timing constraints
       \param cargo (\c supply_package) [supply_package()] Stuff to move around.
       \param stance (\c string) The stance to adopt to perform the mission
       
       \warning A ferry task does NOT include the trip back.
  '''
  def __init__(self):
    sandbox_task.__init__(self,'Ferry')
    self['consumption code'].extend(['transit'])
    
    # Pick-up point
    self['Pick-up'] = None
    self['Pick-up time'] = None
    
    # Drop-off point
    self['Drop-off'] = None
    self['Drop-off time'] = None
    
    # Route 
    self['route'] = []
    
    # Package
    self['cargo'] = supply_package()
    
    # Stance
    self['stance'] = None
    
  def _Process(self, E):
    '''! \brief Move stuff from point A to B.
    
         Here is a possible breakdown of the subtasking:
        -# [Redeploy] to self['stance']
        -# [Relocate] to Pick-up
        -# Load
        -# Relocate
        -# Unload

        \warning This task does NOT include any action after unloading. Users should specify a 
        subsequent task OR subclass taskFerry to get it to behave more specifically.
    '''
    # sequence 
    # Initial position by default to E['position']
    if self['initial position'] == None:
      self['initial postion'] = E['position'].AsVect()
      
    # Initial Stance
    if self['initial stance'] == None:
      self['initial stance'] = E.GetStance()
      
    # Validate Pick-up and Drop-off
    if self['Pick-up'] == None or self['Drop-off'] == None:
      # Delete the task
      return self.sequence
    
    # Need for a relocate task?
    if not E.PointInFootprint(self['Pick-up']):
      reloc = taskRelocate()
      reloc['destination'] = copy(self['Pick-up'])
      reloc['stance'] = copy(self['stance'])
      reloc['initial position'] = copy(self['initial position'])
      reloc['initial stance'] = self['initial stance']
      self.sequence.extend(reloc.Process(E))
      
    # Need to Redeploy but not relocate
    elif self['stance'] != E.GetStance():
      redep = taskRedeploy()
      redep['stance'] = self['initial stance']
      redep['final_stance'] = self['stance']
      redep['initial position'] = copy(self['initial position'])
      self.sequence.extend(redep.Process())
      
    # Add a Pick-Up task
    ntask = taskPickUp()
    ntask['cargo'] = self['cargo']
    ntask['initial position'] = copy(self['Pick-up'])
    ntask['initial stance'] = self['stance']
    self.sequence.extend(ntask.Process(E))
    
    # Relocate to Drop-off
    ferry = taskRelocate()
    ferry['destination'] = copy(self['Drop-off'])
    ferry['route'] = self['route']
    ferry['initial position'] = copy(self['Pick-up'])
    ferry['initial stance'] = self['stance']
    self.sequence.extend(ferry.Process(E))
    
    # Add a Drop-off task
    ntask = taskDropOff()
    ntask['cargo'] = self['cargo']
    ntask['initial position'] = copy(self['Drop-off'])
    ntask['initial stance'] = self['stance']
    self.sequence.extend(ntask.Process(E))
    
    return self.sequence  

  def OrderHTML(self, A):
    out = 'You are to ferry %s from %s to %s. '%(self.VerbalizeCargo(),self['Pick-up'].AsString(),self['Drop-off'].AsString())
    out += 'Assume a %s stance. '%(self['stance'])
    return Tag('p',out)
  
  def VerbalizeCargo(self):
    '''! \brief Make a string out of the cargo
         \return Nametag (\c string)
    '''
    if self['cargo'].__class__ == supply_package().__class__:
      return 'a LOGPAC (%.1f STON)'%(float(self['cargo']))
    return 'something'

class taskConvoyMerge(sandbox_task):
  def __init__(self):
    sandbox_task.__init__(self,'Convoy Merge')
    self['consumption code'].extend(['transit'])
    
  def _Process(self, E):
    self['task time'] = E.sim.Pulse()
    self['supply required'] = E['agent'].EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    
    return [self]
  
  def _Step(self, E):
    A = E['agent']
    A.log("Merging convoy to home CSS unit.",'operations')
    
    # Activity code
    E['activities this pulse'].extend(self.ConsumptionCodes())
    
    # Return unexpanded supply to home
    E.GetHQ().AdjustSupply(E['logistics']['cargo'])
    E.GetHQ()['logistics']['freight'] = E.GetHQ()['logistics']['freight'] + E['logistics']['max_freight']
    E.GetHQ()['agent'].log('Reabsorbing %s with outstanding %.2f units left'%(E.GetName(),E['logistics']['cargo']),'logistics')
    
    # Free up the detachment's label
    dt = E.GetName().find('/')
    dt = E.GetName()[:dt]
    E.GetHQ()['agent'].ReleaseDetachment(dt)

    
    # Flag for deletion
    A.log('Disbanding','operations')
    E['delete me'] = 1
    
    #Move on
    if E['OPORD'].NextTaskCanBegin(E['agent'].clock):
      self['completion'] = True
      #E['OPORD'].NextTask()
        

  def AsHTML(self, A):
    out = 'We are disbanding the detachment and re-integrating to the mother unit.'
    return Tag('p',out)
  
class taskDispatchSupply(sandbox_task):
  '''!
   This tasks attempts to send in the full request, if it can't, it spawns a smaller task and lock
   itself until the spawned subtask is sent out.
  '''
  def __init__(self):
    sandbox_task.__init__(self,'Dispatch Supply')
    #self['consumption code'].extend(['transit'])
  
  def _Step(self, E):
    '''!
       Trigger the Dispatch Supply task
    '''
    A = E['agent']
    # Re-hydrate the pointer
    self['target unit'] = E.sim.AsEntity(self['target unit'])
    
    # Check for two units overlapping footprint
    if E.Position().Overlaps(self['target unit'].Position()):
      # Execute a simple transaction -- validate order
      mycargo = E['logistics'].ValidateRequest(self['COMMODITY'])
      E.AdjustSupply(-1*mycargo)
      self['target unit'].AdjustSupply(mycargo)
      A.log('Transferring directly %.2f STON of material to %s.'%(float(mycargo), self['target unit'].GetName()),'logistics')
      self['target unit']['agent'].log('Absorbing directly %.2f STON of material from %s.'%(float(mycargo), E.GetName()),'logistics')
      # remove from list
      if not self.has_key('delayed'):
        E['OPORD']['EXECUTION']['SUPPORT TASKS']['sequence'].remove(self)
      return
      
    # Create a convoy unit ####################
    newconvoy = E.sim.MakeConvoy()
    # Assign Detachment
    det = A.CreateDetachment()
    # Assign name
    newconvoy['name'] = '%s/%s SUPREQ(%s-%s)'%(det,E.GetName(),self['target unit'].GetName(),self['uid'])
    
    # Supply Overhead ########################
    # How much time to budget to run the train there and back (min 24 hrs)
    self['route'] = self['target unit']['agent'].SolveCSSRoute()
    A.SolvePath(self)
    missiontime = max(24.0,A.EstimateTransitTime(self['waypoints']) * 2.0 * 2)
    # How much supply?
    supplyneed = newconvoy['logistics'].ProjectSupply(activity_dict={'idle':missiontime,'transit':missiontime},E=newconvoy)


    # Check for available stock and freight and return max possible cargo
    mycargo = E['logistics'].ValidateRequest(self['COMMODITY'], supplyneed)
    # Set the 0.75 in SOP (in other word, delay the convoy if too small)
    if float(mycargo) < float(self['COMMODITY'] * 0.75) and not self.has_key('EMERGENCY'):
        # Delay the order until later
        self['delayed'] = True
        A.log('Despatch for %.1f STON to %s is delayed by %.2f hours'%(float(self['COMMODITY']),self['target unit'].GetName(),(A.clock-self['planned begin time']).seconds/3600.0),'logistics')
        A.ReleaseDetachment(det)
        # Refold the unit into UID
        self['target unit'] = E.sim.AsUID(self['target unit'])
        return 
    else:
        # Cargo transaction
        # Overwrite COMMODITY, now in real material.
        self['COMMODITY'] = mycargo * 1.0
        netcargo = mycargo + supplyneed
        newconvoy.AdjustSupply(supplyneed) # overhead already added
        newconvoy['logistics'].LoadFreight(mycargo) # The package to be sent.
        E.AdjustSupply(-1*netcargo)
  
        # Discard freight from self
        E['logistics']['max_freight'] = max(E['logistics']['max_freight'],E['logistics']['freight'])
        stuff = netcargo + newconvoy['logistics']['cargo']
        E['logistics']['freight'] = E['logistics']['freight'] - stuff
        #newconvoy['logistics']['freight'] = float(netcargo) # Used to give back at merging time
        newconvoy['logistics']['max_freight'] = stuff
          
      
    # Adjust freight so all that stuff fits in
    newconvoy['logistics']['capacity'] = supplyneed * 1.0
    
    # Introduce into the simulator
    E.sim.AddEntity(newconvoy)

    # Task not delayed anymore
    if self.has_key('delayed'):
        del self['delayed']
        
    # Begin logs
    newconvoy['agent'].clock = A.clock
    A.log('Creation of %s bound to %s.'%(newconvoy.GetName(), self['target unit'].GetName()),'personel')
    newconvoy['agent'].log('Loading %.1f units as cargo.'%(newconvoy['logistics']['cargo']),'logistics')
    A.log('Allocating %.1f units as cargo. We have :%.2f unit left.'%(float(newconvoy['logistics']['cargo']), float(E['logistics']['cargo'])),'logistics')
    
    # Position the convoy
    newconvoy.SetPosition( deepcopy(E['position']) )
    
    # Attach to CSS unit
    newconvoy.ReportToHQ(E)

    # Prepare the OPORD
    opord = A.PrepareOPORD(newconvoy)
    
    # Go to DP
    there = taskRelocate()
    there['stance'] = 'transit'
    there['destination'] = self['destination']
    there['route'] = self['target unit']['agent'].SolveCSSRoute()
    
    # Drop the load
    LOGPAC = taskDropOff() # DP left blank will mean "right under the convoy"
    LOGPAC['cargo'] = mycargo
    LOGPAC['SUPREQ'] = self['SUPREQ']
    LOGPAC['recipient'] = E.sim.AsUID(self['target unit'])
            
    # Come back
    back = taskRelocate()
    back['destination'] = E['position'].AsVect()
    back['route'] = self['target unit']['agent'].SolveCSSRoute()
    back['route'].reverse()
    
    # Dissolve
    end = taskConvoyMerge()
    
    # Assemble
    opord.AddTask(there)
    opord.AddTask(LOGPAC)
    opord.AddTask(back)
    opord.AddTask(end)
    
    # Issue 
    newconvoy.IssueOrder(opord)
    
    # Refold the unit into UID
    self['target unit'] = E.sim.AsUID(self['target unit'])
        
    # remove from list
    if not self.has_key('delayed'):
      E['OPORD']['EXECUTION']['SUPPORT TASKS']['sequence'].remove(self)
      
  def AsHTML(self, A):
    out = 'We deploying a train to ferry a LOGPAC.'
    return Tag('p',out)  

  def SplitDispatch(self, E, overhead):
    '''
       Split the SUPREQ into smaller chunks.
    '''
    # Locked
    if self.has_key('lock split') or self.has_key('splitted from'):
      return
    
    # the staff
    A = E['agent']
    
    
    # Number of supported units
    N = len(A.SolveSupportedUnits())
    
    # Divide evenly the freight (slightly underestimate the freight to make the chunks smaller)
    chunks = E['logistics']['max_freight']*0.9 / N
    mod = (float(chunks)-float(overhead)) / float(self['COMMODITY'])
    subpk = self['COMMODITY'] * mod
    
    if subpk > E['logistics']['freight']:
      return
    
    # Find the modifier to use to divide SUPREQ
    newtask = copy(self)
    newtask['COMMODITY'] = subpk * 1.0
    newtask['target unit'] = E.sim.AsUID(self['target unit'])
    newtask['splitted from'] = self['uid']
    newtask['uid'] = E.GetName() + A.clock.strftime(".%m%d%H%M")
    #self['lock split'] = True # TODO delete locking of splits
    # Add the task to the CSS tasks
    #newtask.Process(E)
    E['OPORD'].AddCSSTask(newtask)
    newtask.Step(E)
    self['COMMODITY'] = self['COMMODITY'] - subpk
      
    # The leftover remains in the task

class taskFieldRessuply(sandbox_task):
  '''! \brief This task takes 1+ LOGPAC and integrate them into the entity
     
       This task is different from the old taskRessuply in the sense that no more planning is attached
       to the task anymore. Only the physical labor of ressuplying the troops in the field is handles.
       Consequently, the interface is rather different.
       
       \param LOGPACs A list of LOGPAC to use as ressuply.
  '''
  def __init__(self):
    sandbox_task.__init__(self,'FieldRessuply')
    self['LOGPACs'] = []
    
  def _Process(self, E):
    '''! \brief Process the time necessary to perform the field ressuply.
         \note LOGPACs must be in the footprint in this version of the implementation.
         \bug Estimate of time based on unit's current position instead of footprint around the DP.
         
    '''
    # The task time will be the time it takes for a truck to traverse the footprint.
    self['displacement'] = E.Footprint().Radius()
    
    # Average displacement velocity
    ave = self.MeanSpeedInFootprint(E)
    
    # The expected nitty-gritty
    self['task time'] = self['displacement'] / ave
    self['supply required'] = E['agent'].EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    
    # If pre-planning for set LOGPACs
    for i in self['LOGPACs']:
      self['supply required'] = self['supply required'] - E.sim.AsEntity(i).GetCargo()
    
    # Must have at least 1 LOGPAC
    return [self]

  def MeanFriction(self,E):
    '''
       compute the mean friction in the footprint in order to compute the displacement time.
    '''
    # Terrain profile
    terrain = E['agent'].map.SampleTerrain(E.Footprint())
    
    # Mean friction from terrain alone
    out = 0.0
    for i in terrain:
      out = out + E['movement'].friction_terrain(i) * terrain[i]
    
    return out
  
  def MeanSpeedInFootprint(self, E):
    '''
       Returns the mean speed within footprint
       OUPUT : In kph
    '''
    return E['movement'].Speed(self.MeanFriction(E),E.C2Level(),E.GetStance())

  def _Step(self, E):
    '''! \brief Chew on the displacement until <= 0.0, then grab all LOGPAcs in the list.
         Attempt to add all LOGPAC in footprint if list undefined 
    '''
    # If no LOGPACs are provided, attempt to solve for any in the footprint.
    if len(self['LOGPACs']) == 0:
      self['LOGPACs'] = E.sim.LOGPACsInFootprint(E)
      # Encode for serialization
      for i in range(len(self['LOGPACs'])):
        self['LOGPACs'][i] = i['uid']
      
    # Abort if nothing to grab and next task can begin
    if len(self['LOGPACs']) == 0:
      if E['OPORD'].NextTaskCanBegin(E['agent'].clock):
        self['completion'] = True
        return
        
    # Chip away at displacement
    self['displacement'] -= self.MeanSpeedInFootprint(E) * E.sim.Pulse()
    
    if self['displacement'] <= 0.0:
      self['completion'] = True
      # Get all the LOGPACS
      for i in self['LOGPACs']:
        LOGPAC = E.sim.AsEntity(i)
        LOGPAC['delete me'] = True
        LOGPAC['agent'].log('Disbanding.','personel')
        # Get all supply
        stock = E['logistics'].StripLOGPACs([LOGPAC])
        E.AdjustSupply(stock)
        
class taskRessuply(sandbox_task):
  '''! \brief Task that stalls progression until completed.
  
       The main distinction with taskFieldRessuply is that it will do everything in its power to 
       accomplish the task, which fieldRessuply bails if the LOGPAC isn't ready to be picked up.
  '''
  def __init__(self):
    sandbox_task.__init__(self,'Ressuply')
    
    self['consumption code'].append('support')
    
    # The supply request
    self['SUPREQ'] = None 
    
  def _Process(self, E):
    '''!
      Staffwork to coordinate a resupply order
      task come from RoutineRessuply, ProcessOPORD or SolveOPORDRess
    '''
    # Gives at most 30 minutes of waiting/loadin (Just-in-time logistics)
    self['task time'] = 0.5
    self['supply required'] = E['agent'].EstimateSupplyRequired(self.ConsumptionCodes()) * self['task time']
    
    self.sequence.append(self)
    
    # The field ressuply
    fR = taskFieldRessuply()
    if self['concurent']:
      fR.MakeConcurent()
    fR.Process(E)
    
    self.sequence.append(fR)
    
    return self.sequence
  
  def _Step(self, E):
    '''!
       Wait for the resupply package, then begin fieldRessuply.
       \todo Try to track the SUPREQ and adjust timing and supply levels estimates.
    '''
    # Local copy of the contact of LOGPAC
    LOGPAC = self.FindLOGPAC(E)
    
    # Will process either 
    if LOGPAC != None :
      DP = LOGPAC.location
      if DP:
        if E.PointInFootprint(DP):
          # Move on to field ressuply
          self['completion'] = True
          self.sequence[1]['LOGPACs'] = [LOGPAC.unit['uid']]
          LOGPAC.unit['Processing'] = True
          self.sequence[1].Process(E)
        
  def FindLOGPAC(self, E):
    '''! \brief Return the contact to the LOGPAC
         \todo get the contact from the CSS/convoys
         \return the first LOGPAC in the list
    '''
    # Local copy
    for i in E['intelligence'].ContactList():
      if i.unit['TOE'] == 'LOGPAC' and i.IsDirectObs() and not i.unit.has_key('Processing'):
        # Check for the right SUPREQ
        if self['SUPREQ']:
          if i.unit['recipient'] == E['uid'] and i.unit['SUPREQ'] == self['SUPREQ']:
            return i
        else:
          if i.unit['recipient'] == E['uid']:
            self['SUPREQ'] = i.unit['SUPREQ']
            return i
        
    return None
    
  def AsHTML(self, A):
    engine = A.entity.sim
    sender = engine.AsEntity(self['SUPREQ']['UNIT'])
    if self['completion'] == None:
      out = 'We are awaiting for the supply package %s-%s. '%(sender.GetName(),self['SUPREQ']['uid'])#(self['uid'])
    else:
      out = 'We are in the process of ressuplying the lower echelons from request %s-%s. Task completion at %d %%. '%(sender.GetName(),self['SUPREQ']['uid'],self['completion']*100)       
    return Tag('p',out)
  def OrderHTML(self, A):
    out = 'Ressuply as per ressuply instructions and according to CSS policies applicable to your TOE.'
    out = out + self.OrderTimingHTML()
    
    return out 
  def IsActive(self):
    '''! \brief Returns True Only if a field ressuply is initiated.
    '''
    if self.GetSubTask() != self:
      return True
    
    return False
  def AdjustSUPREQ(self, E, opord):
    '''! \brief Issue or modify SUPREQ.
         \warning Doesn't modify existing SUPREQ at the moment.
         \todo Implement this.
    '''
    # Create a request
    if self['SUPREQ'] == None:
      A = E['agent']
      T = self['planned begin time']
      minsup, maxsup = A.PolicyMinMaxSupplyLevels()
      capacity = E['logistics']['capacity']
      cargo = A.EstimateCargoAt(T,opord)
      LOGPAC = (capacity * maxsup) - cargo
      DT = A.EstimatePositionAt(T,opord)
      self['SUPREQ'] = A.PrepareSUPREQ(LOGPAC, DT, T)
  
class taskSupport(sandbox_task):
  def __init__(self):
    # Build the base instance
    sandbox_task.__init__(self,'support')
    self['consumption code'].append('support')
    self['stance'] = 'Support'
    
    # sustain
    self.sustain = taskSustain()
    self.sustain.Process(None)
    
  def _Process(self, E):
    # The agent
    A = E['agent']
    
    A.log('| Plan Support Mission','operations')
    # Duration
    if self['task time'] == 0:
        A.log('|     Duration : Indefinite.','operations')
    else:
        A.log('|     Duration : %.2f hours.'%(self['task time']),'operations')
    
    # Logistics (in case the total amount, consider pre-assigned as extra cargo to budjet for )
    if self['supply required']:
        extra = self['supply required']
        A.log('|     Planned Extra supply : %.2f units'%(extra),'operations')
    else:
        extra = supply_package()
        
    # Project supply expsenses
    self['supply required'] = A.EstimateSupplyRequired(self.ConsumptionCodes(),self['task time'])
    self['supply required'] = self['supply required'] + extra
    if self['supply required']:
        A.log('|     Materiel Estimates: %.2f STON.'%(float(self['supply required'])),'operations')
        
    return [self]

  def _Step(self, E):
    ''' 
       Attempt to complete all tasks in the CSS queue
    '''
    A = E['agent']
    
    # Activity code
    E['activities this pulse'].extend(self.ConsumptionCodes())
    
    # Buffer
    csstasks = []
    
    for csstask in E['OPORD'].GetTaskList('css'):
      # Suppression
      if E.IsSuppressed():
        continue
      
      self.RessuplyScheduler(E)
      
    # terminate only if there is a next task
    if E['OPORD'].GetNextTask() and E['OPORD'].NextTaskCanBegin(E['agent'].clock):
      self['completion'] = True
    
    # Do sustenance operations
    self.sustain.Step(E)

        
  def RessuplyScheduler(self, E):
    '''
       Prioritize and dispatch ressuply missions
    '''
    # The units
    myunits = E['agent'].SolveSupportedUnits()
    
    # The burden
    myburden = 1.0
    try:
      myburden = E['logistics'].ComputeRessuplyBurden(myunits)
    except:
      pass
  
    if myburden <= 0.5:
      nosplit = True
    else:
      nosplit = False
    
    tasks = self.RessuplyPrioritize(E)
    
    # Go through each tasks
    for i in tasks:
      # Prevent splitting in low burden situations
      temp = False
      if not i.has_key('lock split') and nosplit:
        temp = True
        i['lock split'] = True
        
      # Step through the task
      i.Step(E)
      
      # Unlock if necessary
      if temp and nosplit:
        del i['lock split']
  
  def RessuplyPrioritize(self, E):
    # The ressuply tasks
    tasks = []
    for i in E['OPORD'].GetTaskList('css'):
      if i['type'] == 'Dispatch Supply':
        tasks.append(i)
        
    # Prioritize
    priority = []
    for i in tasks:
      if i.has_key('EMERGENCY'):
        priority.append(i)
        tasks.remove(i)
    
    # All Tasks
    priority.sort(self.TaskSort)
    tasks.sort(self.TaskSort)
    return priority + tasks
  
  def RessuplyReport(self, A):
    '''
    '''
    E = A.entity
    out = ''
    # List Convoy
    myconvoys = A.SolveSubordinateConvoys()
    if myconvoys:
        cvlist = 'Here is a list of the current detachments performing supply train tasks : '
        header = ['Detachment','SUPREQ (STON)','Supported Unit']
        table = [header]
        for i in myconvoys:
            name = i.GetName()[:i.GetName().find('Tk')-1]
            # Find ressuply task
            qunty = ''
            tgt = ''
            for t in i['OPORD'].GetExpandedTaskList():
                if t['type'] == 'Drop-Off':
                    qunty = '%.2f STON'%(float(t['cargo']))
                    tgt = A.entity.sim.AsEntity(t['recipient']).GetName()
                    break
            table.append([name,qunty,tgt])
        out = out + cvlist + Table(table)
    
    # Pending tasks
    ptasks = self.RessuplyPrioritize(A.entity)
    if len(ptasks) == 1:
      pstring = 'There are a single SUPREQ in the queue: <BR>'
    elif len(ptasks) > 1:
      pstring = 'Here is a list of Pending ressuply tasks: <BR>'
      
    pending =  [['Status','Supported Unit','SUPREQ (STON)','Timestamp']]

    for i in ptasks:
      c1 = 'Pending'
      # Emergency
      if i.has_key('EMERGENCY'):
        c1 = Tag('B','EMERGENCY', 'red')
      if i.has_key('delayed'):
        if i.has_key('EMERGENCY'):
          c1 = Tag('B','Delayed', 'red')
        else:
          c1 = Tag('B','Delayed')
      # Name
      c2 = A.entity.sim.AsEntity(i['target unit']).GetName()
      # Size
      c3 = '%.2f'%(i['COMMODITY'])
      # timestamp
      c4 = i['planned begin time'].strftime('%m%d/%H%M ZULU')
      pending.append([c1,c2,c3,c4])
    if len(pending) > 1:
      out = out + '<BR>Here is a list of ressuply tasks being dispatched internally: <BR>' + Table(pending)
    return out
    
        

  def TaskSort(self, A, B):
    if A['planned begin time'] > B['planned begin time']:
      return 0
    return 1

  def AsHTML(self, A):
    out = 'We are performing ressuply tasks.\n'
    # Ressuply reports
    out = out + self.RessuplyReport(A)
    
    return Tag('p',out)
  def OrderHTML(self, A):
    out = 'Perform combat support operations.'
    out = out + self.OrderTimingHTML()
    
    return out   
#
#


# Template to add new tasks
class taskTemplate(sandbox_task):
  def __init__(self):
    sandbox_task.__init__(self,'template')
    #self['consumption code'].extend(['transit'])
    
  def _Process(self, E):
    return [self]
  
  def _Step(self, E):
    pass
  
  
  
