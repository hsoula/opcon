''' 
    Communication data structures
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
from copy import deepcopy
import os
import os.path

from random import random
from vector import vect_5D

from sandbox_tasks import *
import Renderer_html as html

from sandbox_graphics import *
from sandbox_exception import SandboxException

# function (debug conveniences mostly)
  

# classes
class sandbox_COMM(dict):
  '''! \brief A communication item datastructure.
  
      The sender and recipient are pointers, unless the structure is pickled.
      The baseclass provide a RenderHeader() method to output HTML header to a communication
  '''
  def __init__(self, sender = None, recipient = None):
    self['C3 level'] = 1.0
    
    self.SetSender(sender)
    self.SetRecipient(recipient)
    
    # Metadata
    self['sent timestamp'] = None
    
    # templating data
    self.template = ''
    self.report = ''
    
  def ArchiveName(self):
    ''' AUTOform a file name for this comm
    '''
    return self['sent timestamp'].strftime('%m%d.%H%M') + '.' + self.__class__.__name__ + '.html'
    
  def SetSender(self, sndr):
    '''! \brief Set sender and sendername
         \warning Set sender as a pointer to sender, not UID.
    '''
    # sndr is None if built without arguments
    self.sender = None
    if sndr:
      self.sender = sndr
      
  def SenderName(self):
    ''' Returns the name of the sender
    '''
    if self.sender:
      return self.sender.GetName()
    
  def SetRecipient(self, rcp):
    self.recipient = None
    if rcp:
      self.recipient = rcp
      
  def Sender(self):    
      return self.sender
  
  def IsSuppressed(self):
    if random() > self['C3 level']:
      return True
    return False
  

  def IsRecipient(self, name):
    ''' Returns true if the name is in the recipient list
    '''
    if self.recipient and name == self.recipient.GetName():
      return True
    return False
  
  # templating interface
  def GetTemplate(self, tname=''):
    ''' Opens the template and returns it as a string, use tname if provided instead of hthe self.template
    '''
    if not tname:
      tname = self.template
    try:
      self.report = open(os.path.join(os.environ['OPCONhome'],'COMM',tname)).read()
    except:
      raise SandboxException('COMMTemplateNotFound',tname)
    
  def FillField(self, field_name, content):
    ''' replace a field (without the ## optionally) by the text in content.
    '''
    if not field_name.startswith('##'):
      field_name = '##%s##'%(field_name).upper()
    self.report = self.report.replace(field_name,content)
    
   
    
  def ConvertToHTML(self):
    ''' convert report to html
    '''
    # end of line
    out = self.report.replace('\n','<br>\n')
    out = out.replace('&nbsp;','$%$%$%$')
    out = out.upper()
    out = out.replace('$%$%$%$','&nbsp;')
    return out
  # Data Structure
  def GetData(self, vector, default=''):
    '''! \brief Return the free text for an arbitrary field where each 
                string in vector is a key in the data tree
    '''
    out = self[vector[0]]
    for i in vector[1:]:
      if i in out:
        out = out[i]
      else:
        # The tree structure don't contain this node... return nothing
        return default
    return out
  
  def SetData(self, vector, data={}):
    ''' Set the data packet at the leaf of the data tree as specified in vector
    '''
    root = self
    for i in range(len(vector)):
      key = vector[i]
      # Add the data field to the root
      if not key in root and not key == vector[-1]:
        root[key] = {}
      # If key isn't the last key in vector, update the root
      if i < len(vector)-1:
        root = root[key]
        continue
      else:
        # Update the data
        root[key] = data
        return True
    # This should never happen
    return False
    
  # IO
  def AsHTML(self):
    return ''
  def toXML(self, doc, root= None, node=None):
    # Create a node if it already doesn't exist, the node is named after the class name
    if node == None:
      node = doc.NewNode(self.__class__.__name__)
      
    # Get the root if not set by default
    if root == None:
      root = self
      
    # Iterate through the data tree
    for key in root.keys():
      safekey = key.replace(' ','_')
      if bool(root[key]) == False:
        # don't bother
        #doc.AddNode(doc.NewNode(safekey),node)
        pass
      # Create recursively a new node
      elif type(root[key]) == type({}):
        newnode = self.toXML(doc, root[key],node=doc.NewNode(safekey))
        # Write conditionally to the fact that newnode must not be empty
        if doc.AllElementsAsDict(newnode):
          doc.AddNode(newnode, node)
      # Add the data as a node if the data has a toXML method
      elif hasattr(root[key],'toXML'):
        doc.AddNode(getattr(root[key],'toXML')(doc),node)
      # If all else fails, add the data as string if it isn't null
      elif root[key]:
        doc.AddField(safekey, str(root[key]), node)
        
    return node
  
  
  def fromXML(self, doc, node, root=None):
    ''' Read in the XML and populate the information tree.
        Bloody complicated piece of code that should work independently of what is in the XML.
    '''
    # Handle the default argument
    if root == None:
      root = self
      
    # Find the new root
    item_name = node.tagName.replace('_', ' ')
      
    children = doc.AllElementsAsDict(node)
    if not children:
      # A text field
      root[item_name] = doc.Get(node)
    for ndkey in children:
      # Get the node itself, then clean up the key name
      nd = children[ndkey]
      ndkey = ndkey.replace('_', ' ')
      # Check to see if it is typed already
      if nd.__class__ == node.__class__:
        # The node is a node, check to see if it has elements
        if doc.AllElementsAsDict(nd):
          # recurse
          if ndkey in root and type(root[ndkey]) == type({}):
            # recurse into this node
            self.fromXML(doc, nd, root[ndkey])
          else:
            # recurse into this node
            self.fromXML(doc, nd, root)
        else:
          # It is a text node (or else, not a node in the tree structure).
          root[ndkey] = doc.Get(nd)
      else:
        root[ndkey] = nd
        
        
class OPORD(sandbox_COMM):
  '''!
   A structured form of OPORD. Meant to contain all the instructions received and generated by the staff
   to conduct operations.
   
   Is formatted almost exactly as a real-world OPORD in its structure, although the data content isn't guarenteed to
   be unstructured text!
   
   Define a Supply Request as formatted in the Canadian Army SUPREQ
   Checklist:
      - Add a Get and Check method.
      - Handle at the FRAGO level
   
  '''
  def __init__(self, sender = None, recipient = None):
    # Other 
    sandbox_COMM.__init__(self, sender, recipient)
    self.status = 'overwrite'
    self.initialized = False
    
    # fields
    self['SITUATION']= {}
    self['SITUATION']['GENERAL'] = ''
    self['SITUATION']['BATTLESPACE'] = {}
    self['SITUATION']['BATTLESPACE']['overlay'] = {}
    # Three free text fields
    self['SITUATION']['BATTLESPACE']['Joint Operation'] = ''
    self['SITUATION']['BATTLESPACE']['HAO'] = ''
    self['SITUATION']['BATTLESPACE']['Area of Interest'] = ''
    self['SITUATION']['BATTLESPACE']['Area of Operation'] = ''
    self['SITUATION']['BATTLESPACE']['AO'] = ''
    self['SITUATION']['ENNEMY FORCES'] = {}
    self['SITUATION']['ENNEMY FORCES']['DISPOSITION'] = []
    self['SITUATION']['FRIENDLY FORCES'] = {}
    self['SITUATION']['FRIENDLY FORCES']['DISPOSITION'] = []
    # free text fields
    self['SITUATION']['FRIENDLY FORCES']['center of gravity'] = ''
    self['SITUATION']['FRIENDLY FORCES']['Gov and NGO agencies'] = ''
    self['SITUATION']['ATTACHMENTS AND DETACHMENTS'] = {}
    self['SITUATION']['ATTACHMENTS AND DETACHMENTS']['ATTACHMENTS'] = []
    self['SITUATION']['ATTACHMENTS AND DETACHMENTS']['DETACHMENTS'] = []
    # free text fields
    self['SITUATION']['assumptions'] = ''
    self['SITUATION']['legal implications'] = ''
    # ----------------------------------------------------------------
    self['MISSION'] = ''
    self['EXECUTION'] = {}
    self['EXECUTION']['INTENTS'] = ''
    self['EXECUTION']['CONCEPT'] = {}
    self['EXECUTION']['CONCEPT']['PRIORITY'] = []
    self['EXECUTION']['CONCEPT']['MANEUVERS']= ''
    self['EXECUTION']['CONCEPT']['FIRE'] = ''
    self['EXECUTION']['CONCEPT']['SUPPORT']= ''
    self['EXECUTION']['MANEUVER TASKS'] = {}
    self['EXECUTION']['MANEUVER TASKS']['cursor'] = 0
    self['EXECUTION']['MANEUVER TASKS']['sequence'] = []
    self['EXECUTION']['SUPPORT TASKS'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['H-hour'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['MOPP'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS']['ENGAGEMENT'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['ENGAGEMENT INSTRUCTIONS']['DISENGAGEMENT'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['REORGANIZATION'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['REPORTING'] = {}
    self['EXECUTION']['COORDINATING INSTRUCTION']['RULES OF ENGAGEMENT'] = {}
    self['EXECUTION']['CCIR'] = []
    self['SERVICE AND SUPPORT'] = {}
    self['SERVICE AND SUPPORT']['TRAIN'] = {}
    self['SERVICE AND SUPPORT']['TRAIN']['UNIT'] = {}
    self['SERVICE AND SUPPORT']['TRAIN']['LOC'] = {}    
    self['SERVICE AND SUPPORT']['MATERIEL'] = {}
    self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY'] = {}
    self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['routine time'] = []
    self['SERVICE AND SUPPORT']['MATERIEL']['TRANSPORTATION'] = {}
    self['SERVICE AND SUPPORT']['MATERIEL']['SERVICES'] = {}
    self['SERVICE AND SUPPORT']['MATERIEL']['MAINTENANCE'] = {}
    self['SERVICE AND SUPPORT']['MATERIEL']['MEDICAL EVACUATION'] = {}
    self['SERVICE AND SUPPORT']['EPW'] = {}
    self['SERVICE AND SUPPORT']['MISCELANEOUS'] = {}
    self['COMMAND AND SIGNAL'] = {}
    self['COMMAND AND SIGNAL']['COMMAND'] = {}
    self['COMMAND AND SIGNAL']['COMMAND']['HIGHER UNIT'] = {}
    self['COMMAND AND SIGNAL']['COMMAND']['ALTERNATE HIGHER UNIT'] = {}
    self['COMMAND AND SIGNAL']['SIGNAL'] = {}
    self['COMMAND AND SIGNAL']['SIGNAL']['SOI'] = {}
    self['COMMAND AND SIGNAL']['SIGNAL']['SILENCE'] = {}
    self['COMMAND AND SIGNAL']['SIGNAL']['COMMUNICATION METHOD PRIORITY'] = {}
    self['COMMAND AND SIGNAL']['SIGNAL']['EMERGENCY SIGNAL'] = {}
    self['COMMAND AND SIGNAL']['SIGNAL']['CODE WORDS'] = {}
    
  def fromXML(self, doc, node, root=None):
    ''' Read in the XML and populate the information tree.
        Bloody complicated piece of code that should work independently of what is in the XML.
    '''
    # Handle the default argument
    if root == None:
      root = self
      
    # Find the new root
    item_name = node.tagName.replace('_', ' ')
      
    children = doc.AllElementsAsDict(node)
    if not children:
      # A text field
      root[item_name] = doc.Get(node)
    for ndkey in children:
      # Get the node itself, then clean up the key name
      nd = children[ndkey]
      ndkey = ndkey.replace('_', ' ')
      # Check to see if it is typed already
      if nd.__class__ == node.__class__:
        # The node is a node, check to see if it has elements
        if doc.AllElementsAsDict(nd):
          # recurse
          if ndkey in root and type(root[ndkey]) == type({}):
            # recurse into this node
            self.fromXML(doc, nd, root[ndkey])
          else:
            # recurse into this node
            self.fromXML(doc, nd, root)
        else:
          # It is a text node (or else, not a node in the tree structure).
          root[ndkey] = doc.Get(nd)
      else:
        root[ndkey] = nd
      
    

  
  def AsHTML(self, owner = None):
    '''
       Render OPORD as HTML code
    '''
    if self.Sender() == None or type(self.Sender()) == type(1):
      return ''
    
    out = ''
    # header
    
    
    out += self.RenderSituation()
    out += self.RenderMission()
    out += self.RenderExecution()
    out += self.RenderCSS()
    out += self.RenderC3()
    
    if out == '':
      out = 'No OPORD at the moment.'
    
    return html.HTMLfile('OPORD view',out)
    

    
  def RenderSituation(self):
    '''! \brief Fully Form an OPORD according to std format
         * Menu entry
         1. Situation
            a) [General] *
            b) Battlespace (specify attachements) *
               1) Joint Operations *
               2) Area of Interest *
               3) Area of Operation *
            c) Enemy Forces (within AO)
            d) Friendly Forces (within AO)
               1) Non-organic forces
                  a) Higher units
                  b) Adjacent units
                  c) Supporting units
               2) Center of gravity * 
               3) Gov and NGO agencies *
            e) Attachment and Detachments (Required field)
            f) Assumption (omitted in orders) 
            g) Legal implications *
            
            \todo render attachements/detachments
    '''
    # Create headers
    out = html.Tag('H2','1 . Situation')
    # level 2
    a = html.Tag('H3','a) General')
    b = html.Tag('H3','b) Battlespace')
    c = html.Tag('H3','c) Enemy Force')
    d = html.Tag('H3','d) Friendly Force')
    e = html.Tag('H3','e) Attachments and Detachments')
    f = html.Tag('H3','f) Assumption')
    g = html.Tag('H3','g) Legal implications')
    
    addSituation = False
    # Free text General
    if self['SITUATION']['GENERAL']:
      out += a + html.Tag('p', self['SITUATION']['GENERAL'])
      addSituation = True
    
    # Specify that there is an attached overlay to the OPORD.
    temp = ''
    if self.GetOverlay(): 
      temp += html.Tag('p','Please refer to attached map overlay %s. '%(self.GetOverlay().name))
      
    # Joint operations
    if self['SITUATION']['BATTLESPACE']['Joint Operation'] or self.GetAO(True):
      if self.GetAO(True):
        S = 'The higher echelon operated within %s. -- '%(self.GetAO(True)) + self['SITUATION']['BATTLESPACE']['Joint Operation']
      else:
        S = self['SITUATION']['BATTLESPACE']['Joint Operation']
        
      temp += html.Tag('p', '<h4>1) Joint Operation and Higher Echelon</h4>%s'%(S))
    
    # Area of interest
    if self['SITUATION']['BATTLESPACE']['Area of Interest']:
      temp += html.Tag('p', '<h4>2) Area(s) of interest</h4>%s'%(self['SITUATION']['BATTLESPACE']['Area of Interest']))
    
    # Area of operation
    if self['SITUATION']['BATTLESPACE']['Area of Operation']or self.GetAO():
      if self.GetAO():
        S = 'The higher echelon operated within %s. -- '%(self.GetAO()) + self['SITUATION']['BATTLESPACE']['Area of Operation']
      else:
        S = self['SITUATION']['BATTLESPACE']['Area of Operation']
      temp += html.Tag('p', '<h4>3) Area of operation</h4>%s'%(S))
      
    if temp:
      out += b + temp
      addSituation = True
          
    # Centre of gravity
    if self['SITUATION']['FRIENDLY FORCES']['center of gravity']:
      d += html.Tag('p', '<h4>2) Center of gravity</h4>%s'%(html.Tag('blockquote',self['SITUATION']['FRIENDLY FORCES']['center of gravity'])))

    # NGO and Gov
    if self['SITUATION']['FRIENDLY FORCES']['Gov and NGO agencies']:
      d += html.Tag('p', '<h4>3) Gov. and NGO agencies</h4>%s'%(html.Tag('blockquote',self['SITUATION']['FRIENDLY FORCES']['Gov and NGO agencies'])))
    if d != html.Tag('H3','d) Friendly Force'):
      out += d
    # Attch/Dtchns
    

    # Assumptions
    if self['SITUATION']['assumptions']:
      f += html.Tag('p', self['SITUATION']['assumptions'])
      addSituation = True
      out += f

    # Legal
    if self['SITUATION']['legal implications']:
      g += html.Tag('p', self['SITUATION']['legal implications'])
      addSituation = True
      out += g

    if addSituation:
      return out
    return ''

    
  def RenderMission(self):
    # Mission
    miss = html.Tag('H2','2. Mission')
    
    txt = self.GetFreeText(['MISSION'])
    if txt:
      return miss + html.Tag('p', txt)
    return ''
    
  def RenderExecution(self):
    '''! \brief The execution part of the OPORD
         a ) Commander's intent
         b ) Concept of Operation
             1) Concept of maneuvers
             2) Concept of fire
             3) Concept of support
             4) Other concepts
         c ) Tasks
         d ) Coordinating Instruction
         e ) Commander's Critical Information Requirements (CCIR)
             * -- NAI (Infiltration, UAV request, OPosts)
    '''
    out = ''
    # Execution
    addExecution = False
    out = html.Tag('H2','3. Execution')
    
    # Free text General
    if self['EXECUTION']['INTENTS']:
      out += html.Tag('H3','a. Commander\'s intent') + html.Tag('p', self['EXECUTION']['INTENTS'])
      addExecution = True
      
    # Concepts
    addconcept = False
    head = html.Tag('H3', 'b. Concept of Operation')
    ops = html.Tag('b', '(1) Concept of maneuver')
    fire = html.Tag('b', '(2) Concept of fire')
    spt = html.Tag('b', '(3) Concept of support')
    if self['EXECUTION']['CONCEPT']['MANEUVERS']:
      head += html.Tag('h4', '(1) Concept of maneuver') + html.Tag('p', self['EXECUTION']['CONCEPT']['MANEUVERS'])
      addconcept = True
    if self['EXECUTION']['CONCEPT']['FIRE']:
      head += html.Tag('h4', '(2) Concept of fire') + html.Tag('p', self['EXECUTION']['CONCEPT']['FIRE'])
      addconcept = True
    if self['EXECUTION']['CONCEPT']['SUPPORT']:
      head += html.Tag('h4', '(3) Concept of support') + html.Tag('p', self['EXECUTION']['CONCEPT']['SUPPORT'])
      addconcept = True
    if addconcept:
      out += head
    
    # Tasking
    addTasks = False
    if self.GetTaskList():
      addTasks = True
      tasking = html.Tag('H3','c. Tasks')
      A = self.recipient['agent']
      donetask = True
      for i in xrange(len(self.GetTaskList())):
        if self.GetCurrentTask() == self.GetTaskList()[i]:
          tasking = tasking + html.Tag('p',html.Tag('strong','Task %d : '%(i+1)) + self.GetTaskList()[i].OrderHTML(A),'style="text-decoration: underline;"')
          donetask = False
        else:
          if donetask:
            mod = '(done)'
          else:
            mod = ''
          tasking = tasking + html.Tag('p',html.Tag('strong','Task %d : '%(i+1)) + self.GetTaskList()[i].OrderHTML(A) + mod) 
    if addTasks:
      addExecution = True
      out += html.Tag('blockquote',tasking)
      
    # Coordination instructions
    addCoordination = False
    coord = html.Tag('h3','d. Coordination instructions')
    if self.GetHhour():
      addCoordination = True
      coord += html.Tag('h4','(1) Timing') + html.Tag('p','H-hour is set to %s.'%(self.GetHhour().strftime('%H%M ZULU (%d %b %y)')))
    if addCoordination:
      addExecution = True
      out += html.Tag('blockquote',coord)
      
    # Critical 
    if self['EXECUTION']['CCIR']:
      ccir = html.Tag('H3', 'e. Commander\'s Critical Information Requirements (CCIR)')
      ccir += html.Tag('p', 'To perform this mission, the following Named Area of Interest (NAI) are required to be covered.')
      ccir += '<ol>'
      for i in self['EXECUTION']['CCIR']:
        ccir += '<li>%s</li>'%(str(i))
      ccir += '</ol>\n'
      out += ccir
      addExecution = True
      
    if addExecution:
      return out
    return ''
  
  def RenderCSS(self):
    '''! \brief 
         4. Administration and Logistics
         a. Personel
         b. Logistics
         c. Public Affairs
         d. Civil Affairs
         e. Meteorological Information
         f. GIS
         g. Medical Services
         
    '''
    # CSS ##########################################
    addCSS = False
    out =  html.Tag('H2','4. Administration and Logistics')
    
    # a. Personel
    
    
    # Train
    addLog = False
    train = html.Tag('H3','b. Logistics')
    if self.GetCSS() or self.GetMSR() or self.GetRoutineRessuplyTime():
      supU = html.Tag('H4', '(1) Supply Unit / MSR')
      HQ = self.Sender().sim.AsEntity(self.GetCSS())
      if self.GetCSS():
        addtrain = True
        supU += html.Tag('strong','Supply Unit : ') + 'Forward all materiel request to %s. <BR>'%(HQ.GetName()) 
      # MSR 
      if self.GetMSR():
        addMSR = True
        supU += 'The CSS train to your position is to follow %s define in overlay %s. '%(self.GetMSR()[0], self.GetOverlay().name)
      # Routine ressupo time
      if self.GetRoutineRessuplyTime():
        temp = self.GetRoutineRessuplyTime()
        supU += 'You are required to ressuply on a routine basis at '
        for i in temp:
          supU += i + ', '
        supU = supU[:-2] + '. '
        addTime = True
      # Add to train
      addLog = True
      train += supU
    
    # Material
    materiel = ''
    addMateriel = False
    if self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY'].has_key('minimum') or self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY'].has_key('maximum'):
      addMateriel = True
      materiel = materiel + html.Tag('strong','Ressuply Policy : ')
      if self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['minimum']:
        materiel = materiel + 'You must maintain at least %.2f basic loads. Falling below this level must be remediated with an emergency ressuply request. '%(self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['minimum'])
      if self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['maximum']:
        materiel = materiel + 'You are required to stockpile %.2f basic loads. '%(self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['maximum'])
    if addMateriel:
      addLog = True
      train += html.Tag('H4','(2) Materiel Levels') + html.Tag('p',materiel)
      
    if addLog:
      addCSS = True
      out += train
      
    if addCSS:
      return out
    return ''
    
  def RenderC3(self):
    '''! \brief Last section of the OPORD
         5. Command and Signal
         a. Command relationship
         b. Command Post and Headquater
         c. Succession of command
         d. Signal
    
    '''
    # C4I ##################################################
    addC3 = False
    out =  html.Tag('H2','5. Command and Signal')
    
    # Higher command
    hqstr = html.Tag('H3', 'a. Command relationship') + '\n'
    addHigherUnit = False
    if self.GetHQ():
      addHigherUnit = True
      HQ = self.Sender().sim.AsEntity(self.GetHQ())
      hqstr += html.Tag('strong','Higher Unit : ') + 'Report to %s.<BR>'%(HQ.GetName())
    if self.GetHQ('alternate'):
      addHigherUnit = True
      HQ = self.Sender().sim.AsEntity(self.GetHQ('alternate'))
      hqstr += html.Tag('strong','Alternate Higher Unit : ') + 'For contingency, report to %s.<BR>'%(HQ.GetName())
    if addHigherUnit:
      addC3 = True
      out += hqstr
      
    if addC3:
      return out
    return ''
  
  # Interface
  def IsSuppressed(self):
    '''
       Randomly check against the C4I level of the OPORD
    '''
    if random() > self['C3 level']:
      return 1
    return 0
  
  #
  # Free Text methods
  def GetFreeText(self, vector):
    '''! \brief Return the free text for an arbitrary field
    '''
    out = self[vector[0]]
    for i in vector[1:]:
      out = out[i]
    return out
  
  def SetFreeText(self, vector, text):
    '''! \brief Set text to vector as text
    '''
    s = vector[-1]
    if s == 'GENERAL':
      self['SITUATION']['GENERAL'] = text
    elif s == 'Joint Operation':
      self['SITUATION']['BATTLESPACE']['Joint Operation'] = text
    elif s == 'Area of Interest':
      self['SITUATION']['BATTLESPACE']['Area of Interest'] = text
    elif s == 'Area of Operation':
      self['SITUATION']['BATTLESPACE']['Area of Operation'] = text
    elif s == 'center of gravity':
      self['SITUATION']['FRIENDLY FORCES']['center of gravity'] = text
    elif s == 'Gov and NGO agencies':
      self['SITUATION']['FRIENDLY FORCES']['Gov and NGO agencies'] = text
    elif s == 'assumptions':
      self['SITUATION']['assumptions'] = text
    elif s == 'Legal implications':
      self['SITUATION']['legal implications'] = text
    elif s == 'MISSION':
      self['MISSION'] = text
    elif s == 'INTENTS':
      self['EXECUTION']['INTENTS'] = text
    elif s == 'MANEUVERS':
      self['EXECUTION']['CONCEPT']['MANEUVERS'] = text
    elif s == 'FIRE':
      self['EXECUTION']['CONCEPT']['FIRE'] = text
    elif s == 'SUPPORT':
      self['EXECUTION']['CONCEPT']['SUPPORT'] = text
      
  # Tasking Interface  
  def SetAO(self, AO, higher = False):
    '''! \brief Set the AO name at the right place.
    '''
    
    if higher:
      v = ['SITUATION','BATTLESPACE','HAO']
    else:
      v = ['SITUATION','BATTLESPACE','AO']
    self.SetData(v,AO)
    
  def GetAO(self,higher = False):
    if higher:
      return self.GetData(['SITUATION','BATTLESPACE','HAO'])
    return self.GetData(['SITUATION','BATTLESPACE','AO'])
  
  def SetOverlay(self, overlay):
    '''! \brief Set an overlay to be indexed by its name
         
         default overlay has no key
    '''
    self.SetData(['SITUATION','BATTLESPACE','OVERLAY'], overlay)
      
  def GetOverlay(self):
    '''! \brief Access an overlay.
    
         If no name is provided, and there is only one overlay of a different name, return it as such.
         This is mainly a backward compatibility with the initial code.
    '''
    x = self.GetData(['SITUATION','BATTLESPACE','OVERLAY'])
    if not x:
      x = operational_overlay()
      self.SetData(['SITUATION','BATTLESPACE','OVERLAY'], x)
      
    return x
  
  def InsertToCurrentTask(self, task):
    cursor = self.GetData(['EXECUTION','MANEUVER TASKS','cursor'])
    self.InsertTask(cursor,task)
    
  def InsertTask(self, index, task):
    '''
       does What it claims
    '''
    task['opord'] = self
    self.GetData(['EXECUTION','MANEUVER TASKS','sequence']).insert(index,task)
    
  def GetContactList(self):
    '''
    '''
    out = []
    friends = self.GetData(['SITUATION','FRIENDLY FORCES','DISPOSITION'])
    if not friends:
      friends = []
    eny = self.GetData(['SITUATION','ENNEMY FORCES','DISPOSITION'])
    if not eny:
      eny = []
      
    for i in friends + eny:
            out.append(i)
    return out

  def GetPriorities(self):
    return self.GetData(['EXECUTION','CONCEPT','PRIORITY'],[])
  def SetPriorities(self, P):
    self.SetData(['EXECUTION','CONCEPT','PRIORITY'],P)
  def GetHhour(self):
    return self.GetData(['EXECUTION','COORDINATING INSTRUCTION','HHOUR'],None)
  def SetHhour(self, H):
    self.SetData(['EXECUTION','COORDINATING INSTRUCTION','HHOUR'],H)
  def GetHQ(self, alternate = False):
    if not alternate:
      return self.GetData(['COMMAND AND SIGNAL','COMMAND','HIGHER UNIT'])
    return self.GetData(['COMMAND AND SIGNAL','COMMAND','ALTERNATE HIGHER UNIT'])
  
  def GetCSS(self):
    return self.GetData(['SERVICE AND SUPPORT','TRAIN','UNIT'])
  def SetCSS(self, CSSunit):
    self.SetData(['SERVICE AND SUPPORT','TRAIN','UNIT'],CSSunit)
  
  def GetMSR(self):
    return self.GetData(['SERVICE AND SUPPORT','TRAIN','LOC'])
  
  def SetMSR(self, loc):
    self.SetData(['SERVICE AND SUPPORT','TRAIN','LOC'],loc)
  
  def SetRoutineRessuplyTime(self, mytime):
    self.SetData(['SERVICE AND SUPPORT','MATERIEL','SUPPLY','routine time'],mytime)
  def GetRoutineRessuplyTime(self):
    return self.GetData(['SERVICE AND SUPPORT','MATERIEL','SUPPLY','routine time'])
    return self['SERVICE AND SUPPORT']['MATERIEL']['SUPPLY']['routine time']
  
  def SetHQ(self, HQuid, alternate = None):
    ''' HQuid must be a uid
    '''
    if not alternate:
      self.SetData(['COMMAND AND SIGNAL','COMMAND','HIGHER UNIT'],HQuid)
    else:
      self.SetData(['COMMAND AND SIGNAL','COMMAND','ALTERNATE HIGHER UNIT'], HQuid)
      
  def GetSupplyPolicies(self):
    '''
       Return the policie for the ressuply.
    '''
    return self.GetData(['SERVICE AND SUPPORT','MATERIEL','SUPPLY'])
  def SetSupplyMinMaxPolicies(self, gmin = None, gmax = None):
    '''
       Specifically set min and max to the supply policies. 
       Flip min and max if they are illogically ordered.
    '''
    if gmin != None and gmax != None and gmin >= gmax:
      temp = gmin
      gmin = gmax
      gmax = temp
    
    if gmin != None:
      self.SetData(['SERVICE AND SUPPORT','MATERIEL','SUPPLY','minimum'],gmin)
    if gmax != None:
      self.SetData(['SERVICE AND SUPPORT','MATERIEL','SUPPLY','maximum'],gmax)
    
  def SetTaskList(self, lst, css = None):
    '''! \brief set a task list.
         make sure that the cursor points to the first incomplete task.
    '''
    if css:
      self.SetData(['EXECUTION','SUPPORT TASKS','sequence'],lst)
    else:
      self.SetData(['EXECUTION','MANEUVER TASKS','sequence'],lst)
      # Set cursor to first task that isn't completed.
      self.AutoCursor()
    
  def AutoCursor(self):
    '''! \brief Set the cursor to the first non-completed task.
    '''
    tasks = self.GetData(['EXECUTION','MANEUVER TASKS','sequence'])
    # Set cursor to first task that isn't completed.
    for i in range(len(tasks)):
      if not tasks[i].IsCompleted():
        self.SetData(['EXECUTION','MANEUVER TASKS','cursor'], i)
        return i
    # Set to 1+ last task!
    self.SetData(['EXECUTION','MANEUVER TASKS','cursor'], len(tasks))
    return len(tasks)
        
  def GetTaskList(self, css = None):
    '''! \brief Return a list of tasks for planners
         \param css [default = None], the css flag returns the CSS tasks instead of maneuvers.
        
         \note Does not expand to subtasks.
    '''
    if css:
      return self.GetData(['EXECUTION','SUPPORT TASKS','sequence'],[])
    else:
      return self.GetData(['EXECUTION','MANEUVER TASKS','sequence'],[])
  
  def GetExpandedTaskList(self):
    '''! \brief Return a complete list of subtasks for methods requiring an exhautive iteration.
    '''
    # Iterate recursively over each subtasks
    out = []
    for i in self.GetData(['EXECUTION','MANEUVER TASKS','sequence']):
      out.extend(i.ExpandedSubtaskList())
    return out

    
    
  def AddTask(self, task):
    '''!
       Add a task to the queue
    '''
    task['opord'] = self
    self.SetData(['EXECUTION','MANEUVER TASKS','sequence']).append(task)
    self.AutoCursor()

      

  def CancelTask(self, task):
    '''! \brief Orderly abort ongoing task or delete future tasks.
    '''
    if task in self.GetTaskList():
      # If task is in the future
      if task['begin time']:
        task.Cancel(self.recipient)
      else:
        self.GetTaskList().remove(task)
        
      self.recipient['agent'].ProcessOPORDTasks(self)
      self.recipient['agent'].EstimateOPORDTiming(self)    
      self.recipient['agent'].SolveOPORDRessuply(self)
  
  def SetCurrentWaypoints(self, wp):
    self.GetCurrentSubTask()['waypoints'] = wp
    
  def SetRessuplyRoute(self, route):
    '''
       Allow to set a ressuply route.
    '''
    self.SetData(['SERVICE AND SUPPORT','TRAIN','LOC'], route)
    
  def GetCurrentWaypoints(self):
    '''
       Return the list of waypoints
    '''
    if self.GetCurrentTask():
        if self.GetCurrentSubTask().has_key('waypoints'):
            return self.GetCurrentSubTask()['waypoints']
        else:
            return []
    else:
        return []
    
  def GetCurrentTask(self):
    # Returns nothing if there is no sequence
    if not self.GetData(['EXECUTION','MANEUVER TASKS','sequence']):
      return None
    # If there is no tasks, the cursor should be None, not 0.
    i = self,GetData(['EXECUTION','MANEUVER TASKS','cursor'])
    if i == None:
      return None
    
    try:
      return self.GetData(['EXECUTION','MANEUVER TASKS','sequence'])[i]
    except:
      return None
  
  def GetCurrentSubTask(self):
    '''! \brief Return the subtask currently in action
    '''
    Tk = self.GetCurrentTask()
    if Tk:
      return Tk.GetSubTask()
    
    return None 
  
  def GetNextTask(self):
    try:
      return self['EXECUTION']['MANEUVER TASKS']['sequence'][self.AutoCursor()]
    except:
      return None
    
  def NextTaskCanBegin(self, ctime):
    '''
       Determine whether the next task can begin.
    '''
    N = self.GetNextTask()
    if N:
      return N.CanBegin(ctime,self.GetHhour())

    # No next task, ready to let go anyway.
    return True

  
  def NextTask(self, E):
    '''!
       Indicate to the staff to implement the next task. Return 0 if out of tasks
    '''
    # Increment subtask if applicable
    if self.GetCurrentTask() and not self.GetCurrentTask().IsCompleted():
      self.GetCurrentTask().NextSubTask(E)
      return True
    
    # Move on to next phase/task
    cursor = self.AutoCursor()
    self.SetData(['EXECUTION','MANEUVER TASKS','cursor'], cursor+1)
    if self.GetData(['EXECUTION','MANEUVER TASKS','cursor']) < len(self.GetData(['EXECUTION','MANEUVER TASKS','sequence'])):
      return True
    
    # No increment possible
    return False

      
  def AddCSSTask(self, task):
    '''
       Add a support task to perform.
    '''
    self.SetData(['EXECUTION','SUPPORT TASKS','sequence']).append(task)
    if self['EXECUTION']['SUPPORT TASKS']['cursor'] == None:
      self['EXECUTION']['SUPPORT TASKS']['cursor'] = 0
      
  def MergeFRAGO(self, frago):
    '''
       Intergrate the FRAGO elements into the instance.
    '''
    # Situation
    # General situation
    if frago.GetFreeText(['SITUATION','GENERAL']):
      self.SetFreeText( ['SITUATION','GENERAL'] , frago.GetFreeText(['SITUATION','GENERAL']))
      
    # AO
    if frago.GetAO(True):
      self.SetAO(frago.GetAO(True))
      
    # Joint Operation
    temp = frago.GetFreeText(['SITUATION','BATTLESPACE','Joint Operation'])
    if temp:
      self.SetFreeText( temp )
      
    # Area of interest
    temp = frago.GetFreeText(['SITUATION','BATTLESPACE','Area of Interest'])
    if temp:
      self.SetFreeText( temp )
      
    # Area of Operation
    if frago.GetAO():
      self.SetAO(frago.GetAO())

    # Text to update
    ttu = []
    ttu.append(['SITUATION','BATTLESPACE','Area of Operation'])
    ttu.append(['SITUATION','FRIENDLY FORCES','center of gravity'])
    ttu.append(['SITUATION','FRIENDLY FORCES','Gov and NGO agencies'])
    ttu.append(['SITUATION','assumptions'])
    ttu.append(['SITUATION','legal implications'])
    ttu.append(['MISSION'])
    
    for i in ttu:
      temp = frago.GetFreeText(i)
      if temp:
        self.SetFreeText( i,temp )
    
    # Execution
    # tasking overwrite
    self.SetTaskList(frago.GetTaskList())
    
    # change H-hour
    if frago.GetHhour():
      self.SetHhour(frago.GetHhour())
    
    # Support
    # CSS
    # Supply unit
    if frago.GetCSS():
      self.SetCSS(frago.GetCSS())
    # Main supply route
    if frago.GetMSR():
      self.SetMSR(frago.GetMSR())
    # supply policies
    temp = frago.GetSupplyPolicies()
    if temp.has_key('minimum') and temp.has_key('maximum'):
      self.SetSupplyMinMaxPolicies(temp['minimum'],temp['maximum'])
      
    
    
    # Command
    # HQ
    if frago.GetHQ():
      self.SetHQ(frago.GetHQ())
  
'''
   
