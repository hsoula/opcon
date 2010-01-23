'''!
        Intelligence model and contact data structure
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
from random import random, choice
from math import pi

from copy import copy

from sandbox_log import *
from sandbox_sensor import *
from sandbox_exception import SandboxException


import Renderer_html as html

from sandbox_keywords import dch_size_denomination
from GUIMapSym import MapSym, Sym_denom
from sandbox_geometry import geometry_rubberband

from sandbox_TOEM import TOEMargument

import system_base


class sandbox_contact:
  '''! \brief contact information data structure.
  '''
  def __init__(self, myunit= None):
    # Identifier for the target unit (could be a pointer)
    self.unit = myunit
    
    # Reliability
    self.p_right = 0.5
    self.rating = 0
    self.deception = 0
    
    # Status (by default, set to undetected)
    self.status = 'undetected'
  
    # Information
    self.fields = {}
    self.fields['equipment'] = {}
    self.fields['equipment']['personel'] = []
    self.fields['equipment']['vehicle'] = []

    # Direct subordinates in direct contact
    self.direct_subordinates = []
    
    # Internal attributes for faster computation
    self.location = None
    
    # Time of last modification
    self.timestamp = None
    
  def __nonzero__(self):
    if self.unit != None:
      return True
    return False
  
  def fromXML(self, doc, node):
    ''' Read in a contact from a XML node
    '''
    # Non-field information
    # unit, timestamp, rating and status
    self.unit = doc.SafeGet(node, 'unit', self.unit)
    self.timestamp = doc.SafeGet(node, 'timestamp', self.timestamp)
    self.rating = doc.SafeGet(node, 'rating', self.rating)
    self.status = doc.SafeGet(node, 'status', self.status)
    self.deception = doc.SafeGet(node, 'deception', self.deception)
    
    # Field processing
    fds = doc.Get(node, 'fields')
    for fd in doc.ElementAsList(fds):
      # Tag name
      tag = fd.tagName
      
      # Special case - Equipment
      if tag == 'equipment':
        count = int(doc.Get(fd, 'count'))
        kind = doc.Get(fd, 'category')
        self.EquipmentSighting(doc.Get(fd), kind, count)
        continue
      
      self.SetField(tag, doc.Get(fd))
    
  def toXML(self, doc):
    ''' Create a node and write an XML representation of the data.
        Uses attributes to make the XML more compact.
    '''
    out = doc.NewNode('contact')
    ## Housekeeping part
    # Name
    if type(self.unit) == type(''):
      doc.SetAttribute('unit', self.unit, out)
    else:
      # unit is a pointer
      doc.SetAttribute('unit', self.unit.GetName(asuniqueID=True), out)
      
    # timestamp
    if self.timestamp:
      doc.AddField('timestamp', self.timestamp, out, 'datetime')
      
    # rating 
    if self.rating:
      doc.SetAttribute('rating', self.rating, out)
      
    # deception
    if self.deception:
      doc.SetAttribute('deception', self.deception, out)
      
    # Status
    if self.status != 'new':
      doc.SetAttribute('status', self.status, out)
      
    # Fields
    if len(self.fields):
      fd = doc.NewNode('fields')
      doc.AddNode(fd, out)
      
      # Write the data
      for k in self.fields:
        if k == 'equipment':
          # Special case
          for kind in self.fields['equipment']:
            for item in self.fields['equipment'][kind]:
              eqnd = doc.AddField('equipment', item['ID'], fd)
              doc.SetAttribute('category', kind, eqnd)
              doc.SetAttribute('count', item['count'], eqnd)
        else:
          # Write the field as is
          x = self.GetField(k)
          doc.AddField(k,x,fd)
    
    return out
  def DefineFields(self):
    ''' 
       fields according to FM 101-5-1 of the US army.
    '''
    self.fields = {}
    
    self.fields['symbol'] = {}
    self.fields['hardware'] = ''
    self.fields['side'] = ''
    self.fields['size indicator'] = ''
    self.fields['equipment'] = ''
    self.fields['task force'] = ''
    self.fields['nature'] = 'new'
    self.fields['reinforced/detached'] = ''
    self.fields['staff comment'] = ''
    self.fields['additional information'] = ''
    self.fields['evaluation rating'] = 'F'
    self.fields['combat effectiveness'] = ''
    self.fields['signature equipment'] = ''
    self.fields['higher formation'] = ''
    self.fields['enemy(hostile)'] = ''
    self.fields['IFF/SIF'] = ''
    self.fields['movement arrow'] = None
    self.fields['mobility'] = ''
    self.fields['locating indicator'] = False
    self.fields['unique designation'] = ''
    self.fields['datetime'] = '' #DDHHMMSSZMONYY
    self.fields['altitude/depth'] = ''
    self.fields['location'] = ''
    self.fields['speed'] = ''
    self.fields['footprint'] = ''
    self.fields['Echelon Footprint'] = None
    
    # Analytical
    self.fields['CCC'] = ''
    self.fields['morale'] = ''
    self.fields['fatigue'] = ''
    self.fields['suppression'] = ''
    self.fields['supply'] = ''
    
    self.fields['min IF range'] = ''
    self.fields['max IF range'] = ''
    
    
    
  def Duplicate(self, encode = None):
    '''
       Make a copy of self into a new instance, used when a contact is reported to more than 1 recipient.
       encode : make the instance pickle-safe.
    '''
    # Write out
    from sandbox_XML import sandboXML
    xml = sandboXML('tests')
    xml.AddNode(self.toXML(xml), xml.root)
    
    # Read again
    out = xml.Get(xml.root, 'contact')
    
    # Preserve the pointer type if no encoding is required.
    if not encode:
      out.unit = self.unit
      
    return out
    
  

  # Retrieve Information
  #  
  def DeceptionLevel(self):
    return self.deception
  
  def GetField(self, k, default=''):
    ''' return thee field or whatever default is'''
    return self.fields.get(k,default)
    
  def IFF(self):
    return self.fields['IFF/SIF']
  

  
  def IntelReliability(self, pv = None):
    return self.rating
  
  def IsDirectObs(self, echelon = False):
    '''Will be able to add EW in due time.'''
    if self.Status() == 'direct':
      return 1
    if echelon and len(self.direct_subordinates):
      return 1
    return 0
  
  def TrackName(self):
    '''
       Try to solve for a track name
    '''
    return self.WriteTrackIdentity()
  
  def Status(self):
    '''
       Return the status
    '''
    return self.status

  

    

  # Manipulate the information
  # 
  def EquipmentSighting(self, kind, eclass, count, timestamp=None):
    ''' Add this equipment to the equipment field. kind is the template name, eclass is either personel of vehicle
        and count is the number seen. 
        If the sighting exists, it will update the count only if it is bigger.
    '''
    for i in self.fields['equipment'][eclass]:
      if i['ID'] == kind:
        if count >= i['count']:
          i['count'] = count
          if self.timestamp:
            self.fields['datetime'] = self.timestamp.strftime('%H%MZ(%d%b%y)')
        return
        
        
    # first sighting of this kind of equipment
    self.fields['equipment'][eclass].append({'ID':kind,'count':count})
    
  def AddDirect(self, uid):
    '''! \brief Add to the list of underling in direct contact with the contact
    '''
    if not uid in self.direct_subordinates:
      self.direct_subordinates.append(uid)
    
  def RemoveDirect(self, uid):
    '''! \brief Remove to the list of underling in direct contact with the contact
    '''
    if uid in self.direct_subordinates:
      self.direct_subordinates.remove(uid)
    
     
  def Merge(self, other):
    '''
       Add un-empt fields if other.IntelReliability() is larger than self.InterReliability()
    '''
    update = self.IntelReliability() <= other.IntelReliability()
    
    for i in other.fields.keys():
      if other.fields[i]:
        if update:
          # Never overwrite a direct contact
          if i == 'nature':
            if self.IsDirectObs():
              continue
            
          self.UpdateField(i,other.fields[i])
          if i == 'location':
            self.location = other.location
            
    if update:
      self.p_right = other.p_right + 0.0
      # Location
      self.location = copy(other.location)
      self.UpdateField('location', self.unit.sim.map.MGRS.AsString(other.location))
      
  # Non-interface methods
  #
  def SetLocation(self, L, translator = None):
    '''! \brief set location
         \param L can be a position descriptor or a vector or a polygon
         \param translator is a coordinate convertor.
    '''
    if 'position_descriptor' in str(L.__class__):
      self.location = L
    
    elif hasattr(L,'x'):
      self.location.x = L.x
      self.location.y = L.y
      self.location.z = L.z
      
    elif hasattr(L,pts):
      self.location.SetFootprint(L)
    
    if translator:
      self.UpdateField('location', translator.AsString(self.location))
    
  def UpdateField(self, Key, value, rating = None, mytime = None):
    '''!
       Higher level to SetField which updates only if the intel strength is 
       equal or higher.
       \param pv (float) If left to none, will update automatically.
       \param Key (string) A key in fields.
       \param value (--) The value to be mapped into the fields.
    '''
    ## Check if the update should be made
    if rating == None:
      update = True
    else:
      update = False
      # Case 1, the rating is higher or equal for the new data
      if rating >= self.rating:
        update = True
        self.rating = rating
      # Case 2, the field doesn't exist, so the data is accepted any how
      if not Key in self.fields:
        update = True
      
    # Abort
    if not update:
      return
    
    # Update time
    if mytime:
      self.timestamp = mytime
      # Remove the undetected status
      if self.status == 'undetected':
        self.status = 'new'
    
    # Set the field
    self.SetField(Key, value)
    
      
  def SetField(self, Key, value):
    '''! \brief Update the dictionary of fields.
        Must be used when a value is set of changed
        \param Key The key in the field structure
        \param value self explanatory
        
        \warning Timestamping is done ONLY if there is a valid timestamp. An exception to this rules
        was found when called from the Edit contact GUI panel with a translator argument provided.
    '''
    
    self.fields[Key] = value
    if self.timestamp:
      self.fields['datetime'] = self.timestamp.strftime('%H%MZ(%d%b%y)')
    #self.log.Add('Field %s set to %s with Intel Reliabilty of %.2f'%(Key, str(value), self.IntelReliability()))
    
    
  def STANAG2022(self, pright):
    '''
       Make a 2 Character code of the intelligence strength.
    '''
    temp = self.IntelReliability()
    if random() < pright:
      # May admit that the inter isn't right
      if pright < 0:
        temp = temp - (0.5 - pright)
    if temp <= -0.1:
      return '5'
    elif temp <= 0.0:
      return '4'
    elif temp <= 0.50:
      return '6'
    elif temp <= 0.75:
      return '3'
    elif temp <= 0.90:
      return '2'
    else:
      return '1'
    
      
    
      

  # Output methods
  #
  def WriteField(self, field):
    ''' Write the content of the field in a simple format
    '''
    # Get content as a string
    content = str(self.fields.get(field,''))
    
    # Field name in bold
    out = html.Tag('STRONG', '%s : '%(field))
    
    # Whole thing as a span
    out = html.Tag('span', '%s%s'%(out,content))
    
    return out
    
  def WriteTrackIdentity(self):
    ''' Write the header of the html render
        name (augmentation) | side | size | TOE
    '''
    out = self.GetField('identity', 'unknown')
    out += self.GetField('augmentation')
    # separator
    if out[-1] == ')':
       out += ' | '
    else:
      out += ' '
    # side
    out += self.GetField('side', 'UNK')
    out += ' | '
    # size
    out += self.GetField('size', 'UNK')
    out += ' | '
    # TOE
    out += self.GetField('TOE')
    
    return out
    
    
  
  
  def __str__(self):
    '''Build a contact string for SITREP and INTREP'''
    out = 'Track : '
    if self.fields['unique designation']:
      out = out + '%s '%(self.fields['unique designation'])
    if self.fields['higher formation']:
      out = out +' %(Higher Echelon : %s) ' %( self.fields['higher formation'])
    # Size details that may be added to track ID
    temp = ' '
    if self.fields['IFF/SIF']:
      temp = temp + 'IFF: %s | '%(self.fields['IFF/SIF'])
    if self.fields['hardware']:
      temp = temp + 'Type: %s | ' %(self.fields['hardware'])
    if self.fields['size indicator']:
      temp = temp + 'Ech.: %s'%(self.fields['size indicator'])  
    if self.fields['reinforced/detached']:
      temp = temp + ' (%s)\n'%(self.fields['reinforced/detached'])
    else:
      temp = temp + '\n'
    out = out + temp
    
    # Intel info
    if self.fields['datetime']:
      out = out + 'Time of report: %s | '%(self.fields['datetime'])
    if self.fields['evaluation rating']:
      out = out + 'Rating: %s | '%(self.fields['evaluation rating'])
    if self.fields['nature']:
      out = out + 'INTEL: %s | '%(self.fields['nature'])
      out = out + '\n'
    # Position and stance
    if self.fields['location']:
      out = out + 'Grid Ref : ' + self.fields['location']
    if self.fields['mobility']:
      out = out + ' in %s .\n'%(self.fields['mobility'])
    if self.fields['combat effectiveness']:
      out = out + 'Estimate effectiveness : %.1f .'%(self.fields['combat effectiveness']) 
    return out + '\n'
  def __repr__(self):
    try:
      return self.TrackName() + ' for ' + self.unit.GetName()
    except:
      return self.__str__()
  def AsHTML(self):
    '''
       Return a HTML encoded report
    '''
    # In a table
    # TrackName as header
    header = self.TrackName()
    
    ## Set of data to write
    keys = self.fields.keys()
    # remove trackname fields
    for k in ['identity', 'size', 'side', 'augmentation', 'TOE']:
      if k in keys:
        keys.remove(k)
    
    # Number of fields
    n = len(keys)
    cells = ['','']
    for k in range(n):
      if k < n/2.0:
        i = 0
      else:
        i = 1
      # Write the field
      cells[i] += self.WriteField(keys[k]) + '<br>'
      
    # Put together
    out = '<table border=1 width="500em">\n'
    out += '<tr><th COLSPAN=2>%s</th></tr>\n'%(header)
    # Data cells
    out += '<small><tr style="font-size:small;"><td>%s</td><td>%s</td></tr></small>\n'%(cells[0],cells[1])
    # close table tag
    out += '</table>\n'
    
    return out
  


'''
  System to model situational awareness and detection routines.
