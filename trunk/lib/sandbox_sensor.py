'''
   The sensor class. The sensor's task is to Acquire, classify and report 
   on units that are in the sensor's Area of Interest.
'''
from copy import copy
from random import random, choice

import sandbox_geometry
import sandbox_position

from sandbox_keywords import dch_size_denomination
from vector import vect_5D

class sandbox_sensor:
    def __init__(self, AoI = None):
        # The Area of Interest (Empty AoI)
        if not AoI:
            self.AoI = sandbox_geometry.base_polygon()
        else:
            self.AoI = AoI
            
    def GetAoI(self):
        return self.AoI
    
    def Acquire(self, E, cnt):
        '''
           determine whether the detection is made and adjust the p_right on the 
           current contact.
        '''
        cnt.timestamp = copy(E['agent'].clock)
    
    def Classify(self, E, cnt):
        '''
           Fill in the data information for the contact
        '''
        for i in dir(self):
            if i.find('Specify') == 0:
                fn = getattr(self, i)
                fn(E,cnt)
    
    def Report(self, E):
        '''
           Returns the contact list defined by the sensor.
        '''
        return []
    
    # Private methods.

    # New interface
    def Requires(self):
        return self.requires
    
    def DegradedBy(self):
        return self.degraded_by
    
    def EnhancedBy(self):
        return self.enhanced_by
    
    def ClassifyProb(self, infoitem):
        '''Returns the probability of classifying an item by this sensor.'''
        return 'neutral'
    