'''
class SUPREQ(sandbox_COMM):
  def __init__(self, sender = None, recipient = None):
    self['UNIT'] = {}
    self['TYPE'] = 'normal' # could also be supplementary, emergency or controlled
    self['COMMODITY'] = {} # Pair of type and quantity, type can be 'bulk' or a class of supply
    self['DP'] = {} # Where to send the convoy as suggested by the requesting unit.
    
  def IsSuppressed(self):
    '''
       Randomly check against the C4I level of the OPORD
    '''
    if random() > self['C3 level']:
      return 1
    return 0
  
  def FillFromTask(self, task, unit):
    '''!
       Fill the request for a Dispatch Supply from a Ressuply task .
       Unused, should delete? 
    '''
    self['UNIT'] = unit.sim.AsUID(unit)
    self.sender = self['UNIT']
    self['DP'] = task['destination']
    self['COMMODITY'] = task['request']
    self['CSS unit'] = unit.sim.AsUID(task['CSS unit'])
    self['uid'] = task['uid']
    try:
      self['TYPE'] = task['priority']
    except:
      pass
    
  def AsHTML(self):
    '''
       Plain english.
    '''
    return '<p>Unimplmented</p>'

class SPOTREP(sandbox_COMM):
  def __init__(self, sender = None, recipient = None, cnt = None, C4Ilevel = 1.0):
    sandbox_COMM.__init__(self, sender,recipient)
    self.cnt = cnt
    self['C3 level'] = C4Ilevel
    
    # templating
    self.template = 'SPOTREP.txt'
    
  def AsText(self):
    return 'Contact Report from %s\n%s\n'%(self.Sendername(), str(self.cnt))
  def AsHTML(self):
    return self.ConvertToHTML()
'''
   Data structure of the situation report