'''
class system_intelligence(system_base.system_base):
  def __init__(self): 
    system_base.system_base.__init__(self)
   
    # Two-layers signature, first level is the signature's kind.The second level is a label
    # A signature is a likelihood of being detected.
    self.signature = {}
    
    
  def fromXML(self, doc, node):
    '''! \brief Populate instance from XML node.
         Effect:
               - signature under a series of stances.
               - sensors listing.
    '''
    # Signatures
    for sig in doc.Get(node, 'signature', True):
      tp = doc.Get(sig, 'type')
      level = doc.Get(sig, 'level')
      
      # Sameas attribute
      sameas = doc.Get(sig, 'sameas')
      if sameas:
        if sameas in self.signature:
          self.signature[tp] = self.signature[sameas]
        else:
          raise SandboxException('XMLParseSameAsInvalid',['intelligence', tp, sameas])
        continue
      
      # Basal level has an empty label
      self.SetSignature(tp, level)
      
      # Read labels exeptions
      for pr in ['very_likely', 'likely', 'neutral', 'unlikely', 'very_unlikely']:
        x = doc.Get(sig, pr)
        if x != '':
          for label in x.split(','):
            label = label.strip()
            self.SetSignature(tp, pr.replace('_',' '), label)
      
  def SetSignature(self, gtype, level, label=''):
    ''' Add this info to the signature. '''
    # Create the signature type if it doesn't exists.
    if not gtype in self.signature:
      self.signature[gtype] = {}
      
    # Override the label
    self.signature[gtype][label] = level
    
  def GetSignature(self, gtype, label=''):
    ''' Return the TOEM level.'''
    # No signature
    if not gtype in self.signature:
      return 'impossible'
    
    # Fetch the label
    if not label in self.signature[gtype]:
      label = ''
    return self.signature[gtype][label]
  
  def GetHighestSignature(self, gtype, labels=[]):
    ''' Cycle through each label and get the highest signature.
    '''
    # Create an argument
    x = TOEMargument()
    
    # 
    bestint = -100
    bestconcept = 'impossible'
    
    for lbl in labels:
      concept = self.GetSignature(gtype, lbl)
      if x.ConceptValue(concept) > bestint:
        bestint = x.ConceptValue(concept)
        bestconcept = concept
        
      return bestconcept
    
      
      
  

    

  # Simulation Interface
  def AcquireTarget(self, E, tgt):
    ''' Process the detection of each sensor owned by E on target tgt.
        Returns the contact to tgt.
        
        Algorithm:
        
        for each SENSOR:
           contact <- AcquireWithSensor( E, sensor, tgt)
           MERGE contact with E's existing contact by updating fields
    '''
    # List all sensors
    sensors = self.EnumerateSensors(E)
    
    # Get the contact
    cnt = E.Contact(tgt)
    if not cnt:
      # Create a new contact
      cnt = sandbox_contact(tgt)
      E.WriteContact(cnt)
    
    # Go over each sensor
    for s in sensors:
      # Get the argument on whether there will be an acquisition
      argument = self.AcquireWithSensor(E, s, tgt)
      
      # Factor in levels of deception
      for i in range(cnt.DeceptionLevel()):
        argument.AddCon('deception')
        
      # Roll the argument
      success = argument.Resolve()
      
      if success:
        self.ClassifyWithSensor(E, cnt, s, argument.Increment())
        
        # Deception and rating
        cnt.deception = 0
        cnt.rating = argument.Increment()
      else:
        # It failed
        cnt.deception += 1
  
  def ClassifyWithSensor(self, E, cnt, sensor, increment):
    ''' Determine which field to update and do it.
    '''
    # Get a list of fields to update
    fields = self.FieldsToUpdate(sensor, increment)
      
    # Update the fields
    self.UpdateFieldsFromList(E, cnt, fields)
  
  def Signature(self, label):
    ''' Returns the signature for a given unit's stance as a TOEM probability. '''
    if self['signature'].has_key(label):
      return self['signature'][label]
    return self['signature']['deployed']  
  
  
  # Private Methods
  def AcquireWithSensor(self, E, sensor, tgt):
    ''' Algorithm:
        
        SIGNAL <- GET sensor's signal
        signature <- Get signature from tgt for SIGNAL
        signature <- fetch tgt stance and activity modifiers.
        
    '''
    # Signal Type
    signal = sensor.signal
    
    # Is this target has a signature for this signal
    signature = tgt.GetSignature(signal)
    
    # Abort if a sensor can't pick-up on the signal
    if signature == 'impossible':
      return []
    
    # Build an argument
    x = TOEMargument(base_prob=signature)
    
    # Get Atmospheric effects over the target
    effects = E.sim.GetAtmosphericEffects(tgt.Position())
    
    # Go over the requirements
    for i in sensor.requires:
      if i == 'LOS':
        # special case of needing a LOS
        if not E.sim.LineOfSight(E.Position(), tgt.Position()):
          return []
      elif not i in effects:
        return []
    
    # PROS/CONS
    for eff in effects:
      if eff in sensor.degraded_by:
        x.AddCon(eff)
      elif eff in sensor.enhanced_by:
        x.AddCon(eff)
    
    # returns
    return x
    
    
  
  def EnumerateSensors(self, E):
    ''' Returns a list of sensors owned by E from the personel and vehicle components.
        The list is in fact a dictionary which uses the count as value and instances as keys.
    '''
    out = {}
    # Personel
    for k in E.personel:
      x = E.personel[k]['kit']
      for s in x.sensors:
        if not s[0] in out:
          out[s[0]] = 0
        out[s[0]] += E.personel[k]['count'] * s[1]
    
    # Vehicles
    for k in E.vehicle:
      x = E.vehicle[k]['kit']
      for s in x.sensors:
        if not s[0] in out:
          out[s[0]] = 0
        out[s[0]] += E.vehicle[k]['count'] * s[1]
        
    return out
  
  def FieldsToUpdate(self, sensor, increment):
    ''' Return the list of fields to update for this sensor, consider the success increment.
    '''
    out = []
    # Not acquired
    if increment < 0:
      return out
    
    # iterate over all fields
    for fd in sensor.ClassificationFields():
      # Get prob
      p = sensor.ClassifyProb(fd)

      # Argument
      add = TOEMargument(base_prob= p).Resolve()
      
      # add to list of true
      if add:
        out.append(fd)
        
    return out
  def UpdateFieldsFromList(self, E, cnt, fields):
    ''' Fetch the correct information from the target unit for each field
    '''
    # tgt unit
    tgt = cnt.unit
    
    # Cycle
    for fd in fields:
      methodname = 'ExtractField' + fd
      if hasattr(self, methodname):
        # Call the method
        cnt.UpdateField(fd, getattr(self, methodname)(E, tgt), mytime=E.sim.clock)
      else:
        raise SandboxException('ExtractFieldError',fd)
      
    pass
  
  ## ExtractField Section
  ''' The naming of these methods is such that it pattern match with the XML tags of the contact fields. This may
      explain why there are inconsistent naming going on.
  '''
  def ExtractFieldTOE(self, unit, E):
    ''' Straighforward get TOE label
    '''
    return E['TOE']
  
  def ExtractFieldside(self, unit, E):
    ''' returns the side of a contact'''
    return E['side']
  
  def ExtractFieldsize(self, unit, E):
    '''  returns the size of a contact'''
    return E['size']
  
  def ExtractFieldhigher_formation(self, unit, E):
    '''  Returns E's command echelon, or it's HQ is E is not a command unit.'''
    if E['echelon_name']:
      return '%s (%s)'%(E['echelon_name'], E['command_echelon'])
    else:
      # Get the TOE HQ, not the TF HQ
      hq = E.GetHQ(use_opcon=False)
      
      # This unit must have an echelon!
      return '%s (%s)'%(hq['echelon_name'], hq['command_echelon'])
    
  def ExtractFieldidentity(self, unit, E):
    '''  Return the unit's identity '''
    return E.GetName()
  
  def ExtractFieldaugmentation(self, unit, E):
    '''  Returns either a (+) or a (-) or an empty string'''
    # Case 1 - augmentation
    if E.AttachedSubordinates():
      return '(+)'
    elif E.DetachedSubordinates():
      return '(-)'
    # No augmentation
    return ''
  
  def ExtractFieldpersonel(self, unit, E):
    ''' return a sighting of personel
    '''
    return 'implement me'
  
  def ExtractFieldvehicle(self, unit, E):
    ''' return a sighting of personel
    '''
    return 'implement me'
  
  def ExtractFieldlocation(self, unit, E):
    '''  Get the location as a string. '''
    return 'UTM ' + E.PositionAsString()
  
  
  def ExtractFieldstance(self, unit, E):
    '''  '''
    return E['stance']
  
  def ExtractFieldactivity(self, unit, E):
    '''  Returns the activity vector. A better implementation would use the name label of the active task.'''
    # Get OPORD
    opord = E['OPORD']
    
    # Get Current task
    act = opord.GetCurrentSubTask()
    if act:
      return act.type
    # No task...
    return 'idle'
  
  def ExtractFieldcourse(self, unit, E):
    '''  Return the direction of the unit.
         TODO: report the road and the direction if on an infrastructure.
    '''
    # Get bearing and convert to degrees
    bear = (E.GetBearing() / pi ) * 180
    if bear < 0.0:
      bear += 360
      
    return str(int(bear)) 

  
  def ExtractFieldspeed(self, unit, E):
    '''  Expressed in kph (/ by the pulse 6 length in hours)'''
    return E.Position().rate / (E.sim.Pulse())
  
  def ExtractFieldrange(self, unit, E):
    '''  Returns the range in km.'''
    # Us and Them
    us = unit.Position().AsVect()
    them = E.Position().AsVect()
    
    # distance
    return (them - us).length()
    
  
  def ExtractFieldbearing(self, unit, E):
    '''  '''
    # Us and Them
    us = unit.Position().AsVect()
    them = E.Position().AsVect()
    
    # In degree
    return (us.BearingTo(them)[0] / pi) * 180
  

  
  def ExtractFieldaltitude(self, unit, E):
    '''  The altitude from the position above ground or sea level.'''
    return E.Position().z
  
  def ExtractFieldcasulaty_level(self, unit, E):
    '''  TODO: implement after revisiting the combat model'''
    # Collect all authorized and actual number
    authorized = 0
    count = 0
    for i in E.personel:
      authorized += E.personel[i]['authorized']
      count += E.personel[i]['count']
      
    for i in E.vehicle:
      authorized += E.vehicle[i]['authorized']
      count += E.vehicle[i]['count']
      
    return 100 * (1.0 - (authorized/count))
  
  def ExtractFieldmorale(self, unit, E):
    '''  '''
    return E.AsStringMorale(E.GetMorale())
  
  def ExtractFieldfatigue(self, unit, E):
    '''  '''
    return E.AsStringFatigue(E.GetFatigue())
  
  def ExtractFieldsuppression(self, unit, E):
    '''  '''
    return E.AsStringSuppression(E.GetSuppression())
  
  def ExtractFieldsupply_level(self, unit, E):
    '''  Rough bulk estimates in percent.
         Confound all supply types: so heavy stuff is more important than light stuff.
    '''
    return float(E.GetCargo()) / float(E.GetCapacity()) * 100
  
  
  # Legacy Methods to eliminate 

  def SituationalAwareness(self, other, real = True):
      '''!
         If real set to false, will return the percieved SA instead of the real SA
         if other is a list, will return an average of all units.
      '''
      if not other:
        return 0.5
      
      # Make a list anyhow.
      if type(other) != type([]):
        other = [other]
      
      tot = 0.0
      for i in other:
        cnt = self.Contact(i)
        if cnt != None:
          if real:
            tot += cnt.p_right
          else:
            tot += cnt.IntelReliability()
            
      return tot / len(other)

