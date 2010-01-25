'''
    Abstract how supply is handled and implement most mathematical operator for the task.
'''
from copy import copy
import Renderer_html as html

import system_base

class supply_package(dict):
  units_conversion = {'':1.0, 'STON':1.0, 'kg':0.00110231131, 'lb':0.0005, 'lt':0.00110231131, 'gal':0.0041727022181012319}
  time_units_conversion = {'':1.0, 'hrs':1.0, 'mins':60.0, 'day':24**-1}
  def __init__(self, generic = 0.0):
    '''
       Can be initialized with a quantity of generic suppply points.
       Express everything in Short Tons and all rates in Short tons per hour.
    '''
    if generic:
      self['Unspecified'] = generic
  
  def toXML(self, doc, name):
    '''! \brief add itself to a node of the type LOGPAC. This node must be prenamed.
    '''
    # node skeleton
    out = doc.NewNode(name, 'LOGPAC')
    for i in self.keys():
      doc.NewField(i, str(self[i], out))
    return out
  
  def fromXML(self, doc, node):
    '''! \brief Build logistic package from a XML node.
    '''
    # safety check
    if doc.Get(node, 'type') != 'LOGPAC':
      return False
    
    # Read in units
    units = supply_package.units_conversion[doc.Get(node, 'units')]
    
    # Read in rate
    ratetime = supply_package.time_units_conversion[doc.Get(node, 'time_units')]
    
    # Read goods in
    for i in doc.ElementAsList(node):
      name = doc.Get(i,'name')
      u = doc.Get(i, 'units')
      if u:
        u = supply_package.units_conversion[u]
      else:
        u = units
      rt = doc.Get(i, 'time_units')
      if rt:
        rt = supply_package.time_units_conversion[rt]
      else:
        rt = ratetime
        
      self[name] = doc.Get(i) * u * rt
    return True
    
  def __str__(self):
    out = ''
    mk = self.keys()
    mk.sort()
    for i in mk:
      out = out + '%s: %.3f STON\n'%(i,self[i])
    return out
  
  def HasNoDeficit(self):
    ''' True if no values are below 0'''
    # Avoid to count deficit of less than 0.1 lb as deficits
    if min(self.values()) < 0.0 and abs(min(self.values())) >= 0.0001:
      return False
    return True
  
  def Allocate(self, endclass, val):
    '''
       INPUT : 
              endclass -- the class to allocate to
              val      -- the quantity to allocate
       OUTPUT:
              The value that could be converted (<= val)
    '''
    # label of generic class
    GC = self.__GenericClass(endclass)
    # Attempt upgrade
    if GC:
      if self.has_key(GC):
        # The key exist are there any material in it?
        transaction = max(0,min(val,self[GC]))
        self[GC] = self[GC] - transaction
        self[endclass] = self[endclass] + transaction
        return transaction
      else:
        # Attempt to seek Unspecified
        temp = self.Allocate(GC, val)
        # Rerun now that we have the GC class in store
        if temp:
          return self.Allocate(endclass, val)
        else:
          return temp
    else:
      # Failed attempt to Get above Unspecified
      return 0.0
        
  def IgnoreDeficit(self):
    ''' Set deficit to 0.0 and return a package with only the dificit items'''
    out = supply_package()
    for i in self.keys():
      if self[i] < 0.0:
        out[i] = self[i]
        self[i] = 0.0
    return out
  
  def ConvertGeneric(self):
    '''
        For each item that is negative, draw from more generic classes
        III(bulk) --> III
        III       --> Generic
    '''
    for i in self.keys():
      if self[i] < 0.0:
        self.UseGenericClasses(i,abs(self[i]))
            
  def UseGenericClasses(self, spec_class, val):
    # Convert general to spec_class up to val
    GC = self.__GenericClass(spec_class)
    if self.has_key(GC):
      if val <= self[GC]:
        self[GC] = self[GC] - val
        if self.has_key(spec_class):
          self[spec_class] = val + self[spec_class]
        else:
          self[spec_class] = val
      else:
        self.UseGenericClasses(GC,val - self[GC])
        if self.has_key(spec_class):
          self[spec_class] = self[GC] + self[spec_class]
        else:
          self[spec_class] = self[GC]

          
  def __GenericClass(self,  K):
    if K.find('(') != -1:
      return K[:K.find('(')]
    elif K == 'Unspecified':
      return ''
    else:
      return 'Unspecified'
    
  def ClearKeys(self):
    for i in self.keys():
      if self[i] == 0.0:
        del self[i]
        
  def __add__(self, other):
    '''
       Add each components
    '''
    out = supply_package()
    for i in other.keys():
      if self.has_key(i):
        out[i] = self[i] + other[i]
      else:
        # Can we upgrade more generic
        out[i] = other[i]
        
    for i in self.keys():
      if not i in other.keys():
        out[i] = self[i]
    
    return out
  

  def __mul__(self, other):
    ''' Assume a value of 1 for missing data, ignore unknown keys and generic classes reintantiations'''
    out = supply_package()
    if type(other) == type(self):
      for i in self.keys():
        try:
          out[i] = self[i] * other[i]
        except:
          out[i] = self[i]
    else:
      for i in self.keys():
        out[i] = self[i] * other
        
    return out
    
  
  def __div__(self, other):
    ''' Allows only scalar operation or pairwise ONLY for item with common keys'''
    out = supply_package()
    if type(other) == type(self):
      for i in self.keys():
        try:
          out[i] = self[i] / float(other[i])
        except:
          pass
    else:
      for i in self.keys():
        out[i] = self[i] / float(other)
    return out
  
  def __sub__(self, other):
    ''' Attempt to upgrade generic classes '''
    out = self*1.0
    
    for i in other.keys():
      # Add the key if missing
      if not out.has_key(i):
        out[i] = 0.0
      # If the other[i] is negative, just add the values!
      if other[i] <= 0.0:
        out[i] = out[i] - other[i]
        continue
      
      if out.has_key(i):
        # the raw difference 
        if out[i] >= other[i]:
          out[i] = out[i] - other[i]
        else:
          out.Allocate(i,other[i]-out[i])
          # We did all that we could here, just do the deed...
          out[i] = out[i] - other[i]
      else:
        out[i] = -other[i]
    
    return out
    

  def __float__(self):
    return float(sum(self.values()))
    




