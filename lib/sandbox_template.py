'''
   A devellopment solution to maintaining template and OOB. BuilderUnit() is a better production
   solution, though.
'''
import syspathlib

import os
import os.path
import pickle
from copy import deepcopy

import sandbox_entity
from logistics import supply_package

# import  models
from logistics import system_logistics as logistics
from logistics import system_logistics_CSS as logistics_css
from movement import system_movement as movement
from intelligence import system_intelligence as intelligence
from intelligence import sandbox_contact
from combat import system_combat as combat
from combat import sandbox_engagement as engagement
from C4I import system_C4I as C4I

from sandbox_XML import sandboXML, XMLParseError

from logistics import system_logistics_CSS as CSSlogistics

class sandbox_XML_templates:
  '''! \brief Interface to templates for units and models within the XML framework.
  '''
  instancemap = {'movement':movement, 'combat':combat, 'logistics':logistics, 'logistics_css':logistics_css,'intelligence':intelligence,'C3':C3}
  def __init__(self, modules = ['base']):
    '''!'''
    # Folder
    self.base_folder = os.path.join(os.getcwd(), 'Data')
    
    # List 
    self.modules = modules
    
    # Dictionaries of nodes
    self.templates = {'unit':{},'C3':{},'intelligence':{},'logistics':{},'combat':{},'movement':{}}
    
    for m in self.modules:
      self._indexmodule(m)
      
  def _getXMLDoc(self, name):
    '''! \brief Test existence and return a sandboxXML object. name MUST NOT contain the xml extension.
    '''
    fname = os.path.join(self.base_folder, name + '.xml')
    if os.access(fname, os.F_OK):
      return sandboXML(read=fname)
    else:
      raise XMLParseError('Module File not found', name)
  
  def _indexmodule(self, mname):
    '''! \brief index into RAM the module of name.
    '''
    try:
      doc = self._getXMLDoc(mname)
      # Make sure that it parsed
      if not doc:
        raise XMLParseError('ErrorParsingTemplateFile', mname)
      
      # Make sure that the root is a templates node
      if doc.root.tagName != 'templates':
        XMLParseError('Root node isn\'t a template node', mname)
        
      # Proceeds into templates
      # Units
      for unit in doc.Get(doc.root, 'units', True):
        for U in doc.Get(unit, 'unit',True):
          self.templates['unit'][doc.Get(U,'name')] = U
          
      # models
      mods = ['logistics', 'intelligence', 'combat', 'C3', 'movement']
      for ms in doc.Get(doc.root, 'models', True):
        for model in ms.childNodes:
          if hasattr(model, 'tagName') and str(model.tagName) in mods:
            self.templates[str(model.tagName)][doc.Get(model, 'name')] = model
          
      
        
    except XMLParseError, e:
      print "Template module %s not loaded: %s"%(e.data, e.message)

  def LoadUnit(self, doc, node):
    '''! \brief Load unit from the scenario doc/node pair.
         \param doc A sandboxXML instance.
         \param node A node containing a unit definition.
    '''
    out = None
    # Identity information #####################################################
    name = doc.Get(node, 'name')
    side = doc.Get(node, 'side')
    level = doc.Get(node, 'command_echelon')
    size = doc.Get(node, 'size')
    TOE = doc.Get(node, 'TOE')
    if TOE:
      TOE = doc.Get(TOE, 'category')
    
    # Load template
    if doc.Get(node, 'template'):
      # Get from template definition
      out = self.LoadUnit(doc, self.templates['unit'][doc.Get(node,'template')])
      if name:
        out['name'] = name
      if side:
        out['side'] = side
      if level:
        out['command_echelon'] = level
      if size:
        out['size'] = size
      if TOE:
        out['TOE'] = TOE
    else:
      # Instanciate the entity, use the kwargs trick in the process.
      kwargs = {}
      if name:
        kwargs['name'] = name
      if side:
        kwargs['side'] = side
      if level:
        kwargs['command_echelon'] = level
      if size:
        kwargs['size'] = size
      if TOE:
        kwargs['TOE'] = TOE
      out = sandbox_entity.sandbox_entity(**kwargs)
    # ##################################################################
    # Model Section
    ms = doc.Get(node, 'models')
    if doc.Get(ms, 'C3'):
      out.SetModelC4I(self.LoadModel(doc, doc.Get(ms, 'C3')))
    if doc.Get(ms, 'movement'):
      out.SetModelMovement(self.LoadModel(doc, doc.Get(ms, 'movement')))
    if doc.Get(ms, 'intelligence'):
      out.SetModelIntelligence(self.LoadModel(doc, doc.Get(ms, 'intelligence')))
    if doc.Get(ms, 'combat'):
      out.SetModelCombat(self.LoadModel(doc, doc.Get(ms, 'combat')))
    if doc.Get(ms, 'logistics'):
      out.SetModelLogistics(self.LoadModel(doc, doc.Get(ms, 'logistics')))
    elif doc.Get(ms, 'logistics_css'):
      out.SetModelLogistics(self.LoadModel(doc, doc.Get(ms, 'logistics_css')))
    
    return out
  
  def LoadModel(self, doc, node):
    '''! \brief Instanciate a model from a node, possibly resorting to templates in the process. 
    '''
    out = None
    # Fetch Template 
    if doc.Get(node, 'template'):
      # Is the template defined?
      if doc.Get(node, 'template') in self.templates[node.tagName].keys():  
        out = self.LoadModel(doc, self.templates[node.tagName][doc.Get(node, 'template')])
    
    # Instanciate
    if out == None:     
      out = self.instancemap[node.tagName]()
      
    # Parse the content of the node
    out.fromXML(doc, node)
    return out


  
      