import unittest
class IntelligenceModelTest(unittest.TestCase):
  def setUp(self):
    import sandbox_data
    self.database = sandbox_data.sandbox_data_server()
    
    os.chdir
    
  def testLoadBaseINTEL(self):
    x = self.database.Get('intelligence', 'base')
    self.assertTrue(len(x.signature) != 0)
    
  def testBaseVizINTEL(self):
    x = self.database.Get('intelligence', 'base')
    self.assertEqual(x.GetSignature('visual'), 'likely')
    
  def testBaseVizINTELdeployed(self):
    x = self.database.Get('intelligence', 'base')
    self.assertEqual(x.GetSignature('visual','deployed'), 'neutral')
    
  def testBaseVizINTELunkLabel(self):
    x = self.database.Get('intelligence', 'base')
    self.assertEqual(x.GetSignature('visual', 'latrine'), 'likely')
    
  def testBaseThermalINTEL(self):
    x = self.database.Get('intelligence', 'base')
    self.assertEqual(x.GetSignature('thermal'), 'likely')
    
  def testBaseSoundINTEL(self):
    x = self.database.Get('intelligence', 'base')
    self.assertEqual(x.GetSignature('sound'), 'unlikely')
    
  def testBaseSoundINTELcombat(self):
    x = self.database.Get('intelligence', 'base')
    self.assertEqual(x.GetSignature('sound', 'combat'), 'very likely')
    
    
    
  def testTwoUnitVisualContact(self):
    # load the scenario
    import sandbox_world
    world = sandbox_world.sandbox('testTwoFireTeamsUTM.xml')
    
    # Run for an hour
    world.Simulate()
    
    self.assertTrue(True)
    