#
# Data
#
lb2STON = 2000**-1
gal2STON = 3.7854 * 2.2 * lb2STON

class data_consumption(dict):
    '''! A dictionary of consumption vectors organized in a herachical manner
    '''
    def __init__(self):
        self.BuildVectors()
        self.possibleHardware = ['personel', 'armor', 'mech', 'motor', 'MLRS', '155SP']
        
    def GetData(self, TOE,  task ,hardware = 'vehicle'):
        '''! \find key and return value
        '''
        key = '%s::%s::%s'%(task, hardware , TOE)
        
        if key in self:
            return self[key]
        elif '%s::%s::%s'%(task, hardware , 'mech') in self:
            return self['%s::%s::%s'%(task, hardware , 'mech')]
        
        return self['idle::vehicle::mech']
    
    def BuildVectors(self):
        '''! \brief this is where Umpires can add stuff if they want to.
        '''
        # Idle consumption of personel ST101-6 2007 data
        a = supply_package()
        a['I'] =  5.25 * lb2STON
        a['II'] = 1.9 * lb2STON
        a['III(p)'] = 0.51 * lb2STON
        a['IV'] = 9.01 * lb2STON
        a['V'] = 1.0 *lb2STON ## Nominal consumption, practice, I wing this one.
        a['VI'] = 2.06 * lb2STON
        a['water'] = 6.1 * gal2STON
        a = a * 24**-1 # Hourly rate
        
        self['idle::personel::personel'] = a 
        
        # Combat, ligh infantry, assume 1 day ~60 minutes fighting.
        a = supply_package()
        a['V'] = 7.78 * lb2STON
        a['VIII'] = 1.0 *lb2STON ## Added from G1-G4 (1996) ~ 1 lb per hour medical supply
        a['XI'] = 2.5 * lb2STON ## Same source, daily * 24 hours in relacement parts.
        self['combat::personel::personel'] = a
        
        # Idle APC and light armored v.
        a = supply_package()
        a['III'] = 1.4 * gal2STON
        a['IX'] = 100.0 * 0.045 * 24**-1 * lb2STON # assume a 100lb spare part
        a['VII'] = 35.0 * 0.005 *  24.**-1 # 35 ton
        
        self['idle::vehicle::mech'] = a
        
        self['transit::vehicle::mech'] = a * 4.0
        
        self['off-road::vehicle::mech'] = a * 8.0
        
        # MBT
        a = supply_package()
        a['III'] = 17.3 * gal2STON
        a['IX'] = 100.0 * 0.045 * 24**-1 * lb2STON # assume a 100lb spare part
        a['VII'] = 55.0 * 0.005 *  24.**-1 # 35 ton
        
        self['idle::vehicle::armor'] = a
        
        self['transit::vehicle::armor'] = a * 2.0
        
        self['off-road::vehicle::armor'] = a * 3.0        
        
        # Idle trucks
        a = supply_package()
        a['III'] = 1.4 * gal2STON
        a['IX'] = 30.0 * 0.045 * 24**-1 * lb2STON # assume a 30lb spare part
        a['VII'] = 10.0 * 0.005 *  24.**-1 # 35 ton
        
        self['idle::vehicle::motor'] = a
        
        self['transit::vehicle::motor'] = a * 4.0
        
        self['off-road::vehicle::motor'] = a * 8.0
    
        # Combat
        a = self['off-road::vehicle::armor'] * 1.0
        # 184 M-1 in a Bn spending 34.2 STON daily (1h intense)
        a['V'] = 0.18
        self['combat::vehicle::armor'] = a
        
        a = self['off-road::vehicle::mech'] * 1.0
        # 184 M-2 in a Bn spending 22.6 STON daily (1h intense)
        a['V'] = 0.12
        self['combat::vehicle::mech'] = a
        
        a = self['off-road::vehicle::mech'] * 1.0
        # 9 M109 in a Bn spending 69.6 STON daily (3h intense) -- Ouch!
        a['V'] = 2.57
        self['combat::vehicle::155SP'] = a
        
        a = self['off-road::vehicle::mech'] * 1.0
        # 9 MLRS in a Bn spending 900 STON daily (3h intense) -- Ouch!
        a['V'] = 33.0
        self['combat::vehicle::MLRS'] = a





