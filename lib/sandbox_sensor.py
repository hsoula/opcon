'''
   The sensor class. The sensor's task is to Acquire, classify and report 
   on units that are in the sensor's Area of Interest.
'''
import os
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
            
        # Name
        self.name = ''
        
        # Range
        self.max_range = 0.0
        
        # Signature target
        self.signal = ''
            
        # Requirements
        self.requires = []
        self.degraded_by = []
        self.enhanced_by = []
        
        # Classification filters
        self.classification_filter = {}
            


    def __str__(self):
        return 'Sensor: %s (%s)'%(self.name, self.signal)
    def fromXML(self, doc, node):
        ''' Read basic data from the node.
        '''
        # Name
        self.name = doc.SafeGet(node, 'name', self.name)
        # Target Signal
        self.signal = doc.SafeGet(node, 'signature', self.signal)
        
        # Range
        self.max_range = doc.SafeGet(node, 'range', self.max_range)
        
        # Read requirements
        for nd in doc.Get(node, 'requires', True):
            self.requires.append(nd)
            
        # Read degradation
        for nd in doc.Get(node, 'degraded_by', True):
            self.degraded_by.append(nd)
            
        # Read enhancement
        for nd in doc.Get(node, 'enhanced_by', True):
            self.enhanced_by.append(nd)
            
        # Negation Section
        # Read requirements
        for nd in doc.Get(node, 'requires_not', True):
            if nd in self.requires:
                self.requires.remove(nd)
            
        # Read degradation
        for nd in doc.Get(node, 'degraded_by_not', True):
            if nd in self.degraded_by:
                self.degraded_by.remove(nd)
            
        # Read enhancement
        for nd in doc.Get(node, 'enhanced_by_not', True):
            if nd in self.enhanced_by:
                self.enhanced_by.remove(nd)
            
        # Classify node
        cls = doc.Get(node, 'classify')
        if cls != '':
            for nd in doc.ElementAsList(cls):
                k = nd.tagName.replace('_',' ')
                x = doc.Get(nd).split(',')
                for i in x:
                    i = i.strip()
                    i = i.replace(' ', '_')
                    self.classification_filter[i] = k.strip()
    
    def GetAoI(self):
        return self.AoI
    
    def Acquire(self, E, cnt):
        '''
           determine whether the detection is made and adjust the p_right on the 
           current contact.
        '''
        cnt.timestamp = copy(E['agent'].clock)
    

    

    # Get Data from sensor
    def ClassificationFields(self):
        ''' returns a list of classification fields'''
        return self.classification_filter.keys()
    
    def Requires(self):
        return self.requires
    
    def DegradedBy(self):
        return self.degraded_by
    
    def EnhancedBy(self):
        return self.enhanced_by
    
    def ClassifyProb(self, infoitem):
        '''Returns the probability of classifying an item by this sensor.'''
        return self.classification_filter.get(infoitem, 'impossible')
    
   
import unittest

class SensorTest(unittest.TestCase):
    def setUp(self):
        import sandbox_data
        self.database = sandbox_data.sandbox_data_server()
        
    def testLoadVisualSensor(self):
        x = self.database.Get('sensor', 'visual')
        self.assertTrue(bool(x))
    
    def testLoadLowLightSensor(self):
        x = self.database.Get('sensor', 'low-light')
        self.assertTrue(not 'light' in x.Requires())
    
    def testGetRequiredVisual(self):
        x = self.database.Get('sensor', 'visual')
        self.assertEqual(['LOS','light'],x.Requires())
    
    def testGetDegradedLowLight(self):
        x = self.database.Get('sensor', 'low-light')
        self.assertTrue('light' in x.DegradedBy())
    
    def testGetEnhancedThermal(self):
        x = self.database.Get('sensor', 'thermal')
        self.assertTrue('cold_temperature' in x.EnhancedBy())
        
    def testClassifyProb(self):
        x = self.database.Get('sensor', 'ear')
        self.assertEqual('very unlikely', x.ClassifyProb('location'))
    

if __name__ == '__main__':
    # Change folder
    os.chdir('..')
    
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(SensorTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)