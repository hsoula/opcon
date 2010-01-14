'''!
        Agent Class -- Staffwork AI implementation for estimates and analyses
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

# import
from copy import deepcopy, copy
from datetime import *
import time as ttime
import os
import os.path
from math import ceil
from random import choice

from vector import NormalizeAngle
from sandbox_comm import *
from intelligence import sandbox_contact
from sandbox_graphics import operational_overlay
from sandbox_position import position_descriptor
from sandbox_tasks import *
from sandbox_geometry import geometry_rubberband
from logistics import supply_package
from logistics import system_logistics_CSS as CSSlogistics # For logistics planning
from logistics import system_logistics

# HTML renderer (for text)
import Renderer_html as html

# Function
def RCPsort(A,B):
    if A.GetRCP() > B.GetRCP():
        return 0
    return 1



# classes
class agent:
    '''! \brief The class emulating a unit's staff.
        An agent is an intelligent interface to the low-level entity. Behaviors must be implemented as 
        and agent and not a method of the entity. Implement in this class all methods that involve 
        micromanagement based on estimates, or straighforward doctrinal resolution. The baseclass
        should not be employed to simulate higher level of decision process. Should this be necessary: it should be reserved
        to am inherited classes or directly into the tasking process. It is advisable to leave to tasks implementation 
        the desicion making as to avoid specialized code into the agent class.
        
        - Process --> Dispatch the process of request or task order
           - Process(request) --> process msg and integrate into entity data
           - Process(task) --> minimally, establish task_time and supply required.
        - Solve --> series of decision made from analyses
        - Prepare --> Make request and reports
        - Contact* --> Handle contacts
        - Estimate --> Project values based on analyses.
    '''
    def __init__(self, entity, map = None):
        self.entity = entity
        self.map = map
        self.clock = datetime.now()
        self.issuedSUPREQs = []
        self.potentialengagements = []
        self.data = {'actions':[], 'Echelon Cnt':{}}
        self.overlay = operational_overlay()
        
        # Minimum survival tasking by default
        self.sustaintask = taskSustain()
        self.sustaintask.Process(self.entity)
        
    def __str__(self):
        '''! \brief "Agent of [sandbox_entity]"'''
        return 'Agent of %s'%(self.entity.GetName())
    #
    # Interface to I/O
    def Situation(self):
        '''!
           Analyse the situation and suggest actions points.
        '''
        # Exclude LOGPACs
        if self.entity.GetName().find('LOGPAC') == 0:
            return
        
        self.log('--------------------------------------------------------------------------')
        # Process all Requests and Orders and convert into tasks and intel pictures
        self.ProcessSTAFF_QUEUE()
                
        # Routine Ressuply
        self.PrepareRoutineRessuply()
        
        # Reporting and all
        self.entity.StepINTEL()
                
    def Process(self, msg):
        '''!
                Generic function to process a new OPORD or REQUEST
        '''
        # Will it be processed because of clarity issues?
        # Can our staff handle it?
        if msg.IsSuppressed() or random() > self.entity.C3Level():
            self.entity.orderoverflow.append(msg)
            return
        
        # Determine whether this is a request or an OPORD using runtime type recognition
        mytype = type(msg)
        # OPORD - New operational orders
        if mytype == type(OPORD()):
            self.ProcessOPORD(msg)
        # SUPREQ - Request for supply (these comes from the units requesting them)
        elif mytype == type(SUPREQ()):
            self.ProcessSUPREQ(msg)
        # CNTREP
        elif mytype == type(CNTREP()):
            self.ProcessCNTREP(msg)
        elif mytype == type(SITREP()):
            self.ProcessSITREP(msg)
        elif mytype == type(INTSUM()):
            self.ProcessINTSUM(msg)
        else:
            self.log('Unimplemented communication request to type : %s'%(type(msg)),'communications')


    def ProcessSTAFF_QUEUE(self):
        '''!
           Seek to implement the new OPORD in the list
        '''
        # All staff queue messages that will not make it this pulse
        self.entity.orderoverflow = []
       
        # Iterate over all item in STAFF QUEUE (OPORD or REQUESTS)
        for i in self.entity['staff queue']:
          self.Process(i)
    
        # Remove all processed items from staff queue, but keep overflow for later.      
        self.entity['staff queue'] = self.entity.orderoverflow       
        
    
    def PrepareOPORD(self, recipient):
        '''! \brief Prepare an OPORD to a given recipient. 
         
             \note Needs to be encoded to be serialized
        '''
        out = OPORD(self.entity, recipient)
        sim = recipient.sim
        '''
        # Intelligence section
        cntlist = []
        for i in self.entity['contacts'].values() + [self.ContactDefineSelf()]:
            if i.fields['nature'] != 'undetected':
                cntlist.append(i.Duplicate('encode'))
        for i in cntlist:
            if i.IFF() == 'FR':
                out['SITUATION']['FRIENDLY FORCES']['DISPOSITION'].append(i)
            else:
                out['SITUATION']['ENNEMY FORCES']['DISPOSITION'].append(i)
        '''
        # Higher unit
        #out['COMMAND AND SIGNAL']['COMMAND']['HIGHER UNIT'] = self.entity['uid']
        return out
    
    def PrepareINTSUM(self):
        '''
        '''
        # IsCommandUnit
        if self.entity.IsCommandUnit() == False:
            return
        # Are we passed the threshold?
        if self.data.has_key('next INTSUM'):
            if self.clock < self.data['next INTSUM']:
                return
        self.log('Preparing a new INTSUM.','intelligence')
        # It is time for a report
        intsum = INTSUM(self.entity)
        for i in self.entity['contacts'].values():
            if i.fields['nature'] != 'undetected':
                temp = i.Duplicate('encode')
                intsum.ContactList(temp)
            
        # Add oneself
        mycnt = self.ContactDefineSelf()
        mycnt.unit = self.entity['uid']
        intsum.ContactList(mycnt)
        
        # Log it to HD
        self.Write('%s.INTSUM.txt'%(self.clock.strftime('%m%d.%H%M')),str(intsum))
        
        intsum['sender'] = self.entity['uid']
        for i in self.entity['subordinates']:
            self.entity.Send(intsum,i)
            
        # Find the delay to the next INTSUM
        # In OPORD
        if self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING'].has_key('INTSUM'):
            d = self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING']['INTSUM']
            self.data['next INTSUM'] = self.clock + timedelta(hours=d)
        elif self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING'].has_key('INTSUM'):
            d = self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING']['INTSUM']
            self.data['next INTSUM'] = self.clock + timedelta(hours=d)
        else:
            del self.data['next INTSUM']
            self.log('No more scheduled INTSUM, should we take appropriate actions?','intelligence')
        

        
    def PrepareWithdrawal(self):
        '''!
           Prepare a withdrawal away from eny preferencially
           Insert to current task a withdrawal task.
        '''
        # Task
        tk = taskWithdrawal()
        tk.Process(self.entity)

        
    def PrepareSITREP(self, echelon = True):
        '''!
           Prepare a SITREP
           
           \param echelon Write a SITREP for owning echelon and not just for the HQ unit.
        '''
        # Dispatch to the righ code
        if echelon and self.entity.EchelonSubordinates():
            # CO agent
            CO = agent_CO(self.entity, self.map)
            CO.clock = self.clock
            return CO.PrepareSITREP()
        
        # HTML render
        ech = self.entity.Echelon()
        if not ech:
            ech = self.entity.HigherEchelon()
        title = 'SITREP for %s %s at time %s\n'%(self.entity.GetName(), ech, self.clock.strftime('%m-%d %H%M ZULU'))
        out = html.Tag('H1',title)
        
        # Contact reporting
        temp, eny, friends = self.REPORT_Contacts()
        out += temp
        
                
        # Adm (logistics) ###############################
        # Human factor(s), fatigue, supression and morale
        out = out + html.Tag('H2','C. Admin') + '<HR>'
        temp=  html.Tag('p',self.REPORT_position())
        
        # Report engagement status if applicable
        if self.entity['ground engagements']:
            temp += html.Tag('p', self.REPORT_Engagement())
            
        temp += html.Tag('p',self.REPORT_CapacityStrenght())
        temp += html.Tag('p',self.REPORT_Command())
        temp += html.Tag('p',self.REPORT_CurrentTask())
        temp += html.Tag('p',self.REPORT_logistics())
        
        out += html.Tag('BLOCKQUOTE',temp)
        
        out = html.HTMLfile('SITREP',out)

        # Other #########################################
        
        # timing
        self.data['last SITREP'] = self.clock        
        
        # Return the actual data structure
        mysit = SITREP(self.entity, eny, friends, out, self.entity.C3Level())
        mysit.PrePickle()
        self.entity.Send(mysit)
        # Log it to HD
        # Make HTML file
        hs = html.HTMLfile(title,str(mysit))
        self.Write('%s.SITREP.html'%(self.clock.strftime('%m%d.%H%M')),hs)
        return mysit
    
    def PrepareSUPREQ(self, LOGPAC, DP, T, emergency_flag = False):
        '''! \brief Prepare a Supply Request
             \param LOGPAC The Requested package.
             \param DP Destination point (vect_3D()).
             \param T Time of arrival.
             \return SUPREQ
             
             It does the following:
            -# Solve for the CSS unit to send to
            -# Prepare request
            -# Send request
            -# Make note of the order so it can be retrieved.
        '''
        # Shorthand
        E = self.entity
        A = self
       
        # Place the Order to Higher Unit
        request = SUPREQ()
        # Fill details
        request['UNIT'] = E['uid']
        request.sender  = E['uid']
        request['DP']   = DP
        request['COMMODITY'] = LOGPAC
        request['CSS unit'] = self.SolveCSSUnit()['uid']
        request['route'] = self.SolveCSSRoute()
        request['uid'] = self.commUID()
        request['ETA'] = T
        if emergency_flag:
            request['EMERGENCY'] = True

        request['C3 level'] = E.C3Level()
        A.log('|     CSS Unit : %s'%(E.sim.AsEntity(request['CSS unit']).GetName()))
        A.log('|     DP : MGRS %s'%(A.map.MGRS.AsString(DP)))
        A.log('|     ETA: %s'%(T.strftime('%m%d/%H%M ZULU time')))
        if A.SolveCSSUnit() in E['subordinates']:
          E.Send(request, A.SolveCSSUnit())
        else:
          E.Send(request)
        
        return request
      
    #
    # Models
    #
    # Staff Tasks
    def PulseStaffwork(self):
        '''! \brief Trigger the execution of the various staffwork.
        '''
        if self.entity['TOE'] == 'LOGPAC':
            return
        for i in range(1,7):
            mt = getattr(self,'routine_S%d'%(i))
            mt()
        
    def routine_S1(self):
        '''! \brief Routine personel staffwork.
        '''
        pass
    def routine_S2(self):
        '''! \brief Routine intelligence staffwork.
        '''
        # Reporting and all
        self.entity.StepINTEL()
        
    def routine_S3(self):
        '''! \brief Routine operations staffwork.
        '''
        # Delete all Echelon footprint
        self.Situation()
    
    def routine_S4(self):
        '''! \brief Routine logistics staffwork.
        '''
        # Routine Ressuply
        self.PrepareRoutineRessuply()
        
    def routine_S5(self):
        '''! \brief Routine public affairs staffwork.
        '''
        pass
    
    def routine_S6(self):
        '''! \brief Routine communications staffwork.
        '''
        # Process all Requests and Orders and convert into tasks and intel pictures
        self.ProcessSTAFF_QUEUE()
    
    def StaffName(self, role, echelon = None):
        '''! \brief Returns the name of the staff officer on a specific role.
        '''
        # Get the unit's current echelon.
        if echelon == None:
            echelon = self.entity['command_echelon']
        
        if 'Div Corp EAC'.find(echelon) != -1:
            prefix = 'G'
        elif echelon == 'Plt Sqd Sec installation Team'.find(echelon) != -1:
            return 'XO'
        else:
            prefix = 'S'
        
        temp = ['personel','intelligence', 'operations', 'logistics', 'public affairs', 'communications']
        if role in temp:
            return prefix + str(temp.index(role))
        else:
            return 'CO'
        
        
    def log(self, entry, who = None):
        '''!
                Add a line into the logfile
        '''
        # Staff Officer
        if who == None:
            SO = '     '
        else:
            SO = self.StaffName(who)
            if SO:
                SO = '[%s] '%(SO)
        # Ignore if last entry is the same as previous
        if self.entity['log'].lines:
            a = self.entity['log'].lines[-1].find(entry)
            if a != -1:
                if self.entity['log'].lines[-1][a:] == entry:
                    return
        out = SO
        out += self.clock.strftime('(%m-%d) %H%M:%S | ') + entry
        self.entity['log'].Add(out)
        
  
    def navigate(self, distance, init, waypoints):
        '''!
           Task independent implementation of the Navigate function.
           INPUT : 
                 distance : Distance to travel in km
                 init     : The vect_5D instance to modify
                 waypoints: list of waypoints to follow
        '''
        # Catch an empty waypoints situation
        if waypoints == []:
            return init, []
        
        # Orient to next waypoint
        newbearing = init.BearingTo(waypoints[0])
        # Set movement's bearing
        init.course = newbearing[0]
        # Loop through close WP
        while distance > newbearing[1]:
            init.rate = newbearing[1]
            init.Step()
            # Adjust distance
            distance = distance - newbearing[1]
            # delete waypoint
            if len(waypoints) == 1:
                waypoints = []
                return init, waypoints
            else:
                waypoints = waypoints[1:]
                newbearing = init.BearingTo(waypoints[0])
                init.course = newbearing[0]
                
        # Now that the distance isn't reaching anymore
        init.rate = distance
        init.Step()
        return init, waypoints
                    
    #
    # Process tasks, orders and requests
    def ProcessOPORD(self, opord, nointel = False):
        '''! \brief Process an OPORD once in the staff queue.
        
           Here is a list of task done in this method:
           - Log planning info in to the Log instance of the owning entity
           - set the opord['received'] to the current time stamp
           - Update the overlay
           - Integrate the contacts from the contactlist
           - [Set HQ]
           - Process all tasks
           - Time and compute supply estimates
           
           \param opord (\c OPORD) An instance of an OPORD
           
           \warning Is keeping track if INIREADINESS (string tag for search) necessary?
           
        '''
        # Time Stamp
        if not opord.has_key('sent timestamp'): 
            self.log('=====================================================')
            self.log('| Processing New OPORD at %s'%(self.clock),'operations')
            
        opord['sent timestamp'] = copy(self.clock)
        # Redirect FRAGO to current OPORD
        if opord.has_key('FRAGO'):
            self.log('| Processing New FRAGO at %s'%(self.clock),'operations')
            self.entity['OPORD'].MergeFRAGO(opord)
            self.entity['agent'].ProcessOPORD(self.entity['OPORD'], nointel = True)
            return
        
        
        # Time stamp
        opord['received'] = deepcopy(self.clock)
        
        # SITUATION #####################################################
        # Read a contact
        if not nointel:
            self.IntegrateContactList(opord.GetContactList())
        self.SetMapOverlay(opord.GetOverlay())
        
        # MISSION #######################################################
        
        # EXECUTION #####################################################
        # Process all the relocate task
        self.ProcessOPORDTasks(opord)
        
        # SUPPORT #######################################################
        # SET CSS unit
        
        # Set MSR
        
        # Supply Policies
        
        # COMMAND #######################################################
        # Set HQ 
        tHQ = self.entity.sim.AsEntity(opord.GetHQ())
        if tHQ != self.entity['HQ'] and tHQ != None:
            self.entity.ReportToHQ(tHQ)
            
        # Timing and Projected logistics
        self.EstimateOPORDTiming(opord)    
        self.SolveOPORDRessuply(opord)
        
        # Initiate the first task
        if opord['scope'] == 'overwrite':
            self.entity['OPORD'] = opord
            self.InitializeOPORD()
        
    def ProcessOPORDTasks(self, opord):
        '''! \brief Set the initial conditions and process task queue.
        
             Pulled into a separate method for readability of the ProcessOPORD() method.
             
             \opord The OPORD/FRAGO to process
        '''
        initpos = deepcopy(self.entity['position'])
        initread = self.entity['readiness']
        curstance = self.entity.GetStance()
        for i in opord.GetTaskList():
            i['initial position'] = initpos
            i['initial readiness'] = initread
            i['initial stance'] = curstance
            
            i.Process(self.entity)
            
            if i.has_key('destination'):
                initpos = copy(i['destination'])
            # Is this necessary INIREADINESS
            if i.has_key('final readiness') and i['final readiness'] != None:
                initread = i['final readiness']
            if i.has_key('final_stance'):
                if i['final_stance']:
                    curstance = i['final_stance']
                    
    def ProcessINTSUM(self, intsum):
        '''
        '''
        self.log('Receiving an INTSUM','communications')
        endline = False 
        self.Write('%s.INTSUM.incoming.txt'%(self.clock.strftime('%m%d.%H%M')),str(intsum))
        for i in intsum.ContactList():
            # from UID to pointer to unit
            # Ignore defunct units
            if self.entity.sim.AsEntity(i.unit) == None:
                continue
            #if type(i.unit) == type(1):
            temp = i.Duplicate()
            temp.unit = self.entity.sim.AsEntity(temp.unit)
            # Absorb and then report if needed.
            if self.ContactAbsorb(temp):
                endline = True
                self.log('\t| Adding contact %s to our intelligence picture.'%(temp.TrackName()),'intelligence')
            else:
                endline = True
                self.log('\t| Updating contact %s in our intelligence picture.'%(temp.TrackName()),'intelligence')
        if endline:
            self.log('\t--- End INTSUM ---','intelligence')

    def IntegrateContactList(self, cntl):
        for i in cntl:
            # from UID to pointer to unit
            # Ignore defunct units
            if self.entity.sim.AsEntity(i.unit) == None:
                continue
            #if type(i.unit) == type(1):
            temp = i.Duplicate()
            temp.unit = self.entity.sim.AsEntity(temp.unit)
            # Absorb and then report if needed.
            if self.ContactAbsorb(temp):
                endline = True
                self.log('\t| Adding contact %s to our intelligence picture.'%(temp.TrackName()),'intelligence')
            else:
                endline = True
                self.log('\t| Updating contact %s in our intelligence picture.'%(temp.TrackName()),'intelligence')
                
    def ProcessCNTREP(self, rep):
        '''!
           Integrate a contact report to the intelligence picture.
        '''
        self.log('Received a contact report from %s'%(rep.Sender(self.entity.sim).GetName()),'communications')
        # Re-generate the contact's unit pointer
        rep.PostPickle(self.entity.sim)
        rep.cnt.unit = self.entity.sim.AsEntity(rep.cnt.unit)
        # Catch defunct units (such as deleted LOGPACs)
        if rep.cnt.unit == None:
            return
        
        # Determine in within whether the report comes from below.
        within = None
        if rep.Sender in self.entity.Subordinates():
            within = rep.Sender['uid']
        if self.ContactAbsorb(rep.cnt, within):
            self.log('\t| Adding contact %s to our intelligence picture.'%(rep.cnt.TrackName()),'intelligence')
    
    def ProcessSITREP(self, rep):
        '''!
           Integrate a SITREP report to the intelligence picture.
        '''
        rep.PostPickle(self.entity.sim)
        if rep.Sender(self.entity.sim) == None:
            return
        # Save the SITREP into the 
        self.entity.CacheSITREP(rep.sender['uid'],rep)
        
        
        self.log('Received a SITREP from %s'%(rep.Sender(self.entity.sim).GetName()),'communications')
        cnts = rep.contacts + rep.friends
        endline = False
        for i in cnts:
            # Convert back to a pointer from a UID (needed for serialization.)
            i.unit = self.entity.sim.AsEntity(i.unit)
            # catch Defunct units
            if i.unit == None:
                continue
            # This should be taken care of later on in the processing, in the AbsorbFn
            #i.UpdateField('nature','reported')
            if self.ContactAbsorb(i,self.entity.sim.AsUID(rep.sender)):
                endline = True
                self.log('\t| Adding contact %s to our intelligence picture.'%(i.TrackName()),'intelligence')
            else:
                self.log('\t| Updating contact %s in our intelligence picture.'%(i.TrackName()),'intelligence')
        if endline:
           self.log('\t--- End SITREP ---','communications')
           
    
    def ProcessSUPREQ(self, request):
        '''!
           Convert a SUPREQ into a task for the appropriate CSS.
           INPUT : An instance of SUPREQ()
           Effect : 1) If self is CSS --> Create a Dispatch supply task and add it to the CSS tasks
                    2) Pass it on up/down the chain of command if unit isn't CSS.
        '''
        # If the processing unit is the target CSS unit
        if request['CSS unit'] == self.entity['uid']:
            # Reconstitute the unit pointers (stored as UID for pickling)
            request['CSS unit'] = self.entity.sim.AsEntity(request['CSS unit'])
            request['UNIT'] = self.entity.sim.AsEntity(request['UNIT'])
            
            # Create a Dispatch Task.
            task = taskDispatchSupply()
            task['SUPREQ'] = request
            task['target unit'] = self.entity.sim.AsUID(request['UNIT'])
            task['priority'] = request['TYPE']
            task['destination'] = request['DP']
            task['uid'] = request['uid']
            task['COMMODITY'] = request['COMMODITY']
            try:
                # Delayed release
                task['planned begin time'] = request['planned begin time']
            except:
                # Immediate release
                task['planned begin time'] = self.clock
                
            # Task time (a pulse by default)
            task['task time'] = self.entity.sim.Pulse()
            
            # Process and add task to opord (NB: process does nothing at the moment)
            task.Process(self.entity)
            self.entity['OPORD'].AddCSSTask(task)
        
        else:
            # If not, send the request up/down the chain of command
            # C4I levels for request is an average of both C4I values.
            request['C3 level'] *= self.entity.C3Level() 
            
            # Send to subordinates if applicable
            tgtunit = self.entity.sim.AsEntity(request['UNIT'])
            cssunit = self.entity.sim.AsEntity(request['CSS unit'])
            
            if cssunit in self.entity.AllSubordinates():
                # Get the chain of command, chain 1 HAS to be the next unit in line
                chain = self.entity.ChainOfCommandTo(cssunit)
                self.log('Forward Supply request from %s to %s'%(tgtunit.GetName(), chain[1].GetName()),'communications')
                self.entity.Send(request,chain[1])
            else:
                # Relay up the chain
                if self.entity.GetHQ():
                    self.log('Relay Supply request from %s to %s'%(tgtunit.GetName(), cssunit.GetName()),'communications')
                    self.entity.Send(request)
                # Else, shred the request.
                else:
                    self.log('SUPREQ from %s cannot be passed to %s. It has been thrown in the shredder.'%(tgtunit.GetName(), cssunit.GetName()),'communications')
    
    
    def MatchCodewords(self, CW):
        '''!
           Consider a list of codewords and return these that aren't matched yet.
        '''
        # Empty conditions
        if CW == []:
            return False
        
        # No codeword recorded
        if not self.data.has_key('codewords'):
            return False
        
        # All must be matched
        for i in CW:
            if not i in self.data['codewords']:
                return False
        
        return True    
    #
    # Staff Planning Subroutines
    # Decision Making
    def PolicyPrioritize(self, elements):
        '''!
           consider a list of elements and return them sorted by priority (if they are priorities). Useful to make tactical desisions.
           
           usage:
                 top_priority = self.PolicyPrioritize(['timing','readiness','avoid urban'])[0]
                 top_priority = self.PolicyPrioritize(['terrain','readiness', 'economy'])[0]
                 
        '''
        # Get the OPORDs concepts
        concepts = self.entity['OPORD']['EXECUTION']['CONCEPT']['PRIORITY']
        concepts = concepts + self.entity['SOP']['EXECUTION']['CONCEPT']['PRIORITY']
        
        # Add in order 
        out = []
        for i in concepts:
            if i in elements:
                out.append(i)
        return out
    def PolicySendSITREP(self):
        # Determine if one is warranted
        if self.data.has_key('next SITREP'):
            if self.clock < self.data['next SITREP']:
                return False
        self.log('Preparing a new SITREP.','operations')
        # Set next SITREP
        if self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING'].has_key('SITREP'):
            d = self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING']['SITREP']
            self.data['next SITREP'] = self.clock + timedelta(hours=d)
        elif self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING'].has_key('SITREP'):
            d = self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING']['SITREP']
            self.data['next SITREP'] = self.clock + timedelta(hours=d)
        else:
            del self.data['next SITREP']
            self.log('No more scheduled SITREP, should we take appropriate actions?','operations')
        return True
    
    #
    # Map markings
    def SolveFootprint(self):
        '''! \brief A S2 function which solves the footprint of the unit's echelon.
        '''
        if self.entity.Echelon():
            temp = agent_CO(self.entity, self.map)
            return temp.SolveFootprint()
            
        # Don't lie, there is only 1 unit to worry about anyway.
        return self.entity.EchelonFootprint()
    #    
    # Supply
    def EstimateCasulatiesFigures(self):
        '''!
           Estimate the number of KIA/MIA, WIA, destroyed vehicle and dammaged ones.
           Return as a tuple
        '''
        # FIXME
        #D = 1.0 - self.entity['combat'].RawRCP()/self.entity['combat']['TOE RCP']
        #C =  self.entity['combat'].UnavailableRCP() / self.entity['combat']['TOE RCP']
        D = 0.0
        C = 0.0
        #Nv = self.entity['logistics']['Nv']
        #Np = self.entity['logistics']['Np']
        Nv = 1
        Np = 1
        
        W = int(C * Np)
        K = int(D * Np) - W
        dm = C * Nv
        dt = int(D * Nv) - dm
        
        return K, W, dt, dm
        
    def SolveOPORDRessuply(self, opord):
        '''! \brief Find whether there is a need to resupply within the OPORD
             \param opord An OPORD instance
             \note May add a resupply task if required by SOP/OPORD during planning.
        '''
        # Dont bother if there is no ressuply unit
        if self.SolveCSSUnit() == None or self.SolveCSSUnit() == self.entity:
            return
        # Find Standing orders, first directly on OPORD
        minsup, maxsup = self.PolicyMinMaxSupplyLevels()
        capacity = self.entity['logistics']['capacity']
        
        # Go Over every tasks
        for i in range(len(opord.GetTaskList())):
            task = opord.GetTaskList()[i]

            if isinstance(task,taskRessuply):
                task.AdjustSUPREQ(self.entity,opord)
            
            T = task.PlannedEndTime()
            if T:
                cargo = self.EstimateCargoAt(T,opord)
                if min((cargo/capacity).values()) <= minsup:
                    # Add a ressuply mission 
                    LOGPAC = (self.entity['logistics']['capacity'] * maxsup) - cargo
                    DT = self.EstimatePositionAt(T,opord)
                    # Make a field ressuply request
                    fieldRessuply = self.PrepareSUPREQ(LOGPAC,DT,T)
                    # Insert a field ressuply
                    tkRess = taskRessuply()
                    tkRess['SUPREQ'] = fieldRessuply
                    tkRess.Process(self.entity)
                    task.sequence.append(tkRess)
                    # Re-start the timing and SolveOPORDRessuply from the beginning.
                    self.EstimateOPORDTiming(opord)
                    return self.SolveOPORDRessuply(opord)
                    
 
    def SolveRessuplyFromLOGPACs(self, LOGPAClist):
        '''! Move to ressuply task if there are LOGPACs in range
        '''
        opord = self.entity['OPORD']
        
        # Make sure the current task isn't ressuply
        if opord.GetCurrentTask():
          if opord.GetCurrentTask()['type'] == 'Ressuply':
            return
          
        toremove = []
        task = None
        for LOGPAC in LOGPAClist:
          # Emergency switch to a Ressuply task
          # Find the pending task
          waybill = LOGPAC.GetName()
          for i in self.issuedSUPREQs:
            if waybill.find(i['uid']) != -1:
              task = i
              toremove.append(i)
        # Remove tasks
        for i in toremove:
          self.issuedSUPREQs.remove(i)
        
        if task:
          opord.InsertToCurrentTask(task)
          self.log('Begin Recovery of Supply in %s'%(waybill),'logistics')
          self.EstimateOPORDTiming(opord)
          
    def PrepareRoutineRessuply(self):
        '''!
           Plan ressuply on ongoing tasks, after the initial planning is done.
        '''
        # Merged convoys should not ask for supply!
        if self.entity.has_key('delete me'):
            return
        
        # Only if current task has no defenitive end. Others are cuaght during OPORD planning.
        ct = self.entity['OPORD'].GetCurrentTask()
        if ct != None:
            if ct.TaskTime() != 0:
                return
        
        # Dont bother if no Resuply unit (or the SOP CSS is set to self)
        myCSS = self.SolveCSSUnit()
        if myCSS == None or myCSS == self.entity:
            return
        
        # Pending tasks. Don't bother if there is other ressuply tasks pending
        for i in self.issuedSUPREQs:
            if i.__class__ == SUPREQ().__class__:
                return

        # Time to reach threshold for ressuply.
        timeleft = self.EstimateTimeToRessuply()
        
        # Time to next routine ressuply
        timeroutine = ((self.SolveNextRoutineRessuplyTime() - self.clock).seconds) / 60.0**2
        if (timeleft) > timeroutine:
            EMERGENCY = False
            timeleft = timeroutine
        else:
            EMERGENCY = True
        
        # Time estimates for the train to reach the unit.
        timeneeded = self.EstimateConvoyTransitTime()
        
        # 10% margin of error
        if timeleft <= timeneeded * 1.1:
            # Min max
            mn, mx = self.PolicyMinMaxSupplyLevels()
            
            # Package
            LOGPAC = (self.entity['logistics']['capacity'] * mx) - self.EstimateCargoAt(self.clock+timedelta(hours=timeleft))
            
            # DP
            DP = self.entity['position'].AsVect()
            
            # Estimate TOA
            plantime = max(timeleft,timeneeded)
            T = self.clock + timedelta(seconds = plantime*3600)
            
            # Send Supreq
            supreq = self.PrepareSUPREQ(LOGPAC,DP,T, EMERGENCY)
            
            # Add to pending
            self.issuedSUPREQs.append(supreq)

    #
    # contacts
    def GetContact(self, E):
        return self.entity.Contact(E)
    
    def GetContactList(self):
        return self.entity['contacts'].values()
    
    def ContactAbsorb(self, cnt, fromwithin = False):
        '''!
           From reports of any kind
           \param fromwithin When the contact comes from a sub-unit, the flags takes on the uid of the observer
           OUTPUT True if new contact
        '''
        if cnt.unit == self.entity:
            return
        contact = self.entity.Contact(cnt.unit)
        if contact != None:
            if cnt.IsDirectObs() and fromwithin:
                contact.AddDirect(fromwithin)
            elif not cnt.IsDirectObs() and fromwithin: 
                contact.RemoveDirect(fromwithin)
            cnt.UpdateField('nature', 'reported')
            contact.Merge(cnt)
            del cnt
            return False
        else:
            # Make a personal copy because the broadcast version is shared by everyone
            cnt = cnt.Duplicate()
            if cnt.IsDirectObs() and fromwithin:
                cnt.AddDirect(fromwithin)
            elif not cnt.IsDirectObs() and fromwithin: 
                cnt.RemoveDirect(fromwithin)
            cnt.UpdateField('nature', 'reported')
            self.ContactUpdate(cnt)
            return True
        
        
    def ContactDefineSelf(self):
        '''!
           Prepare a fully informative contact about self.entity
        '''
        # Create the contact
        cnt = sandbox_contact(self.entity)
        # Right all the time about self.
        cnt.p_right = 1.0
        # unit
        cnt.unit = self.entity
        # Set the time
        cnt.timestamp = copy(self.clock)
        # All fields updated
        cnt.UpdateField('symbol', self.entity['icon'], mytime = self.clock)
        cnt.UpdateField('hardware', self.entity['TOE'], mytime = self.clock)
        cnt.UpdateField('size indicator', self.entity['size'], mytime = self.clock)
        #cnt.UpdateField('equipment', val, mytime = self.clock)
        #cnt.UpdateField('task force', val, mytime = self.clock)
        cnt.UpdateField('nature', 'direct', mytime = self.clock)
        #cnt.UpdateField('reinforced/detached', val, mytime = self.clock)
        #cnt.UpdateField('staff comment', val, mytime = self.clock)
        #cnt.UpdateField('additional information', val, mytime = self.clock)
        cnt.UpdateField('evaluation rating', 'A1', mytime = self.clock)
        #cnt.UpdateField('combat effectiveness', self.entity['combat']['RCP'], mytime = self.clock)
        cnt.UpdateField('combat effectiveness', 1.0, mytime = self.clock)
        #cnt.UpdateField('signature equipment', val, mytime = self.clock)
        try:
            cnt.UpdateField('higher formation', self.entity.GetHQ()['echelon'], mytime = self.clock)
        except:
            pass # TODO, implement a robust higher echelon solving.
        #cnt.UpdateField('enemy(hostile)', val, mytime = self.clock)
        cnt.UpdateField('side', self.entity['side'], mytime = self.clock)
        cnt.UpdateField('IFF/SIF', 'FR', mytime = self.clock)
        #cnt.UpdateField('movement arrow', val, mytime = self.clock)
        cnt.UpdateField('mobility', self.entity.GetStance(), mytime = self.clock)
        #cnt.UpdateField('locating indicator', val, mytime = self.clock)
        cnt.UpdateField('unique designation', self.entity.GetName(), mytime = self.clock)
        cnt.timestamp = deepcopy(self.clock)
        cnt.UpdateField('datetime', cnt.timestamp.strftime('%d%H%M%SZ%b%y'), mytime = self.clock) #DDHHMMSSZMONYY
        #cnt.UpdateField('altitude/depth', val, mytime = self.clock)
        cnt.SetLocation(copy(self.entity['position']))
        #cnt.UpdateField('location', self.map.MGRS.AsString(cnt.location), mytime = self.clock)
        cnt.location.SetFootprint(copy(self.entity.Footprint()))
        cnt.UpdateField( 'Echelon Footprint', copy(self.SolveFootprint()) )
        #cnt.UpdateField('footprint', self.entity.Footprint())
        cnt.UpdateField('speed', self.entity['position'].rate * 1.0 / (self.entity.sim.Pulse()), mytime = self.clock)
        
        # Min/Max range IF
        '''
        if self.entity.IFRCP():
            temp = self.entity.IFranges()
            cnt.UpdateField('min IF range', temp[0])
            cnt.UpdateField('max IF range', temp[1])
        '''
        
        return cnt
            
    def ContactLose(self, cnt, note, fromwithin = False):
        '''!
           Flag a contact as lost and take action if necessary
           note : the reason why it was lost in the first place
        '''
        if cnt == self.entity:
            return
        contact = self.entity.Contact(cnt)
        if note == '':
            note = 'Undetermined'
        if contact != None:
            contact.timestamp = copy(self.clock)
            if fromwithin in contact.direct_subordinates:
                contact.RemoveDirect(fromwithin)
            contact.UpdateField('nature', 'lost')
            self.log('>>Contact %s is lost. Cause: %s.'%(contact.TrackName(),note),'intelligence')
            # Report if needed.
            if self.ContactPolicy('lost'):
                self.log('>>Reporting lost contact %s.'%(contact.TrackName()),'intelligence')
                temp = contact.Duplicate('encode')
                myrep = CNTREP(self.entity,self.entity.GetHQ(), temp, self.entity.C3Level())
                myrep.PrePickle()
                self.entity.Send(myrep)
        
    def ContactPolicy(self, query):
        '''!
           Return the SOP/OPORD structure relating to this theme
        '''
        if self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING'].has_key(query):
            return self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING']
        return self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING']
    
    def ContactUpdate(self, cnt):
        '''! 
           change a contact and take action if necessary. Changing includes adding new contacts to the list
        '''
        if cnt.unit == self.entity:
            return
        # Never bother with a contact flagged for deletion
        if cnt.unit.has_key('delete me'):
            if cnt.unit['delete me']:
                return
        # Get contact
        contact = self.entity.Contact(cnt.unit)
        if contact != None:
            contact.Merge(cnt)
            del cnt
            # TODO check to see whether the contact should be reported.
        else:
            # Case where non-logged contact are not detected, but should be
            cnt.timestamp = copy(self.clock)
            self.entity.WriteContact(cnt)
            if self.ContactPolicy('new') and cnt.IsDirectObs():
                # report only if HQ
                if self.entity.GetHQ():
                    self.log('>>Reporting new contact %s.'%(cnt.TrackName()),'communications')
                    self.Write('%s.CNTREP.txt'%(self.clock.strftime('%m%d.%H%M')),str(cnt))
                    temp = cnt.Duplicate('encode')
                    myrep = CNTREP(self.entity,self.entity.GetHQ(),temp, self.entity.C3Level())
                    myrep.PrePickle()
                    self.entity.Send(myrep)
    def CanEngage(self, E):
        '''!
           Determine whether entity E can be engged by the parent entity.
           Criterion 1 - Direct Observation.
           Criterion 2 - In weapons range (footprint for now).
           Criterion 3 - Have the necessary ammo to do it (TODO)
        '''
        # In contact (direct)
        incontact = False
        cnt = self.GetContact(E)
        if cnt != None:
            incontact = cnt.IsDirectObs()
            
        # overlaps
        overlap = self.entity.Footprint().Overlaps(E.Footprint())
        
        return incontact and overlap
    # 
    # Threats 
    def EstimateThreat(self, cnt):
        '''!
           Estimate a threat weight of a contact.
           TODO : Assign threat of 1 to all. 
        '''
        out = 1.0
        
        # RCP as base.
        if cnt.fields['combat effectiveness'] != '':
            out *= cnt.fields['combat effectiveness']
            
        return out
    
    def SolveWithdrawalHeading(self):
        '''!
           Find which direction the unit should withdraw toward to get out of an engagement.
           Remember last solution as 
        '''
        # Create a default entry
        if not self.data.has_key('last withdrawal heading'):
            self.data['last withdrawal heading'] = self.entity['position'].course
        
        # Fetch all 
        count = 0
        cntlist = []
        # Build a list of all engaged units
        units = []
        for i in self.entity['ground engagements']:
            units = units + i.ListActiveENY(self.entity)
        for i in units:
            cnt = self.entity.Contact(i)
            cntloc = cnt.location
            if cntloc != None:
                cntlist.append(cnt)
                
        # Compute the mean vector
        bear = self.SolveThreatVector(cntlist)
        
        # Remember solution
        self.data['last withdrawal heading'] = bear.course
            
        return bear.course
    
    
    def SolveThreatAxis(self):
        return self.SolveThreatVector(self.entity.ContactList())
    
    def SolveThreatVector(self, cntlist):
        '''!
           Solve for the vector to the cummulative threat based on the contact provided 
           by the list cntlist.
           The length of the vector is the anisotropy of the threat vector. Values close to 1.0 means that
           the threat is concetrated around the vector's heading.
        '''
        # The out vector
        out = vect_5D()
        
        if len(cntlist) == 0:
            return out
            
        # The sum of all threat
        sm = 0.0
        
        for i in cntlist:
            if i.location:
                T = self.EstimateThreat(i)
                sm += T
                # Relative vector time the scalar Threat estimates
                V = (i.location - self.entity['position'])
                V.Normal()
                out += V * T
                
        if T > 0.0:
            return out * (1.0 / T)
        
        # Shouldn't happen unless all cnt are exaclty at the same coordinates than
        # self.entity
        return out
    
    #
    # Combat
    def SolvePriorityTarget(self, tgtlist):
        '''!
           Returns the priority target amongst the list tgtlist
        '''
        # Make a list of contacts (get rid of unseen units).
        cntlist = []
        for i in tgtlist:
            cnt = self.GetContact(i)
            if cnt != None:
                if cnt.IsDirectObs() and cnt.IFF() != self.entity['side'] and cnt.IFF():
                    cntlist.append(cnt)
        
        # Dumb picker, choose a random unit
        if cntlist:
            tgt = choice(cntlist)
            return tgt.unit
        return None
        
    #
    # Reports preparation
    def REPORT_Contacts(self):
        '''! \brief Do the contact reporting for the SITREP
         
             \return outstring, eny vector and friends vector
        '''
        # Contacts
        out = ''
        eny = []
        friends = []
        for i in self.entity['contacts'].values():
            if i.IsDirectObs():
                temp = i.Duplicate('encode')
                if self.SolveIFF(i.fields['side']) != 'FR':
                    eny.append(temp)
                else:
                    friends.append(temp)

        if eny:
            out = out + html.Tag('H2','A. Eny Forces') + '<HR>\n'
            tout = ''
            for i in eny: 
                tout += i.AsHTML()
            out += html.Tag('BLOCKQUOTE', tout)
        else:
            out = out + html.Tag('H2','A. Eny Forces') + '<HR>' + html.Tag('BLOCKQUOTE','None to report.') + '\n'
            
                
        # Own Tps #######################################
        # Location and Stance
        us = self.ContactDefineSelf()
        out = out + html.Tag('H2','B. Friendly Forces') + '<HR>'
        tout = html.Tag('STRONG','Reporting Unit: ') +  ' <BR>'
        tout +=  us.AsHTML()
        if friends:
            tout += html.Tag('H3','Other Friendlies:') +'\n'
        for i in friends:
            tout += i.AsHTML() 
        out += html.Tag('Blockquote',tout)
        
        us.unit = self.entity['uid']
        friends.append(us)
        
        
        # Fish out all subordinates at all levels
        subs = self.entity.AllSubordinates()
        for i in range(len(subs)):
            cnt = self.entity.Contact(subs[i])
            if cnt != None and cnt.Type() != 'undetected':
                temp = cnt.Duplicate('encode')
                temp.UpdateField('nature','reported')
                friends.append(temp)
        
        
        return out, eny, friends
    
    def REPORT_Engagement(self):
        '''!
           Prepare a report about engagement eng and return as a string.
        '''
        out = html.Tag('p',html.Tag('B','Engagement Report'))
        # for each Engagements
        for eng in self.entity['ground engagements']:
            if eng:
                out += eng.Report(self.entity)
        # 
        return html.Tag('div', out)
    
    def REPORT_logistics(self):
        '''!
           Prepare a report about logistics
           \todo Use obsolete Deliver Supply tasks
        '''
        out = html.Tag('h3','Logistics Report')
        # CSSUnit and ressuply policies
        cssunit = ''
        css = self.SolveCSSUnit()
        cssroute = self.SolveCSSRoute()
        policies = self.PolicyMinMaxSupplyLevels()
        if css == None:
            cssunit = 'We have yet to be assigned a supply source.'
        elif css == self.entity:
            cssunit = 'We have not been assigned a supply source from a higher echelon yet.'
        elif self.entity['TOE'] != 'convoy':
            # Write up about CSS source and route.
            ttime = self.EstimateConvoyTransitTime()
            ttime = int(ttime * 60)
            hr = ttime / 60
            min = ttime % 60
            if hr:
                ttime = '%dh%02d min'%(hr,min)
            else:
                ttime = '%02d min'%(min)
            cssunit = 'Our current CSS unit is %s. We are located some %.2f Km from the ressuply area and should plan for a train transit time of %s. '%(css.GetName(), (self.entity['position']-css['position']).length(),ttime)
            
        pol = 'We are currently required to maintain between %.2f and %.2f basic loads. Here follows our current inventory:'%(policies[0],policies[1])
        
        out = out + html.Tag('P',cssunit+pol) + html.Tag('blockquote',self.entity['logistics'].Report(self.entity))
        
        if type(self.entity['logistics']) == type(CSSlogistics()):
            # burden and available freight
            temp = 'Our transportation assets are used at %d%% under projected supply requirements for our serviced units; with %.1f STON left of freight currently available. Note that 100%% means there is no freight that can be allocated for contingency plan even while assuming an optimized routine schedule.'%(100*self.entity['logistics'].ComputeRessuplyBurden(self.SolveSupportedUnits()),self.entity['logistics']['freight'])
            out = out + html.Tag('p',temp)
            #
            myconvoys = self.SolveSubordinateConvoys()
            if myconvoys:
                cvlist = 'Here is a list of the current detachments performing supply train tasks : '
                header = ['Detachment','SUPREQ (STON)','Supported Unit']
                table = [header]
                for i in myconvoys:
                    name = i.GetName()[:i.GetName().find('Tk')-1]
                    # Find ressuply task
                    qunty = ''
                    tgt = ''
                    for t in i['OPORD'].GetTaskList():
                        if t['type'] == 'Drop-Off':
                            # Retrieve the package to load
                            qunty = '%.2f STON'%(float(t['cargo']))
                            tgt = self.entity.sim.AsEntity(t['recipient']).GetName()
                            break
                    table.append([name,qunty,tgt])
                out = out + cvlist + html.Tag('small',html.Table(table))
                
        
        return html.Tag('div',out)

    def REPORT_Command(self):
        '''!
           Report on command and control.
        '''
        out = html.Tag('H3', 'Command, Control and Communication.')
        out1 = html.Tag('B', 'C2 level   : ') + self.entity['C4I'].AsStringCommand(self.entity.C2Level()) + ' (%d%%)'%(100*self.entity.C2Level())
        if self.entity.GetHQ(): 
            out1 = out1 + '<BR>' + html.Tag('B', ' C4I level   : ') + self.entity['C4I'].AsStringCommand(self.entity.C3Level()) + ' (%d%%)'%(100*self.entity.C3Level())
        out1 = out1 + '<BR>'
        out1 = out1 + 'Suppression: ' + self.entity['C4I'].AsStringSuppression(self.entity.GetSuppression()) + ' (%d%%)<BR>'%(100*self.entity.GetSuppression())
        out1 = out1 + 'Fatigue    : ' + self.entity['C4I'].AsStringFatigue(self.entity.GetFatigue()) + ' (%d%%)<BR>'%(100*self.entity.GetFatigue())
        out1 = out1 + 'Morale     : ' + self.entity['C4I'].AsStringMorale(self.entity.GetMorale()) + ' (%d%%)<BR>'%(100*self.entity.GetMorale())
        out = out + html.Tag('blockquote',out1)
        return html.Tag('div',out)
    
    
    def REPORT_position(self):
        '''!
           Location and stance.
           OUTPUT : A string.
        '''
        head = html.Tag('H3','Deployment Details')
        out =  'We are located at MGRS %s in %s stance. '%(self.map.MGRS.AsString(self.entity['position'],2),self.entity.GetStance())

        # Distance from HQ
        if self.entity.GetHQ():
            bear = self.entity.GetHQ()['position'].BearingTo(self.entity['position'])
            bear[0] = (bear[0] / 3.14159) * 180
            if bear[0] < 0.0:
                bear[0] = bear[0] + 360
            out = out + 'Some %.1f Km bearing %s from your position. '%(bear[1],('00'+str(int(bear[0])))[-3:])
        # terrain report
        terrain = self.map.SampleTerrain(self.entity.Footprint())
        out = out + 'We are deployed over %.1f km^2. The terrain profile in our footprint is: '%(self.entity.Footprint().Area())
        for i in terrain:
            out = out + '%d%% %s, '%(100*terrain[i], i)
        out = out[:-2] + '. '
        if self.entity['readiness'] != 0.0:
            hr = int(self.entity['readiness'])
            minutes = int(self.entity['readiness'] * 60) % 60
            if hr and minutes:
                ts = '%dh %dm'%(hr,minutes)
            elif hr:
                ts = '%dh'%(hr)
            else:
                ts = '%d mins'%(minutes)
            out = out + 'We are ready to get underway in %s. '%(ts)
        return head + html.Tag('p',out)
    
    def REPORT_CurrentTask(self):
        '''!
           Format depending on tasks.
        '''
        out = html.Tag('H3','Maneuver Report')
        # Get Task
        task = self.entity['OPORD'].GetCurrentTask()
        
        # Default report
        if task == None:
            return ''
            return out + html.Tag('p','Nothing to Report')
        
        # custom report
        return html.Tag('div',out+task.AsHTML(self))
    
    def REPORT_CapacityStrenght(self):
        '''!
           Report on the Capacity of the entity to perform its tasks.
        '''
        # Out string
        out = html.Tag('H3', 'Capacity and Strenght')
        
        # Relative Combat strenght
        #R = self.entity['combat'].RawRCP()/self.entity['combat']['TOE RCP']
        R = 0.0
        temp = 'We are operating at %d%% of our TOE allocation. '%(int(100*R))
        
        KIA,WIA,dst,dmg = self.EstimateCasulatiesFigures()
        temp += 'We report %d KIA/MIA and %d WIA. We also report %d destroyed and %d dammaged vehicles that possibly can be salvaged. '%(KIA, WIA, dst, dmg)
        
        out += html.Tag('p',temp)
        
        return out
    
    #
    # Timing
    def EstimateOPORDTiming(self, opord):
        '''! \brief Project planned time and logistics requirements
           \param opord : An OPORD
           
           Propagate/Populate the tasks structures with planned end/begin time, using task_time and begin time data
        '''
        # Map in time
        mytime = self.clock
        for k in range(len(opord.GetTaskList())):
            i = opord.GetTaskList()[k]
            # Ignore task already finished
            if i.EndTime():
                mytime = i.EndTime()
                continue
            
            # Push within the task/subtask the timing
            mytime = i.PushPlannedBeginTime(mytime, self.entity['OPORD'].GetHhour())
    
    def EstimateConvoyTransitTime(self):
        '''! \brief Estimate time of transit for a supply truck to get there.
             \return Transit time in hours [float]
        '''
        # do you know where is the CSS (always true)
        myCSS = self.SolveCSSUnit()
        myroute = self.SolveCSSRoute()
        
        # If no CSS
        if myCSS == None:
            self.data['attn'].append('CSS unit')
            return 0.0
        
        # Pre computed
        if self.data.has_key('convoy transit time'):
            if self.map.MGRS.AsString(self.entity['position']) == self.data['convoy transit time']['mypos'] and self.map.MGRS.AsString(myCSS['position']) == self.data['convoy transit time']['CSS pos']:
                return self.data['convoy transit time']['transit time']
        
        
        # Path to CSS
        tk = {'destination':myCSS['position'].AsVect(), 'initial position':None}
        if myroute:
            tk['route'] = myroute
            # We want it from unit to CSS so we can use our own agent to do the estimation
            tk['route'].reverse()
        self.SolvePath(tk)
        #self.map.DrawPath(tk['waypoints'])
        
        # Assume a convoy's base speed of 35 km/hr
        mytime = self.EstimateTransitTime(tk['waypoints'],35.0)
        self.data['convoy transit time'] = {'transit time':mytime, 'mypos':self.map.MGRS.AsString(self.entity['position']),'CSS pos':self.map.MGRS.AsString(myCSS['position'])}
        
        return mytime
    
    def EstimateTransitTime(self, path, baseSP = None):
        '''!
           Will default to the unit's base speed.
        '''
        # Set basSP
        if baseSP == None:
            baseSP = self.entity['movement']['speed']
            
        return self.map.EffectivePathLength(path, frict=self.entity['movement'].frictions) / baseSP
    
    
    def EstimateSupplyRequired(self, act, ctime = 1.0):
        '''! \brief Estimate from an activity list and duration
           \param act (\c list(string)) A list of activities
           \param ctime (\c float) Time elapsing in hours [1 hour]
           \return \c supply_package
           \bug Doesn't query within sub task to get precise estimates. May cause significant discrepancies
           if the consumption isn't uniformly distributed.
        '''
                
        # Make sure the idle consumption is included
        if not 'idle' in act:
            act.append('idle')
        
        return self.entity['logistics'].SupplyExpenditure(1,act,ctime, self.entity)

    def EstimateTimeAtCargo(self, tcargo):
        '''! \brief Estimate when a entity will be down to the levels in arg tcargo
             \param tcargo [supply_package] Target levels
             
             Here is a synopsis of tasks done in this method:
             -# re-time the OPORD to make sure that the estimates are as good as possible.
             -# Find current subtask, time and cargo.
             -# Substract the supply required for each subtask until tcargo is reached. Use proportional spending.
             -# If ongoing task, or no task, divide the remaining cargo to threshold by the rate of consumption.
             
             \return Target Time (\c datetime)
             
             \note Subfunction of self.EstimateTimeToRessuply() which makes the first statment redundant.
        '''
        # refresh time estimated to current situation.
        self.EstimateOPORDTiming(self.entity['OPORD'])
        
        # Begin at the current task.
        ctask = self.entity['OPORD'].GetCurrentSubTask()
        ctime = deepcopy(self.clock)
        cargo = self.entity['logistics']['cargo']
        
        # Quickcheck  whether we already run out If already reached, returns NOW!
        if cargo <= tcargo:
            return ctime
    
        # If the unit has some pre-determined tasks to perform, substract the supply requirements.
        if ctask != None:
            # From current task to end
            for task in self.entity['OPORD'].GetExpandedTaskList()[self.entity['OPORD'].GetExpandedTaskList().index(ctask):]:
                if task.TaskTime() == 0.0:
                    break
                # Add concurent LOGPAC within this task's 
                for i in self.issuedSUPREQs:
                    if i['ETA'] > task['planned begin time'] and i['ETA'] <= task['planned end time']:
                        cargo = cargo + i['COMMODITY']
                        
                # find when the task is planned to be finished
                if (cargo - task.Supplyrequired()) <= tcargo:
                    # Simple fractions of a task
                    ratio = (cargo - tcargo) / task.Supplyrequired()
                    return ctime + timedelta(hours=ratio * task.TaskTime())
                cargo = cargo - task.Supplyrequired()
                ctime = ctime + timedelta(hours=task.TaskTime())
        
        act = []
        if self.entity.GetStance() == 'support':
            act.append('support')
            
        # Eligible SUPREQ
        supreqs = []
        for i in self.issuedSUPREQs:
            if i['ETA'] > ctime:
                supreqs.append(i)
        
        # Perform a remaining / rate to get a time estimate otherwise.
        remain = cargo - tcargo
        hourlyrate = self.EstimateSupplyRequired(act) # 1 hr by default
        
        # Time until the first item reaches threshold. This div does a pairwise division.
        dtime = max(min((remain / hourlyrate).values()),0.0)
        ctime = ctime + timedelta(hours=dtime)
        
        # Tricky loop, goes on for all extensions granted by concurent supreqs
        while 1:
            dtime = 0.0
            for i in supreqs:
                if i['ETA'] <= ctime:
                    dtime = max(min((i['COMMODITY'] / hourlyrate).values()),0.0)
                    # Dings the supreq so its counted only once
                    supreqs.remove(i)
            if dtime:
                # Push the time further and restart
                ctime = ctime + timedelta(hours=dtime)
            else:
                break
        return ctime
    
    def EstimateCargoAt(self, T, opord = None):
        '''! \brief Estimate the cargo in the unit's store at time T.
             \param T : a datetime instance
             \parma opord : an optional opord to consider (default to current) 
            \return A logistic package.
        '''
        # Overide/default opord
        if opord == None:
            opord = self.entity['OPORD']
            
        # Ensure the most recent timing estimates.
        self.EstimateOPORDTiming(opord)
        
        # Begin at the current task.
        ctask = opord.GetCurrentSubTask()
        ctime = deepcopy(self.clock)
        
        # The cargo cursor which will decrease as we walk the tasklist
        cargo = self.entity['logistics']['cargo']
        
        # Planned concurent ressuply
        for i in self.issuedSUPREQs:
            if i['ETA'] <= T:
                cargo = cargo + i['COMMODITY']
        
        if ctask != None:
            # From current task to end
            for task in opord.GetExpandedTaskList()[opord.GetExpandedTaskList().index(ctask):]:
                # If there is no task time, the task that will be effective until running out is this one
                if not task.TaskTime():
                    break
                # find when the task is planned to be finished
                if (ctime + timedelta(hours=task.TaskTime())) >= T:
                    # Simple fractions
                    ratio = (T - ctime).seconds / timedelta(hours=task.TaskTime()).seconds
                    return cargo - (task.SupplyRequired() * ratio)
                
                # Decrement the cargo cursor and move on to the next task
                cargo = cargo - task.SupplyRequired()
                ctime = ctime + timedelta(hours=task.TaskTime())
                ctask = task
        
        # Get the last task
        if ctask:
            act = ctask.ConsumptionCodes()
        else:
            # No task, just exist.
            act = ['idle']
        
        # Get a hourly consumption rate
        hourlyrate = self.EstimateSupplyRequired(act, 1.0)
        
        # time left idle (dtime will be positive here, so I deleted the check.)
        dtime = (T - ctime).seconds / 3600.0
        cargo = cargo - (hourlyrate * dtime)
        
        # Outstanding expenses
        return cargo
        
    
    def EstimatePositionAt(self, T, opord = None):
        '''! \brief Returns a probably position at time T.
             \param T  [\c datetime] Timestamp for the projection.
             \param opord [OPORD] Optional alternative OPORD instance to consider.
             \return A vect_3D instance.

           Notes:
                 Scan tasks with latest time estimates to find the Active task at time T
                 Evaluate the position at an intermediate time.
                 
                 Of course, This estimate isn't going to be very accurate for transit in unpredictable,
                 or busy, terrain.
                 
                 \note The precision on the result will be +/- sample in radius from the actual position, but
                 yet again, the real position isn't all that precise now that positions are treated as footprints.
                 \bug Ignored friction other than terrain.
        '''
        # Default/overide OPORD
        if opord == None:
            opord = self.entity['OPORD']
            
        # Ensure the most recent timing estimates.
        self.EstimateOPORDTiming(opord)
        
        # Begin at the current task.
        ctask = opord.GetCurrentSubTask()
        
        # Cursors
        ctime = deepcopy(self.clock)
        newpos = deepcopy(self.entity['position'])
        stance = self.entity.GetStance()
        
        for task in opord.GetExpandedTaskList()[opord.GetExpandedTaskList().index(ctask):]:
            # never ending task.
            if task.TaskTime() == 0.0:
                return newpos
            # find when the task is planned to be finished, act if ends after T
            if (ctime + timedelta(hours=task.TaskTime())) >= T:
                if task.has_key('waypoints'):
                    # Get samples
                    samples = self.map.SamplePath(task['waypoints'])
                    
                    for i in range(1,len(samples)):
                        # Distance
                        distance = (samples[i] - samples[i-1]).length()
                        
                        # Attempt to adjust the stance cursor
                        if task.has_key('stance'):
                            stance = task['stance']
                        
                        # Ignore Traffic
                        speed = self.entity['movement'].Speed(self.map.TerrainUnder(samples[i]),self.entity.C2Level(),stance)
                        d_time = distance/speed
                        
                        # Increment the time cursor
                        ctime = ctime + timedelta(hours=d_time)
                        
                        # Return the right sample if times run out.
                        if ctime >= T:
                            return samples[i]
                else:
                    # Last recorded position 
                    return newpos
                # Update position
                if task.has_key('destination'):
                    newpos = task['destination']
                    
                # Update stance
                if task.has_key('final_stance'):
                    stance = task['final_stance']
                    
                #Update clock
                ctime = ctime + timedelta(hours=task.TaskTime())
                
    
    def EstimateTimeToRessuply(self):
        '''!
           Try to predict when the unit will reach the point at which it must ressuply
           assuming continuing ops.
           OUPUT : time left in hour.
        '''
        minsup, maxsup = self.PolicyMinMaxSupplyLevels()
        minsup = self.entity['logistics']['capacity'] * minsup
        # Delta of time estimate to get to minsup
        diff = self.EstimateTimeAtCargo(minsup) - self.clock
        return (diff.days * 24.) + (diff.seconds / 3600.00)
    
    #
    # Map manipulations
    def SetMapOverlay(self, overlay):
        self.overlay = overlay
        
    def GetControlMeasure(self, name):
        '''! \brief Retrieve control measure from overlay
             \param name support wildcards * for label, not for tag
             
             name TAG label eg. AO ZORRO
        '''
        # tag only
        if name.find('*'):
            tag = name.split(' ')[0]
            return self.overlay.GetElementByTag(tag)
    
        # exact name
        return self.overlay.GetElement(name)
            
    def SolvePath(self, task):
        '''!
                Solve for the series of WP to cross to get to the destination.
                Simply make a 1 WP path for now.
        ''' 
        # Pre-determined WP
        wp = []
        if task.has_key('route') and task['route']:
            route = self.SolveRouteAsList(task['route'])
            for i in route:
                wp.append(self.SolveCoordAsVect(i))
                
        task['destination'] = self.SolveCoordAsVect(task['destination'])
        
        if task['initial position'] != None:
            wp = [task['initial position']] + wp + [task['destination']]
        else:
            wp = [copy(self.entity['position'].AsVect())] + wp + [task['destination']]
            if (self.entity['position']-task['destination']).length() < 0.1:
                task['waypoints'] = wp
        i = 0
        task['waypoints'] = self.map.FindPath(wp,self.entity['movement'].friction_dict())
          

    def GetControlMeasure(self, CM):
        return self.overlay.GetElement(R)
    def SolveRouteAsList(self, R):
        '''! \brief make sure that the output is a list of vect_5D, dig in the Overlay is R is a string.
        '''
        if type(R) == type(''):
            # get from overlay
            line = self.overlay.GetElement(R)
            if line:
                return line
        return R
    
    def SolveAreaAsList(self, A):
        '''! \brief make sure that the output is a list of vect_5D, dig in the Overlay is R is a string.
        '''
        if type(A) == type(''):
            # get from overlay
            line = self.overlay.GetElement(A)
            if line:
                return line
        return A
    

    
    def SolveCoordAsVect(self, C):
        '''!
            Convert coord in any format so it can be taken up by the pathfinding algorithm.
        '''
        if C.__class__ == vect_5D().__class__:
            return C
        elif C.__class__ == vect_3D().__class__:
            return C
        elif C.__class__ == position_descriptor().__class__:
            # This should not happen, 
            return vect_5D(C.x, C.y, C.z, C.course,C.rate)
        elif type(C) == type(''):
            try:
                temp = self.map.MGRS.AsVect(C)
                if temp:
                    return temp
            except:
                p = self.overlay.GetElement(C).Center()
                if p:
                    return vect_5D(p.x,p.y)
        return None
                
    def SolveArea(self, area):
        '''! \brief Make sure that area is an operational_area and not an overlay marking
              (which would be a string).
        '''
        if type(area) == type(''):
            overlay = self.entity['OPORD'].GetOverlay()
            return overlay.GetElement(area)
        
        return area
            
    
    #
    # Inner data manipulations (OPORD and SOP)   
    def commUID(self):
        '''! \brief Returns a communication UID 
        '''
        if not self.data.has_key('comm UID'):
            self.data['comm UID'] = 1
        self.data['comm UID'] += 1
        
        return self.data['comm UID'] - 1
    
    def PolicyMinMaxSupplyLevels(self):
         # Find Standing orders, first directly on OPORD
        minsup = maxsup = 0.0
        
        opord = self.entity['OPORD']
        sop = self.entity['SOP']
        
        opord_pol = opord.GetSupplyPolicies()
        sop_pol   =   sop.GetSupplyPolicies()
        
        for i in ['minimum','maximum']:
            if opord_pol.has_key(i):
                temp = opord_pol[i]
            elif sop_pol.has_key(i):
                temp = sop_pol[i]
            else:
                temp = 0.0
            if i == 'minimum':
                minsup = temp
            else:
                maxsup = temp
            
        return minsup, maxsup
   

    def SolveCSSRoute(self):
        '''
           find the LOC from the OPORD and SOP.
        '''
        ov = self.entity['OPORD'].GetOverlay()
        if not ov:
            return []
        
        msr = self.entity['OPORD'].GetMSR()
        if not msr:
            msr = self.entity['SOP'].GetMSR()
        if msr:
            gfx = ov.GetElement(msr)
            if gfx:
                return gfx.shape
            
        return []
   
    def SolveCSSUnit(self):
        '''!
           Find the CSS unit under the following orders:
             1) OPORD
             2) SOP
        '''
        temp = self.entity['OPORD'].GetCSS()
        if type(temp) == type(1):
            return self.entity.sim.AsEntity(temp)
        
        temp = self.entity['SOP'].GetCSS()
        if type(temp) == type(1):
            return self.entity.sim.AsEntity(temp)
        
        return None
    
    def SolveSupportedUnits(self, addconvoy = False):
        '''!
           Return a list of supported units.
           Cheat!! Read the OOB instead! TODO
        '''
        out = []
        for i in self.entity.sim.OOB:
            if i == self.entity:
                continue
            if self.entity == i['agent'].SolveCSSUnit():
                if i['TOE'] != 'convoy' or addconvoy:
                    out.append(i)
        return out
    
    def SolveSubordinateConvoys(self):
        '''!
           return a list of subordinate convoys
        '''
        out = []
        for i in self.entity['subordinates']:
            if i['TOE'] == 'convoy':
                out.append(i)
            
        return out
    
    def SolveInitiateEngagement(self):
        '''!
           Choose whoe to attacck and engage AND/OR break engagements if out of range.
        '''
        # Choose a Foe from the list of potential foes (built during detection phase)
        foe = self.SolveChooseEngageFoe()
        
        # Register the engagement
        if foe:
          self.entity.sim.EngagementBegin(self.entity,foe)
          
    def SolveNextRoutineRessuplyTime(self):
        '''! \brief Returns a datetime instance build from OPORD instruction or a 
              default to the following 0000.  
        '''
        # From OPORD
        temp = self.entity['OPORD'].GetRoutineRessuplyTime()
        if not temp:
            temp = ['0000']
            
        # build times today for this.
        times = []
        now = datetime.now()
        for i in temp:
            ttime = datetime(now.year, now.month, now.day,int(i[:2]), int(i[2:]))
            while ttime - self.clock < timedelta():
                ttime += timedelta(hours=24)
            times.append(ttime)
        times.sort()
        return times[0]
          
    def SolveIFF(self, color):
        if color != self.entity['side']:
            return 'ENY'
        return 'FR'
    
    def SolveChooseEngageFoe(self):
        '''!
           Decides if a ground engagement should be initiated.
        '''
        # Make sure this exists
        if not self.entity.has_key('ground engagements'):
            self.entity['ground engagements'] = []
    
        # Can't engages new opponents if already committed.
        if self.entity['ground engagements']:
            return False
        
        # If no potential oppoents, aborts.
        if self.potentialengagements == []:
            return False
        
        # Fetch Engagement policies from OPORD/SOP
        policy = None
        if self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS'].has_key('ENGAGEMENT'):
            policy = self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS']['ENGAGEMENT']
        if not policy:
            if self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS'].has_key('ENGAGEMENT'):
                policy = self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS']['ENGAGEMENT']
        if not policy:
            # Do not engages because of lack of orders to do so.
            return False
    
        # Weapons tight
        if policy.has_key('WEAPON TIGHT'):
            return False
        
        # Return
        return self.SolvePriorityTarget(self.potentialengagements)

    
    def SolveWithdrawal(self, engag):
        '''!
           Decided whether to pull out of an engagement.
        '''
        # Fetch Engagement policies from OPORD/SOP
        policy = None
        if self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS'].has_key('DISENGAGEMENT'):
            policy = self.entity['OPORD']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS']['DISENGAGEMENT']
        if not policy:
            if self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS'].has_key('DISENGAGEMENT'):
                policy = self.entity['SOP']['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS']['DISENGAGEMENT']
        if not policy:
            # Do not disengage because of lack of orders to do so.
            return False
        
        # Catch the bail-out threshold
        if policy.has_key('threshold'):
            if self.entity['combat']['RCP'] <= (engag.OOB[self.entity['uid']]['initial RCP'] * (1-policy['threshold'])):
                # Need to Withdraw
                return True
        return False
               
            
    def SolveActivitiesFromTask(self, task_type):
        out = []
        if task_type == 'Relocate' or task_type == 'Redeploy':
            out.append('transit')
        if task_type == 'Ressuply' or task_type == 'Support':
            out.append('support')
        return out
    
    def InitializeOPORD(self):
        '''!
                Begin OPORD implementation
        '''
        # Initialize cursor to first non-completed task
        self.entity['OPORD'].AutoCursor()
        if self.entity['OPORD']['sent timestamp'] == self.clock:
            self.log('=====================================================')
            self.log('Begin Executing OPORD', 'operations')
        

    def CreateDetachment(self):
        if not self.data.has_key('detachments'):
            self.data['detachments'] = []
        # Find suitable detachment
        for i in range(1000)[1:]:
            if not str(i) in self.data['detachments']:
                self.data['detachments'].append(str(i))
                return str(i)
    
    def ReleaseDetachment(self, detn):
        '''!
           INPUT:
                detn --> string
        '''
        try:
          self.data['detachments'].remove(detn)
          return True
        except:
          self.log('Detachment %s could not be removed'%(detn),'personel')
          return False
      
    # File Ops
    #
    def PrePickle(self):
        self.entity = None
        for i in range(len(self.potentialengagements)):
            self.potentialengagements[i] = self.potentialengagements[i]['uid']
        
    def PostPickle(self, parent):
        self.entity = parent
        for i in range(len(self.potentialengagements)):
            self.potentialengagements[i] = parent.sim.AsEntity(self.potentialengagements[i])
        
    def Write(self, name, text):
        '''!
           Write the text to a file in the entity folder
        '''
        fh = open(os.path.join(self.entity['folder'],name),'w')
        fh.write(text)
        fh.close


class agent_CO(agent):
   '''!
        \brief An Agent that manage more than one units as an echelon/battlegroup.
        
        This class intend to separate the management of entities from these of battlegroups
        and echelon. This separation is necessary because the agent class, implementing XO tasks,
        is already quite large and complex.
   '''
   def __init__(self, entity, map):
       '''! \param XO, the agent of the HQ for the echelon
        '''
       agent.__init__(self, entity, map)
       
       self.XO = entity['agent']
       
   # Reporting
   def PrepareSITREP(self):
       '''! \brief Prepare a report on the battle group, including all the units under OPCON.
       
           The game should use this funciton for all HQ units that are managing echelons, unless the owning
           player of this HQ explicitely request a SITREP for the HQ unit.
       '''
       # HTML render
       nm = self.entity.Echelon()
       if not nm:
           nm = self.entity.GetName()
       title = 'SITREP for %s at time %s\n'%(nm, self.clock.strftime('%m-%d %H%M ZULU'))
       out = html.Tag('H1',title)
        
       # Contacts
       temp, eny, friends = self.REPORT_Contacts()
       out += temp
       
               
       # Adm (logistics) ###############################
       # Human factor(s), fatigue, supression and morale
       out = out + html.Tag('H2','C. Admin') + '<HR>'
       temp=  html.Tag('p',self.REPORT_position())
       
       # Report engagement status if applicable
       if self.entity['ground engagements']:
           temp += html.Tag('p', self.REPORT_Engagement())
           
       temp += html.Tag('p',self.REPORT_CapacityStrenght())
       temp += html.Tag('p',self.REPORT_Command())
       temp += html.Tag('p',self.REPORT_CurrentTask())
       temp += html.Tag('p',self.REPORT_logistics())
       
       out += html.Tag('BLOCKQUOTE',temp)
       
       out = html.HTMLfile('SITREP',out)
   
       # Other #########################################
       
       # timing
       self.data['last SITREP'] = self.clock
       
       # Fish out all subordinates at all levels
       subs = self.entity.AllSubordinates()
       for i in range(len(subs)):
           cnt = self.entity.Contact(subs[i])
           if cnt != None:
               temp = cnt.Duplicate('encode')
               temp.UpdateField('nature','reported')
               friends.append(temp)
               
       
       # Return the actual data structure
       mysit = SITREP(self.entity, eny, friends, out, self.entity.C3Level())
       mysit.PrePickle()
       self.entity.Send(mysit)
       # Log it to HD
       # Make HTML file
       hs = html.HTMLfile(title,str(mysit))
       self.Write('%s.SITREP.html'%(self.clock.strftime('%m%d.%H%M')),hs)
       return mysit        
   
   def REPORT_Contacts(self):
       '''! \brief Reports only direct contact to the overall team. 
            Connection at the time of the preparation must be validated using a 
            
            \param comm A map of valid connection to subordinates.
            
            \return Section A and B of the SITREP.
       '''
       # Contacts
       out = ''
       eny = []
       friends = []
       # contacts
       contacts = self.GetContactList()
       
       # Pointer to subordinates
       echelon  = self.entity.EchelonSubordinates()
       attached = self.entity.AttachedSubordinates()
       sub      = self.entity.Subordinates()
       
       # ENY Situation ###################################
       out += html.Tag('H2','A. Eny Forces') + '<HR>\n'
       tout = ''
       for i in contacts:
           if i.IsDirectObs('echelon'):
               temp = i.Duplicate('encode')
               if self.SolveIFF(i.fields['side']) != 'FR':
                   eny.append(temp)
                   tout += i.AsHTML()
       if tout == '':
           tout = 'None to report.'
       # Add the eny string
       out += html.Tag('BLOCKQUOTE', tout)   
               
       # Own Tps #######################################
       subord = []
       attch = []
       others = []
       for i in contacts:
           if i.IsDirectObs('echelon'):
               if i.unit in echelon:
                   subord.append(i.Duplicate())
               elif i.unit in attached:
                   attch.append(i.Duplicate())
               else:
                   if i.IsDirectObs('echelon'):
                       temp = i.Duplicate('encode')
                       if self.SolveIFF(i.fields['side']) == 'FR':
                           others.append(i.Duplicate())
            
       out += html.Tag('H2','B. Friendly Forces') + '<HR>'
       # Location and Stance (self)
       us = self.ContactDefineSelf()
       tout = html.Tag('STRONG','Reporting Unit: ') +  ' <BR>'
       tout +=  us.AsHTML()
       
       # Echelon Subordinates
       if subord:
           tout += html.Tag('STRONG','Subordinate Unit(s): ') +  ' <BR>'
           for i in subord:
               tout += i.AsHTML()
       if attch:
           tout += html.Tag('STRONG','Attached Unit(s): ') +  ' <BR>'
           for i in attch:
               tout += i.AsHTML() 
               
       # Others friends 
       if others:
           tout += html.Tag('STRONG','Attached Unit(s): ') +  ' <BR>'
           for i in others:
               tout += i.AsHTML()
               
       out += html.Tag('Blockquote',tout)
       
       # Build the friend list
       friends = []
       for i in sub:
           cnt = self.GetContact(i)
           if cnt != None:
               friends.append(cnt)
       us.unit = self.entity['uid']
       friends.append(us)
       
       
       return out, eny, friends
   
   def REPORT_logistics(self):
        '''!
           Prepare a report about logistics
           \todo Use obsolete Deliver Supply tasks
        '''
        out = html.Tag('h3','Logistics Report')
        
        # Get the inventory for all subordinates
        sub = self.entity.Subordinates() + [self.entity]
        
        # cargo (local copy)
        cargo = self.entity.GetCargo() * 1.0
        capacity = self.entity.GetCapacity() * 1.0
        freight = supply_package()
        for s in sub:
            cargo = cargo + s.GetCargo()
            capacity = capacity + s.GetCapacity()
            freight += s['logistics']['freight']
        
        temp = system_logistics()
        temp['cargo'] = cargo
        temp['capacity'] = capacity
        temp['freight'] = freight
        
        out += temp.Report()
                
        
        return html.Tag('div',out)
    
   def REPORT_Command(self):
       '''! \brief Command report for a multiple units formation.
       '''
       # Get Average values.
       com = 0.0
       sup = 0.0
       fat = 0.0
       mor = 0.0
       
       for i in self.entity.Subordinates():
           com += self.entity.CommLevelTo(i)
           sup += self.entity.GetSuppression()
           fat += self.entity.GetFatigue()
           mor += self.entity.GetMorale()
       
       # compute averages    
       N = len(self.entity.Subordinates())
       com /= N
       sup /= N
       fat /= N
       mor /= N
        
       out = html.Tag('H3', 'Command, Control and Communication.')
       out1 = '<BR>' + html.Tag('B', ' HQ C2 level   : ') + self.entity['C4I'].AsStringCommand(self.entity.C2Level()) + ' (%d%%)'%(100*self.entity.C2Level())
       out1 += '<BR>' + html.Tag('B', ' C4I level   : ') + self.entity['C4I'].AsStringCommand(com) + ' (%d%%)'%(100*com)
       out1 = out1 + '<BR>'
       out1 = out1 + 'Suppression: ' + self.entity['C4I'].AsStringSuppression(sup) + ' (%d%%)<BR>'%(100*self.entity.GetSuppression())
       out1 = out1 + 'Fatigue    : ' + self.entity['C4I'].AsStringFatigue(fat) + ' (%d%%)<BR>'%(100*self.entity.GetFatigue())
       out1 = out1 + 'Morale     : ' + self.entity['C4I'].AsStringMorale(mor) + ' (%d%%)<BR>'%(100*self.entity.GetMorale())
       out = out + html.Tag('blockquote',out1)
       return html.Tag('div',out)
   
   def REPORT_CapacityStrenght(self):
        '''!
           Report on the Capacity of the entity to perform its tasks.
        '''
        # Out string
        out = html.Tag('H3', 'Capacity and Strenght')
        
        # Relative Combat strenght
        R = self.entity['combat'].RawRCP()/self.entity['combat']['TOE RCP']
        temp = 'We are operating at %d%% of our TOE allocation. '%(int(100*R))
        
        KIA = WIA = dst = dmg = 0
        for S in self.entity.Subordinates()+[self.entity]:
            t1,t2,t3,t4 = S['agent'].EstimateCasulatiesFigures()
            KIA += t1
            WIA += t2
            dst += t3 
            dmg += t4
            
        
        temp += 'We report %d KIA/MIA and %d WIA. We also report %d destroyed and %d dammaged vehicles that possibly can be salvaged. '%(KIA, WIA, dst, dmg)
        
        out += html.Tag('p',temp)
        
        return out
    
   def REPORT_position(self):
        '''!
           Location and stance.
           OUTPUT : A string.
        '''
        head = html.Tag('H3','Deployment Details')
        out =  'Our HQ element is located at MGRS %s in %s stance. '%(self.map.MGRS.AsString(self.entity['position'],2),self.entity.GetStance())

        # Distance from HQ
        if self.entity.GetHQ():
            bear = self.entity.GetHQ()['position'].BearingTo(self.entity['position'])
            bear[0] = (bear[0] / 3.14159) * 180
            if bear[0] < 0.0:
                bear[0] = bear[0] + 360
            out = out + 'Some %.1f Km bearing %s from your position. '%(bear[1],('00'+str(int(bear[0])))[-3:])
            
        # terrain report
        footprint = self.SolveFootprint()
        terrain = self.map.SampleTerrain( footprint )
        out = out + 'The terrain profile in our footprint covers %d Km square and is made of: '%(footprint.Area())
        for i in terrain:
            out = out + '%d%% %s, '%(100*terrain[i], i)
        out = out[:-2] + '. '
       
        return head + html.Tag('p',out)
    
   # Managing Subordinates
   def DirectContact(self, E):
       '''! \brief Confirms that a subordinate echelon has direct observation of the 
            entity behind the contact track.
            This verification is done by looking up the contact in the last SITREP sent.
            \return None or the subordinate in contact.
       '''
       return False
   
   def SolveFootprint(self):
       '''! \brief make an agglomerate footprint for the whole echelon.
            Is defined as the convex polygon of the footprint of all subordinates
       '''
       
       V = self.entity.Footprint().vertices()
       for i in self.entity.Subordinates():
           # Get Contact
           C = self.entity.Contact(i)
           if C and C.fields['Echelon Footprint']:
               V += C.fields['Echelon Footprint'].vertices()
           elif C and C.location:
               V += C.location.footprint.vertices()
           
        
       return geometry_rubberband().Solve(V)
   
   

if __name__ == '__main__':
    import syspathlib
    
import unittest

class AgentTest(unittest.TestCase):
    pass

if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(AgentTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)