class data_transportation(dict):
  def __init__(self):
    self.Build()
    
  def Build(self):
    # Light Truck Co
    self['Lt-Med'] = supply_package(220.0)
    self['Lt-Med, semi'] = supply_package(260.0)
    
    self['Med'] = supply_package(360.0)
    self['Med, Ammo'] = supply_package()
    self['Med, Ammo']['V'] = 660.0
    self['Med, 3K SMFT'] = supply_package()
    self['Med, 4K SMFT'] = supply_package()
    self['Med, 3K SMFT']['water'] = 155000. * gal2STON
    self['Med, 4K SMFT']['water'] = 250000. * gal2STON
    self['Med, PLS'] = supply_package(570.0)
    self['Med, PLS, Ammo'] = supply_package()
    self['Med, PLS, Ammo']['V'] = 1150.0
    
    self['POL, 7.5K'] = supply_package()
    self['POL, 7.5K']['III(b)'] = 370000 *gal2STON
    
    self['HET'] = supply_package(1700.0)
    
    
  
class system_logistics(system_base.system_base):
  def __init__(self):
    system_base.system_base.__init__(self)
    
    # Capacities 
    self['capacity'] = supply_package()
    self['passenger_lift'] = 0
    self['crew_size'] = 0

    # Expressed in 
    self['basic load'] = {'idle': 3*24., 'transit': 6.0, 'combat': 1.0, 'service':0.0}
    
    # consumption data
    self['consumption_rate'] = {'idle':supply_package(), 'transit':supply_package(), 'combat':supply_package(), 'service':supply_package()}

  #
  # Interface
  def fromXML(self, doc, node):
    '''! \brief Populate instance from XML node.
    ''' 
    # Passenger lift
    lift = doc.Get(node, 'passenger_lift')
    if lift != '':
      self['passenger_lift'] = lift
      
    # Crew
    lift = doc.Get(node, 'crew')
    if lift != '':
      self['crew_size'] = lift
    
    # Basic Load
    bl = doc.Get(node, 'basicload')
    if bl:
      d = doc.ElementsAsDict(bl)
      if d:
        self['basic load'].update(d)
        
    # consumption vectors
    cons = doc.Get(node, 'consumption_rate')
    if cons:
      for i in ['idle','transit','combat','service']:
        nd = doc.SafeGet(cons, i, supply_package())
        self['consumption_rate'][i] = nd
        

    # Capacity
    cap = doc.Get(node, 'capacity')
    if cap:
      self['capacity'] = cap
    else:
      # Capacity not defined, lets set it to a basic load
      self['capacity'] = self.ProjectSupply(activity_dict=self['basic load'])
  
  # Initialization
  # Manips
  #
  def StripLOGPACs(self, LOGPACs):
      '''
         Get the supply out of all LOGPACs 
         INPUT : LOGPACs [list]
      '''
      out = supply_package()
      for i in LOGPACs:
        out = out + i['logistics']['cargo']
      return out
  #
  # Report and information
  def GetCapacity(self, E=None):
    '''! \brief returns the cargo capacity of a unit 
    '''
    # Base capacity of the model
    out = self['capacity']
  
    
    if not E:
      return out
    
    # Vehicles
    for i in E.vehicle:
      cnt = E.vehicle[i].GetCount()
      vh  = E.vehicle[i].GetKit()
      out = out + (vh.logistics.GetCapacity() * cnt)
      
    # Personel
    for i in E.personel:
      cnt = E.personel[i].GetCount()
      vh  = E.personel[i].GetKit()
      out = out + (vh.logistics.GetCapacity() * cnt)
      
    return out
  
  
  def Report(self, E):
    '''
       Logistics report for entity E
    '''
    cargo = E.GetCargo()
    capacity = E.GetCapacity()
    
    out = html.Tag('b','Inventory:')
    out = out + ' %.2f STON (%.2f%% store)'%(float(cargo), 100.0 * float(cargo)/float(capacity))
    mylist = ''
    for i in ['Unspecified','I','II','III','IV','V','VI','VII','VIII','IX','X','water']:
      for j in cargo.keys():
        if j == i or j.find('%s('%(i)) == 0:
          mylist = mylist + html.Tag('li','%s : %.2f STON'%(j,cargo[j]))
    out = out + html.Tag('ol',mylist)
    return html.Tag('div',out)
   
  def ValidateRequest(self, commodity, overhead = supply_package(), E=None):
    ''' Returns up the the capacity if the current stock.
        Returns a negative 
    '''
    # Remove overhead from the cargo
    cargo = E.GetCargo()
    temp = cargo - overhead
    
    # Remove the commodity from what is left 
    out = temp - commodity
    
    # Remove deficits
    if not out.HasNoDeficit():
      # remove all deficit from commodity
      for i in out.keys():
        if out[i] < 0.0 and commodity.has_key(i):
          commodity[i] = commodity[i] + out[i]
          
    # consider available freight minus the overhead
    freight_lift = E.GetCapacity() - cargo
    mod = max(0.0,min(1.0, (float(freight_lift)-float(overhead))/float(commodity)))
    return commodity * mod
          
  
  # Transactions
  #
  def LoadFreight(self, package):
    '''! \brief Load a package as freight. It can't be used for local consumption.
         \param freight package (\c supply_package)
         \return True/False whether this is done or not.
         \todo Check for mass, bulk, capacity.
    '''
    self['freight package'] = package
    return True
    
  def UnloadFreight(self):
    '''! \brief Unload the freight 
         \return supply_package
    '''
    temp = self['freight package']
    del self['freight package']
    self['freight'] += temp
    return temp
    
     
    
  # Computation of expenses - Interface
  def _GetConsumptionRate(self, activity):
    '''Returns the consumption rate or an empty supply object'''
    return self['consumption_rate'].get(activity,supply_package())
  def SupplyExpenditure(self, N=1, activity_code = ['idle'], deltatime = 1.0/6, E=None):
    '''
       Compute the Expenditure of supply for this logistic model provided a multiplier of N,
       for a list of activity_code (list of strings), for a deltatime (in hours) 
       If a pointer to an entity E is provided, the function will recurse into the logistics models 
       of each personel and vehicle in the TOE of this entity.
    '''
    # The output
    out = supply_package()
    
    # The children, possibly
    if E:
      # personel
      for i in E.personel.keys():
        x = E.personel[i]
        out = out + x.GetKit().logistics.SupplyExpenditure(x.GetCount(), activity_code, deltatime)
      # Vehicle
      for i in E.vehicle.keys():
        x = E.vehicle[i]
        out = out + x.GetKit().logistics.SupplyExpenditure(x.GetCount(), activity_code, deltatime)
    
    # The model itself
    for act in activity_code:
      if act in self['consumption_rate']:
        out = out + (self._GetConsumptionRate(act) * N * deltatime)
        
    return out
       

  def ProjectSupply(self, N=1, activity_dict = {}, E=None):
    '''!
        Compute supply, but by providing a dictionary of activity and their time allowance.
        Useful for planning of computing supply in a timespan of uneven activities.
    '''
    out = supply_package()
    for i in activity_dict.keys():
      # Pass each activity separately, with its time allowance
      out = out + self.SupplyExpenditure(N,[i], activity_dict[i], E)
    
    return out
  

  def DailySupply(self, E):
    '''! \brief Returns an average 24 h of supply based on the definition of the daily load.
    
         This is a convenient method for planning.
    '''
    if 'idle' in self['basic load']:
      mod = 24.0 / self['basic load']['idle']
      return self.ProjectSupply(1, self['basic load'], E) * mod
    return supply_package()
  def GetBasicLoad(self, E):
    ''' Returns the basic load of Entity E
    '''
    return self.ProjectSupply(activity_dict=self['basic load'], E=E)
  #
  # Umpire interface
  def ComputeCapacity(self):
    '''
       Adjust the capacity to a store large enough for a given timespan (in hours).
    '''
    self['capacity'] = self.ProjectSupply(self['basic load'],self['initRCP'])
    
  