'''
   This class wraps all the DB for building units and formation.
   Save() is necessary only if the DB is changed.
'''
class sandbox_templates:
  def __init__(self):
    pass
  
  def Make(self, system, template):
    try:
      s = 'Make%s%s'%(system,template)
      ex = getattr(self,s)
      return ex()
    except:
      print "Failed to build %s"%(s)
      
  def Create(self, system, template, keyw = {}):
    try:
      s = 'Create%s%s'%(system,template)
      ex = getattr(self,s)
      return ex(**keyw)
    except:
      print "Failed to build %s" %(s)   
      
  # C4I #########################################################
  def MakeC3Default(self):
    return C4I()
  
  # Movement ###################################################
  def MakeMovementDefault(self):
    return movement()
  
  def MakeMovementLeg(self):
    return movement(speed=6.0, mode='leg')
  
  def MakeMovementwheeled(self):
    return movement(speed=35.0, mode='wheeled')
  
  def MakeMovementtracked(self):
    return movement(speed=35.0, mode='tracked')
  
  def MakeMovementair(self):
    return movement(speed=200.0, mode='air')
  
  def MakeMovementLOGPAC(self):
    return movement(speed=0.0, mode='leg')
  
  # Combat #####################################################
  def MakeCombatDefault(self):
    return combat()
  
  def MakeCombatStaff(self):
    # HQ compbat profile
    return combat(RCP=1.0,footprint=1.0)
  def MakeCombatRecceTroop(self):
    # HQ compbat profile
    return combat(RCP=1.0,footprint=2.5)
  def MakeCombatMechBn(self):
    return combat(RCP=10.0,footprint=3.0)
  
  def MakeCombatArmorBn(self):
    return combat(RCP=20.0,footprint=2.0)
  def MakeCombat155SpBty(self):
    return combat(RCP=5.0, footprint=1.0, minrange=4.0, maxrange=22.0)
  def MakeCombat155SpBn(self):
    return combat(RCP=15.0, footprint=1.0, minrange=4.0, maxrange=22.0)
  def MakeCombatLOGPAC(self):
    return combat(RCP=0.5,footprint=0.01)
    
  # Intelligence ###############################################
  def MakeIntelligenceDefault(self):
    return intelligence()
  def MakeIntelligenceMechBn(self):
    out = intelligence()
    out['signature']['transit'] = 0.8
    out['signature']['deployed'] = 0.6
    return out
  
  def MakeIntelligenceArmorBn(self):
    out = intelligence()
    out['signature']['transit'] = 0.95
    out['signature']['deployed'] = 0.8
    return out  
  
  def MakeIntelligenceBdeHHC(self):
    out = intelligence()
    out['signature']['transit'] = 0.95
    out['signature']['deployed'] = 0.9
    return out
  
  def MakeIntelligenceFSB(self):
    out = intelligence()
    out['signature']['transit'] = 0.95
    out['signature']['deployed'] = 0.9
    return out
  
  def MakeIntelligenceconvoy(self):
    out = intelligence()
    out['signature']['transit'] = 0.7
    out['signature']['deployed'] = 0.55
    return out
  def MakeIntelligenceRecceTroop(self):
    out = intelligence()
    out['signature']['transit'] = 0.3
    out['signature']['deployed'] = 0.15
    return out  
  def MakeIntelligenceLOGPAC(self):
    out = intelligence()
    out['signature']['transit'] = 0.3
    out['signature']['deployed'] = 0.2
    return out
  
  # Logistics ##################################################
  def MakeLogisticsDefault(self):
    return logistics()
  
  def MakeLogisticsMechBn(self):
    out = logistics()
    out.ConsumptionInitialize('mech',10.0,4*14, 900,'Bn')
    # According to TOE (MG team) of freight beyond TOE allowance using organic vehicles
    out['freight'] = supply_package(14.8)
    return out
    
  def MakeLogisticsArmorBn(self):
    out = logistics()
    out.ConsumptionInitialize('armor',10.0,4*14, 225,'Bn')
    # According to TOE (MG team) of freight beyond TOE allowance using organic vehicles
    out['freight'] = supply_package(1.3)
    return out
  def MakeLogistics155SpBty(self):
    out = logistics()
    out.ConsumptionInitialize('155SP',5.0, 20, 60,'Coy')
    # According to TOE (MG team) of freight beyond TOE allowance using organic vehicles
    out['freight'] = supply_package(1.3)
    return out
  def MakeLogisticsBdeHHC(self):
    out = logistics()
    out.ConsumptionInitialize('motor',1.0,24, 40,'Bn')
    # According to TOE, in excess using organic vehicle
    out['freight'] = supply_package(19.25)
    return out
  
  def MakeLogisticsFSB(self):
    out = CSSlogistics()
    out.ConsumptionInitialize('motor',1.0,100, 50,'Bn')
    # According to TOE, in excess using organic vehicle
    out['freight'] = supply_package(200.0)
    return out
  
  def MakeLogisticsconvoy(self):
    out = logistics()
    out.ConsumptionInitialize('motor',1.0,10, 5,'Coy')
    # According to TOE, in excess using organic vehicle
    out['freight'] = supply_package(0.0)
    return out
  def MakeLogisticsRecceTroop(self):
    out = logistics()
    # 12 vehicles, 30 men
    out.ConsumptionInitialize('motor',1.0,12, 30,'Plt')
    # According to TOE, in excess using organic vehicle
    out['freight'] = supply_package(1.0)
    return out
  
  def MakeLogisticsLOGPAC(self):
    out = logistics()
    out.ConsumptionInitialize('LOGPAC', 1.0, 0, 0,'Coy')
    # According to TOE, in excess using organic vehicle
    out['freight'] = supply_package(0.0)
    return out
    
  # Unit #######################################################
  def CreateUnitDefault(self, gname = '', gside = 'Blue'):
    # Make a unit with all defaults
    out = sandbox_entity.sandbox_entity(gname,'Coy')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','Default'))
    out.SetModelCombat(self.Make('Combat','Default'))
    out.SetModelLogistics(self.Make('Logistics','Default'))
    out.SetModelMovement(self.Make('Movement','Default'))
    return out
  
  # Combat Units #####################
  # Mechanized infantry
  def CreateUnitMechBn(self, gname = '', gside = 'Blue'):
    # A generic Mechanized Bn
    out =  sandbox_entity.sandbox_entity(gname,'Bn','mech')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','MechBn'))
    out.SetModelCombat(self.Make('Combat','MechBn'))
    out.SetModelLogistics(self.Make('Logistics','MechBn'))
    out.SetModelMovement(self.Make('Movement','tracked'))
    return out
  
  def CreateUnitArmorBn(self, gname = '', gside = 'Blue'):
    # A generic Mechanized Bn
    out = sandbox_entity.sandbox_entity(gname,'Bn','armor')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','ArmorBn'))
    out.SetModelCombat(self.Make('Combat','ArmorBn'))
    out.SetModelLogistics(self.Make('Logistics','ArmorBn'))
    out.SetModelMovement(self.Make('Movement','tracked'))    
    return out
  
  # Fire Support Units
  def CreateUnit155SPBty(self, gname = '', gside = 'Blue'):
    # A generic 155mm SP Bty
    out = sandbox_entity.sandbox_entity(gname,'Coy','sp-art')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','ArmorBn'))
    out.SetModelCombat(self.Make('Combat','155SpBty'))
    out.SetModelLogistics(self.Make('Logistics','155SpBty'))
    out.SetModelMovement(self.Make('Movement','tracked'))    
    return out
  
  # Combat Support Units
  def CreateUnitRecceTroop(self, gname = '', gside = 'Blue'):
    out = sandbox_entity.sandbox_entity(gname,'Plt','recce')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','RecceTroop'))
    out.SetModelCombat(self.Make('Combat','RecceTroop'))
    out.SetModelLogistics(self.Make('Logistics','RecceTroop'))
    out.SetModelMovement(self.Make('Movement','wheeled'))
    return out
  
  # C4I units
  def CreateUnitBdeHHC(self, gname = '', gside = 'Blue'):
    out = sandbox_entity.sandbox_entity(gname,'Coy','HQ')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','BdeHHC'))
    out.SetModelCombat(self.Make('Combat','Staff'))
    out.SetModelLogistics(self.Make('Logistics','BdeHHC'))
    out.SetModelMovement(self.Make('Movement','wheeled'))
    return out
  
  # Support Units
  def CreateUnitFSB(self, gname = '', gside = 'Blue'):
    # Forward Support Company
    out = sandbox_entity.sandbox_entity(gname,'Bn','CSS')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','FSB'))
    out.SetModelCombat(self.Make('Combat','Staff'))
    out.SetModelLogistics(self.Make('Logistics','FSB'))
    out.SetModelMovement(self.Make('Movement','wheeled'))
    return out
  
  def CreateUnitConvoy(self, gname = '', gside = 'Blue'):
    ''' Create a generic convoy for supply.'''
    out = sandbox_entity.sandbox_entity(gname,'Sec','convoy')
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','convoy'))
    out.SetModelCombat(self.Make('Combat','Staff'))
    out.SetModelLogistics(self.Make('Logistics','convoy'))
    out.SetModelMovement(self.Make('Movement','wheeled'))
    
    return out
  
  def CreateUnitLOGPAC(self, gname = '', gside = 'Blue'):
    ''' Create a LOGPAC, unmanned. '''
    out = sandbox_entity.sandbox_entity('LOGPAC','installation',"LOGPAC")
    out['side'] = gside
    out.SetModelC4I(self.Make('C3','Default'))
    out.SetModelIntelligence(self.Make('Intelligence','LOGPAC'))
    out.SetModelCombat(self.Make('Combat','LOGPAC'))
    out.SetModelLogistics(self.Make('Logistics','LOGPAC'))
    out.SetModelMovement(self.Make('Movement','LOGPAC'))
    return out
  
  # Unit formation #############################################
  def CreateFormation155SPBn(self, echelon = '110 FA', gside = 'Blue'):
    out = []
    hq = self.CreateUnitBdeHHC(gname='HQ %s'%(echelon),gside = gside)
    hq['C3']['echelon'] = echelon
    out.append(hq)
    # 2 Mech Bn Bn
    for i in ['1-','2-','3-']:
      temp = self.CreateUnit155SPBty(gname='%s%s'%(i,echelon),gside = gside)
      temp.ReportToHQ(hq)
      out.append(temp)
    return out
    
  def CreateFormationHMechBde(self, echelon = '1 Bde', gside = 'Blue'):
    out = []
    # HQ
    hq = self.CreateUnitBdeHHC(gname='HHC',gside = gside)
    hq['C3']['echelon'] = echelon
    out.append(hq)
    # 2 Mech Bn Bn
    for i in ['1/','2/']:
      temp = self.CreateUnitMechBn(gname='%s%s'%(i,echelon),gside = gside)
      temp.ReportToHQ(hq)
      out.append(temp)
      
    # recon Squadron
    temp = self.CreateUnitRecceTroop(gname = 'RS/%s'%(echelon),gside = gside)
    temp.ReportToHQ(hq)
    out.append(temp)
      
    # 1 Armor
    temp = self.CreateUnitArmorBn(gname='3/%s'%(echelon),gside = gside)
    temp.ReportToHQ(hq)
    out.append(temp)
    
    return out
  
  def CreateFormationTwoUnits(self, echelon = '1 Bde', gside = 'Blue'):
    out = []
    # HQ
    hq = self.CreateUnitBdeHHC(gname='HHC',gside = gside)
    hq['C3']['echelon'] = echelon
    out.append(hq)
    # 2 Mech Bn Bn
    for i in ['2Bn']:
      temp = self.CreateUnitMechBn(gname='%s'%(i),gside = gside)
      temp.ReportToHQ(hq)
      out.append(temp)
      
    
    return out
    