'''

class INTSUM(sandbox_COMM):
  def __init__(self, sender = None):
    sandbox_COMM.__init__(self, sender)
    self['contacts'] = []
    
  def __str__(self):
    out = 'INTSUM from %s\n\n'%(self.SenderName())
    line = '#############################################\n\n'
    for i in self['contacts']:
      out = out + str(i) + '\n' + line
    return out
      
  def ContactList(self, lst = None):
    '''
       if lst == None --> return the contact list
          lst == contact --> add to the list
          lst == [] --> replace the list altogehter
    '''
    if lst == None:
      return self['contacts']
    elif type(lst) == type([]):
      self['contacts'] = lst
    else:
      self['contacts'].append(lst)

class SITREP(sandbox_COMM):
  def __init__(self, me = None, gcontacts = None, gfriends = None, rep = None, C4Ilevel = 1.0):
    sandbox_COMM.__init__(self, me)
    # templating
    self.template = 'SITREP.txt'
    
    self.contacts = gcontacts
    self.friends = gfriends
    if rep:
      self.report = rep
    else:
      self.report = ''
    
    self['C3 level'] = C4Ilevel
    
  def AsHTML(self):
    return str(self)
    
  def __str__(self):
    return self.report

  


class CODEWORD(sandbox_COMM):
  def __init__(self, sender, recipient, CODE):
    sandbox_COMM.__init__(self, sender, recipient)
    self.message = CODE
    
  

import unittest

class TestCaseOPORD(unittest.TestCase):
  def testLoadfromXML(self):
    # Test files
    filename = os.path.join(os.environ['OPCONhome'], 'tests', 'opord.xml')
    
    # Get the XML data
    from sandbox_XML import sandboXML
    doc = sandboXML(read=filename)
    opord = doc.Get(doc.root, 'COMM')
    opord.SetMSR('ROUTE BLUE')
    
    # Write the node info
    newopordnode = opord.toXML(doc)
    outxml = sandboXML('COMMS')
    outxml.AddNode(newopordnode, outxml.root)
    with open(os.path.join(os.environ['OPCONhome'], 'tests', 'testOPORD.xml'),'w') as fout:
      fout.write(str(outxml))
    
    # Test for the structure of the OPORD
    self.assertTrue(opord)
    
  def testWriteOPORDtoXML(self):
    # Test files
    filename = os.path.join(os.environ['OPCONhome'], 'tests', 'opord.xml')
    
    # Get the XML data
    from sandbox_XML import sandboXML
    doc = sandboXML(read=filename)
    opord = doc.Get(doc.root, 'COMM')
    
    # Write to an XML node
    doc.AddNode(opord.toXML(doc))
    
    
  def testEmptyOPORD(self):
    opord = OPORD()
    self.assertEqual(0,len(opord.GetExpandedTaskList()))
    
  def testSimpleFRAGOMerge(self):
    opord = OPORD()
    opord.SetMSR(range(10))
    opord.SetCSS(10)
    
    
    frago = OPORD()
    frago.SetMSR(range(5))
    frago.SetHQ(8)
    
    # function
    opord.MergeFRAGO(frago)
    
    temp = [opord.GetMSR(), opord.GetCSS(), opord.GetHQ()]
    self.assertEqual([range(5),10,8], temp)
    
    
  def testSetMinMaxSupplyPolicies(self):
    O = OPORD()
    O.SetSupplyMinMaxPolicies(1.0,2.0)
    temp = O.GetSupplyPolicies()
    
    self.assert_(temp['minimum']==1.0 and temp['maximum']==2.0)
    
  def testSetMinMaxSupplyError(self):
    O = OPORD()
    O.SetSupplyMinMaxPolicies(2.0,1.0)
    temp = O.GetSupplyPolicies()
    
    self.assert_(temp['minimum']==1.0 and temp['maximum']==2.0)

if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(TestCaseOPORD))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)