class system_logistics_CSS(system_logistics):
  def __init__(self):
    system_logistics.__init__(self)
    self['IsCSS'] = True
    
  # Analysis
  def ProjectSupply(self, code_ratios, base_RCP, unit_list=[]):
    '''! Agglomerate of total supply needed by a logistic unit
    '''
    return self.ProjectRessuply(unit_list) + system_logistics.ProjectSupply(self, code_ratios, base_RCP)
  
  def ProjectRessuply(self, unit_list):
    '''
       Compute a projected daily ressuply burden for all units in the unit_list.
    '''
    out = supply_package()
    
    for i in unit_list:
      out = out + i['logistics'].DailySupply(i)
      
    return out
  
  def ComputeRessuplyBurden(self, unit_list):
    '''!
       Evaluate the STON/hr ratio.
    '''
    burden = 0.0
    for i in unit_list:
      if i['TOE'] == 'convoy' or i['TOE'] == 'LOGPAC':
        continue
      dailyload = i['logistics'].DailySupply(i)
      transittime = i['agent'].EstimateConvoyTransitTime() * 2.0
      burden = burden + (float(dailyload)*transittime)
  
    myfreigth = float(self['max_freight'] * 24.0)
    return burden/myfreigth
    
  
  # Umpire tool
  def ComputeFreight(self, unit_list):
    '''!
       Compute the burden with the current freight, then adjust the freight so the burden
       is 1/target_overhead for all supported unit within 32 km (max local hauls).
    '''
    burden = self.ProjectSupply(self['basic load'], self['initRCP'], unit_list)
    
    # this burden will be distributed over 2 shifts of local haul
    burden = burden * 0.5
    
    # Maintenance levels of 75%
    burden = burden * 1.333
    
    # set internal values.
    self['freight'] = burden
    self['max_freight'] = burden * 1.0
    self['cargo'] = burden * 3.0
    self['capacity'] = self['cargo'] * 1.0
      


# Debug
if __name__ == '__main__':
  
  my = system_logistics()
  I = my.Consumptionidle('armor', 13*14, 900, 'temperate', 'Bde')
  T = my.Consumptiontransit('armor', 13*14)
  C = my.Consumptioncombat('armor', 13*14)
  
  print (I + T * 0.5 + C * 0.25) * 3.25
  