class ContactTest(unittest.TestCase):
  def setUp(self):
    from sandbox_XML import sandboXML
    # Get the XML test file
    os.chdir(os.environ['OPCONhome'])
    self.doc = sandboXML(read="./tests/contacts.xml")
    
  def GetTest(self, label):
    ''' Retrieve the node of a contact of the following label
    '''
    for i in self.doc.Get(self.doc.root, 'contact', True):
      if i.unit == label:
        return i
      
    return None
  
  def testGetFullDescContact(self):
    x = self.GetTest('test unit')
    self.assertTrue(x)

  def testReadFullDescContact(self):
    x = self.GetTest('test unit')
    self.assertTrue(len(x.fields))
    
  def testReadWriteContact(self):
    # Read in
    x = self.GetTest('test unit')
    
    # Write out
    from sandbox_XML import sandboXML
    xml = sandboXML('tests')
    xml.AddNode(x.toXML(xml), xml.root)
    
    # Read again
    y = xml.Get(xml.root, 'contact')
    
    out = []
    
    # Compare fields
    out.append(set(x.fields.keys()).difference(set(y.fields.keys())) == set())
    out.append(set(y.fields.keys()).difference(set(x.fields.keys())) == set())
    for k in x.fields.keys():
      out.append(x.GetField(k) == y.GetField(k))
      
    # unit
    out.append(x.unit == y.unit)
    out.append(x.timestamp == y.timestamp)
    out.append(x.rating == y.rating)
    
    self.assertEqual(out.count('False'),0)
    
  def testContactSetField(self):
    # Read in
    x = self.GetTest('test unit')
    x.SetField('side', 'BLUE')
    self.assertNotEqual(x.GetField('side'), 'RED')
    
  def testContactUpdateField(self):
    x = sandbox_contact()
    x.rating = 1
    
    x.SetField('side','BLUE')
    x.UpdateField('side','RED', 2)
    
    self.assertEqual(x.GetField('side'), 'RED')
    
  def testContactUpdateFieldTie(self):
    x = sandbox_contact()
    x.rating = 1
    
    x.SetField('side','BLUE')
    x.UpdateField('side','RED', 1)
    
    self.assertEqual(x.GetField('side'), 'RED')
    
  def testContactUpdateFieldNot(self):
    x = sandbox_contact()
    x.rating = 1
    
    x.SetField('side','BLUE')
    x.UpdateField('side','RED', 0)
    
    self.assertEqual(x.GetField('side'), 'BLUE')
    
  def testContactUpdateFieldDefault(self):
    x = sandbox_contact()
    x.rating = 1
    
    x.SetField('side','BLUE')
    x.UpdateField('size','Plt', 0)
    
    self.assertEqual(x.GetField('size'), 'Plt')


    
    
if __name__ == '__main__':
  import os
  # Change folder
  os.chdir('..')
  
  # suite
  testsuite = []

  # basic tests on sandbox instance
  testsuite.append(unittest.makeSuite(IntelligenceModelTest))
  testsuite.append(unittest.makeSuite(ContactTest))
  
  # collate all and run
  allsuite = unittest.TestSuite(testsuite)
  unittest.TextTestRunner(verbosity=2).run(allsuite)