class SensorVisual(sandbox_sensor):
    def __init__(self, NAI=None, direct = True):
        # Create a radius area centered 
        # If NAI is None, it will force the sensor to fetch its AoI at every acquisition (unit's visual)
        # Otherwise, it is a real NAI and has a fixed AoI
        self.AoI = NAI
        self.direct = direct
        
    
    
    def Acquire(self, E, cnt, force_detect = False):
        # Make sure that the polygon really is te unit's footprint
        if self.direct:
            self.AoI = E.Footprint()
            
        sandbox_sensor.Acquire(self,E,cnt)
        A = E['agent']
        pvalue = self.GetPValue(E,cnt)
        # Attempt to shake hand with friends (returns otherwise)
        if self.CanShakeHand(E, cnt): 
            self.ShakeHand(E,cnt)
            # Do not perform the rest
            return
            
        if random() <= pvalue or force_detect:
            cnt.p_right = min(1.0 ,cnt.p_right + (pvalue/12.0))
            cnt.UpdateField('nature', 'direct')
            self.Classify(E, cnt)
            A.ContactUpdate(cnt)
        else:
            cnt.p_right = max(0.0 ,cnt.p_right - (pvalue/12.0))
            # Lose only if visual contact in the first place
            if cnt.Type() == 'direct':
                A.ContactLose(cnt.unit, 'observation interupted')
            # Keep track of new contacts
            if cnt.Type() == 'new':
                cnt.timestamp = copy(A.clock)
                cnt.UpdateField('nature', 'undetected')
                # Add to contact list
                A.ContactUpdate(cnt) 
        
    
    
            
    
    # #################################
    # Private
    def GetPValue(self, E, cnt):
        '''
           Visual detection routine.
           Influenced by E.C2Level() --> ability to deal with internal information
           cnt.unit.signature() --> The profile of the unit to document
           0.75* pright*0.5 F(1.0) -> 1.25, F(0)= 0.75 F(0.5) = 1.0
        '''
        # The acquisition is automatic if the footprints overlap
        p_detect = 0.0
        if self.AoI.Overlaps(cnt.unit.Footprint()):
            p_detect = E.C2Level() * cnt.unit.Signature() * (0.75 + cnt.p_right*0.5)
            # Remove me this isn't the right place
            if cnt.IFF() == 'ENY' and cnt.IsDirectObs():
                E['agent'].potentialengagements.append(cnt.unit)
        else:
            # Non- automatic detection withing the visibility range away from the footprint
            visible = copy(self.AoI)
            visible.Extend(E.sim.Visibility(E.Position()))
            if visible.Overlaps(cnt.unit.Footprint()):
                # Get a p_detect (signature adjusted by p_right)
                p_detect = (E.C2Level()**2) * cnt.unit.Signature() * (0.75 + cnt.p_right*0.5)
                
        # Target coverage consideration
        # TODO coverage vectors
        if p_detect:
            terrain = E['agent'].map.SampleTerrain(E.Footprint())
            tv = E['movement'].friction_dict()
            sum = 0.0
            for i in terrain:
                sum += tv[i] * terrain[i]
            sum = max(0.20, sum)
            p_detect *= sum
            
        return p_detect
            

        
    # Private
        
    def CanShakeHand(self, E, cnt):
        '''
           Determine if two units can shake hands
        '''
        # classified as friendly
        if cnt.IFF() != 'FR':
            return False 
        
        # In footprint overlap
        if not E.Footprint().Overlaps(cnt.unit.Footprint()):
            return False
        
        # Can communicate with via COC
        if random() > E.CommLevelTo(cnt.unit):
            return False
        
        # Hand shake is possible
        return True
    
    def ShakeHand(self, E, cnt):
        '''
           Exchange states between units
        '''
        # Get info from other
        cnt.Merge(cnt.unit['agent'].ContactDefineSelf())
        E['agent'].ContactUpdate(cnt)
        # Transfer self to cnt
        ocnt = cnt.unit.Contact(E)
        # If the contact doesn't exists
        if ocnt == None:
          ocnt = sandbox_contact(E)
        ocnt.Merge(E['agent'].ContactDefineSelf())
        cnt.unit['agent'].ContactUpdate(ocnt)
        
    # #################################
    # Classify
    def SpecifyIntelRating(self, E, cnt):
        '''
           According to STANAG.
        '''
        # STANAG 2022 classification of the intelligence
        cnt.UpdateField('evaluation rating', 'A%s'%(cnt.STANAG2022(cnt.p_right)))
    
    def SpecifyHardware(self, E, cnt):
        '''
           Set the symbol to the right one.
        '''
        cnt.UpdateField('symbol', cnt.unit['icon'])
        cnt.UpdateField('hardware', cnt.unit['TOE'])
        
    def SpecifySizeIndicator(self, E, cnt):
        '''
           Implement a lie on a random roll.
        '''
        if random() <= cnt.p_right:
            # Rectify incorrect knowledge
            if cnt.fields['size indicator'] != cnt.unit['size']:
              cnt.UpdateField('size indicator', cnt.unit['size'])
        elif random() <= (1.0-cnt.p_right) or cnt.fields['size indicator'] == '':
            # Lie about it
            newindex = dch_size_denomination.index(cnt.unit['size']) + choice([-1,1])
            newindex = min(newindex,len(dch_size_denomination)-1)
            newindex = max(newindex,0)
            cnt.UpdateField('size indicator', dch_size_denomination[newindex])
    
    def SpecifySide(self, E, cnt):
        cnt.UpdateField('side', cnt.unit['side'])
    def SpecifyIFF(self, E, cnt):
        cnt.UpdateField('IFF/SIF', E['agent'].SolveIFF(cnt.unit['side']))
    def SpecifyLocation(self, E, cnt):
        # Classify location
        if random() <= cnt.p_right:
          # Level of precision
          cnt.location = copy(cnt.unit['position'])
          cnt.location.footprint = copy(cnt.location.footprint) # in case of shallow copying.
          cnt.UpdateField('location', E['agent'].map.MGRS.AsString(cnt.location))
        elif random() <= 1.0 - cnt.p_right:
          # randomize location within footprint
          cnt.location = sandbox_position.position_descriptor(cnt.unit.Footprint().RandomPointInside())
          cnt.UpdateField('location', E['agent'].map.MGRS.AsString(cnt.location))
        else:
          # randomize location within 0.25 - 1.25 footprint
          temp = copy(cnt.unit.Footprint())
          temp.Scale(1.25)
          blank = copy(cnt.unit.Footprint())
          blank.Scale(0.25)
          cnt.location = temp.RandomPointInside()
          while blank.PointInside(cnt.location):
            cnt.location = temp.RandomPointInside()
          cnt.location = sandbox_position.position_descriptor(cnt.location)
          cnt.UpdateField('location', E['agent'].map.MGRS.AsString(cnt.location))
          
        # default footprint
        if not cnt.location.footprint:
            cnt.location.footprint = sandbox_geometry.circle(cnt.location, 1.0)
          
    def SpecifyMobility(self, E, cnt):
        # Classify intentions and activities.
        if random() <= cnt.p_right:
          cnt.UpdateField('mobility', cnt.unit.GetStance())
        elif random() <= 1.0 - cnt.p_right:
          # Lie about stance (FIXME)
          cnt.UpdateField('mobility', 'deliberate defense')
    def SpecifyCombatEffectiveness(self, E, cnt):
        # Classify Combat effectiveness
        if random() <= cnt.p_right:
          cnt.UpdateField('combat effectiveness', cnt.unit['combat']['RCP'])
        elif random() <= 1.0 - cnt.p_right:
          # Lie about stance (FIXME)
          cnt.UpdateField('combat effectiveness', cnt.unit['combat']['RCP'] * 1.0 + ((random()*2.0)-1.0))
    
    def RefineFootprint(self, E, cnt, level):
        '''! \brief Develop a footprint based on the previous one.
        '''
        pass
    
import unittest
from sandbox_data import sandbox_data_server

class SensorTest(unittest.TestCase):
    def setUp(self):
        self.database = sandbox_data_server()
        
    def testLoadVisualSensor(self):
        x = self.database.GetInstance('sensor', 'visual')
        self.assertTrue(bool(x))
    
    def testLoadLowLightSensor(self):
        x = self.database.GetInstance('sensor', 'low-light')
        self.assertTrue(not 'light' in x.Requires())
    
    def testGetRequiredVisual(self):
        x = self.database.GetInstance('sensor', 'visual')
        self.assertEqual(['LOS','light'],x.Requires())
    
    def testGetDegradedLowLight(self):
        x = self.database.GetInstance('sensor', 'low-light')
        self.assertTrue('light' in x.DegradedBy())
    
    def testGetEnhancedThermal(self):
        x = self.database.GetInstance('sensor', 'thermal')
        self.assertTrue('cold_temperature' in x.EnhancedBy())
        
    def testClassifyProb(self):
        x = self.database.GetInstance('sensor', 'ear')
        self.assertEqual('very unlikely', x.ClassifyProb('location'))
    