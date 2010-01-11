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

import Renderer_html as html

from sandbox_keywords import dch_size_denomination
from GUIMapSym import MapSym, Sym_denom
from sandbox_geometry import geometry_rubberband

import system_base


class sandbox_contact(dict):
  '''! \brief contact information data structure.
  '''
  def __init__(self, myunit= None):
    self.unit = myunit
    self.p_right = 0.5
    
    self.log = sandbox_log()
  
    # Create field according to FM 101-5-1
    self.DefineFields()

    # Direct subordinates in direct contact
    self['direct subordinates'] = []
    
    self.location = None
    self.timestamp = None
    
  def __nonzero__(self):
    if self.unit != None:
      return True
    return False
  
  def fromXML(self, doc, node):
    pass
  def toXML(self, doc):
    pass
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
    out = sandbox_contact(self.unit)
    if encode:
      out.unit = out.unit['uid']
    out.p_right = self.p_right
    out.log = copy(self.log)	
    out.location = copy(self.location)
    out.timestamp = copy(self.timestamp)
    
    for i in self.fields.keys():
      out.UpdateField(i, self.fields[i])
    return out
  

  # Retrieve Information
  #
  def GetFootprint(self, echelon = False):
    '''! \brief Return the contact location
    '''
    if echelon:
      pass
    
    return self.location
  def GetRangeRings(self):
    '''! \brief Get the range rings for a contact. 
         \return A list with [min, max] or None
    '''
    if self.fields['max IF range']:
      return [self.fields['min IF range'], self.fields['max IF range']]
  
  def IFF(self):
    return self.fields['IFF/SIF']
  

  
  def IntelReliability(self, pv = None):
    # Percieved intel reliability
    if pv == None:
      pv = self.p_right
    return abs(0.5 - pv) / 0.5
  
  def IsDirectObs(self, echelon = False):
    '''Will be able to add EW in due time.'''
    if self.Type() == 'direct':
      return 1
    if echelon and len(self['direct subordinates']):
      return 1
    return 0
  
  def TrackName(self):
    '''
       Try to solve for a track name
    '''
    out = ''
    if self.fields['unique designation']:
      out = '%s ||'%(self.fields['unique designation'])
    else:
      out = 'Undetermined track ||'
    # Size details that may be added to track ID
    temp =  ' [ %s %s %s %s ]'%(self.fields['IFF/SIF'], self.fields['hardware'], self.fields['size indicator'], self.fields['reinforced/detached'])
    if temp != ' [    ]':
      out = out + temp
    return out
  
  def Type(self):
    '''
       Return the fields['nature'] variable
    '''
    return self.fields['nature']

  
  def IconString(self):
    '''! \brief return the MapSym string for the contact, or a blank icon is it doesn't work.
    '''
    try:
      size = Sym_denom[self.fields['size indicator']]
      type = self.fields['symbol']['char']
      return size+type
    except:
      return '0'
    
  def IconFont(self):
    '''! \brief return the font name to use, or a generic NU-Land if it fails.
        The font name MUST be valid, this check has to be done at the UI level!
    '''
    type = self.fields['symbol']['type']
    iff = self.fields['symbol']['IFF']
    try:
      if iff == 'NA' or (type in ['Land1','Eqpt','OOTW']):
        return 'MapSym%s%s'%(iff,type)
      else:
        return 'MapSym-%s-%s'%(iff,type)
    except:
      return 'MapSym-NU-Land'
    
  # Manipulate the information
  # 
  def AddDirect(self, uid):
    '''! \brief Add to the list of underling in direct contact with the contact
    '''
    if not uid in self['direct subordinates']:
      self['direct subordinates'].append(uid)
    
  def RemoveDirect(self, uid):
    '''! \brief Remove to the list of underling in direct contact with the contact
    '''
    if uid in self['direct subordinates']:
      self['direct subordinates'].remove(uid)
    
     
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
    
  def UpdateField(self, Key, value, pv = None, mytime = None):
    '''!
       Higher level to SetField which updates only if the intel strength is 
       equal or higher.
       \param pv (float) If left to none, will update automatically.
       \param Key (string) A key in fields.
       \param value (--) The value to be mapped into the fields.
    '''
    if pv == None:
      pv = self.p_right
    if self.IntelReliability(pv) >= self.IntelReliability(self.p_right) or (not self.fields[Key]):
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
    # counter-intelligence
    # Chance of detection while footprints are touching
    self['signature'] = {'transit':0.9, 'deployed':0.8}
    
    # Data gathering
    # radius for testing in km -- OBSOLETE
    self['sensors'] = {'visual':True}
    
    # Contacts (use pointers as keys)
    self['contacts'] = {}
    
    
  def fromXML(self, doc, node):
    '''! \brief Populate instance from XML node.
         Effect:
               - signature under a series of stances.
               - sensors listing.
    '''
    # Signature
    sig = doc.Get(node, 'signature',True)
    for s in sig:
      for st in doc.Get(s, 'stance', True):
        self['signature'][doc.Get(st,'name')] = doc.Get(st)
        
    # Sensors
    for s in doc.Get(node, 'sensors', True):
      for sn in doc.Get(s, 'sensor', True):
        self['sensors'][doc.Get(sn,'name')] = doc.Get(sn)
      
      
  def InitializeSensors(self, E):
    '''
       Build sensors.
    '''
    # Flush sensors from platform
    E['sensors'] = []
    
    # Direct detection through visuals
    if self['sensors'].has_key('visual') and E.Footprint():
      E['sensors'].append(SensorVisual(E.Footprint()))
  
  def ContactList(self):
    '''! \brief Return the complete Contact list
    '''
    return self['contacts'].values()
  

  
  def Contact(self, unit):
    '''! \brief Return a contact from the pointer of the unit.
         \return None if the contact doesn't exist
    '''
    if not unit:
      return None
    k = unit['side']+unit.GetName()
    if k in self['contacts'].keys():
      return self['contacts'][k]
    return None
      
    
  def DeleteContact(self, unit):
    for i in self['contacts']:
      if self['contacts'][i].unit == unit or self['contacts'][i] == unit:
        del self['contacts'][i]
        return
      
  def WriteContact(self, cnt):
    '''
       Alter the contact list
    '''
    if cnt.unit.has_key('delete me'):
      return
    k = cnt.unit['side']+cnt.unit.GetName()
    self['contacts'][k] = cnt
  
  def Signature(self, stance):
    if self['signature'].has_key(stance):
      return self['signature'][stance]
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
   