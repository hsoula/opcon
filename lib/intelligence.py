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
    
    # Status
    self.status = 'new'
  
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
  def GetField(self, k):
    ''' return thee field or None'''
    return self.fields.get(k,'')
    
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
    out = ''
    if self.fields['unique designation']:
      out = '%s ||'%(self.fields['identity'])
    else:
      out = 'Undetermined track ||'
    # Size details that may be added to track ID
    temp =  ' [ %s %s %s %s ]'%(self.GetField('side'), self.GetField('TOE'), self.GetField('size'), self.GetField('augmentation'))
    if temp != ' [    ]':
      out = out + temp
    return out
  
  def Status(self):
    '''
       Return the fields['nature'] variable
    '''
    return self.fields['nature']

  

    

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
    out = ''
    # First line
    firstline = html.Tag('STRONG','Track ID: ') + self.fields['unique designation']
    if self.fields['higher formation']:
      firstline = firstline + html.Tag('STRONG', ' (%s)'%(self.fields['higher formation']))
    if self.fields['IFF/SIF']:
      firstline = firstline + html.Tag('STRONG', ' [%s]'%(self.fields['IFF/SIF']))
    firstline = html.Tag('span', firstline) + '<BR>'
    
    # Second Line
    secondline = ''
    if self.fields['hardware']:
      secondline = secondline + html.Tag('STRONG','Type: ') + self.fields['hardware']
    if self.fields['size indicator']:
      secondline = secondline + ' %s'%(self.fields['size indicator'])  
    if self.fields['reinforced/detached']:
      secondline = secondline + ' (%s)'%(self.fields['reinforced/detached'])
    if self.fields['location']:
      secondline = secondline + ' |' +html.Tag('STRONG',' MGRS: ') + self.fields['location']
    secondline = html.Tag('span',secondline) + '<BR>'
    
    # Third line
    thirdline = ''
    if self.fields['datetime']:
      thirdline = thirdline + html.Tag('STRONG','Time of report: ') + self.fields['datetime']
    if self.fields['evaluation rating']:
      thirdline = thirdline + html.Tag('STRONG',' | Intel Rating: ') + self.fields['evaluation rating']
    if self.fields['nature']:
      thirdline = thirdline + html.Tag('STRONG',' | Observation : ') + self.fields['nature']
    thirdline = html.Tag('span',thirdline) + '<BR>'
    
    # Fourth line
    fourthline = ''
    if self.fields['mobility']:
      fourthline = fourthline + html.Tag('STRONG','Stance: ') + self.fields['mobility']
    if self.fields['combat effectiveness']:
      fourthline = fourthline + ' | ' +html.Tag('STRONG','Estimate effectiveness : ')+' %.1f .'%(self.fields['combat effectiveness'])
    fourthline = html.Tag('span',fourthline)
    
    return html.Tag('p',firstline+secondline+thirdline+fourthline)
  


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
    
    # Go over each sensor
    for s in sensors:
      # Get the fields that should be updated
      fields = self.AcquireWithSensor(E, s, tgt)
      
      # Get the contact
      cnt = E.Contact(tgt)
      if not cnt:
        cnt = sandbox_contact(other)
        
      # Update the fields
      self.UpdateFieldsFromList(E, cnt, fields)
      
    return sandbox_contact(tgt)
  
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
    
    # Build an argument
    x = TOEMargument(base_prob=signature)
    
    # Get Atmospheric effects over the target
    effects = E.sim.AtmosphericEffects(tgt.Position())
  
  def EnumerateSensors(self, E):
    ''' Returns a list of sensors owned by E from the personel and vehicle components.
        The list is in fact a dictionary which uses the count as value and instances as keys.
    '''
    out = {}
    # Personel
    
    # Vehicles
    
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
        getattr(self, methodname)(E, tgt)
      else:
        raise SandboxException('ExtractFieldError',fd)
      
    pass
  
  ## ExtractField Section
  ''' THe naming of these methods is such that it pattern match with the XML tags of the contact fields. This may
      explain why there are inconsistent naming going on.
      List: TOE, side, size, higher_formation, identity, augmentation, location, personel, vehicle
            stance, activity, course, speed, range, bearing, altitude, casualty_level, morale, fatigue, suppression,
            supply_level
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
    return 'UTM ' + E.GetPositionAsString()
  
  
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
    return E.Position().rate / (E.sim.pulse.seconds/3600.0)
  
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
  def InitializeSensors(self, E):
    '''
       Build sensors.
    '''
    # Flush sensors from platform
    E['sensors'] = []
    
    # Direct detection through visuals
    if self['sensors'].has_key('visual') and E.Footprint():
      E['sensors'].append(SensorVisual(E.Footprint()))
      
    


  
  def Signature(self, label):
    ''' Returns the signature for a given unit's stance as a TOEM probability. '''
    if self['signature'].has_key(label):
      return self['signature'][label]
    return self['signature']['deployed']
  
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
    
    self.assertTrue(False)
    
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