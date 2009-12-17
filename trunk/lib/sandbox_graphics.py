'''
    Operational Graphics module
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

from sandbox_geometry import *
from pickle import dumps, HIGHEST_PROTOCOL

class operational_graphic:
    '''! \brief A line as a sequence of points in the map.
    '''
    def __init__(self, type = '', name = ''):
        # Can be MSR, PL, etc...
        self.type = type
        
        # Name
        self.name = name
        
        # placeholder for control points
        self.shape = ''
        
        self.style = {}
        
        
    def __getattr___(self, attr):
        '''! \brief Attempts to pass on the calls to the shape instance
        '''
        if attr == '__setstate__':
            raise AttributeError, attr
        
        if hasattr(self.shape, attr):
            return getattr(self.shape, attr)
      
        # All else fail  
        raise AttributeError, attr
    
    def SetStyle(self, s):
        '''! \brief set manual override 
        '''
        del self.style
        
        self.style = s
        

    # Access Methods
    def Center(self):
        return None
    def Name(self):
        '''! \brief Assemble the name together.
        '''
        if self.type != 'DATUM':
            return "%s %s"%(self.type,self.name)
        return self.name
    
    def GetShape(self):
        '''! \brief Return the shape attribute to the class.
        '''
        return self.shape
    
    def BoundingBox(self):
        '''! \brief return the BoundingBox
             \return [minX, minY, maxX, maxY]
        '''
        try:
            return self.shape.BoundingBox()
        except:
            return [None, None, None, None]
    
    def PositionLabel(self):
        '''! \brief reference point for a label
        '''
        return None
    def DistanceToPoint(self, P):
        # Abstract Method to be overloaded, work for the point case
        try:
            return (P-self.shape).length()
        except:
            return -1.0
    
class operational_point(operational_graphic):
    '''! \brief Single points CP
    '''
    def __init__(self, type, name, vertex):
        operational_graphic.__init__(self, type, name)
        self.shape = vertex

    def BoundingBox(self):
        '''! \brief Overload the BBox
        '''
        return [self.shape.x,self.shape.y,self.shape.x,self.shape.y]
    def Center(self):
        return self.shape
class operational_line(operational_graphic):
    '''! \brief A sequence of points forming a line
    '''
    paths = ['MSR','ROUTE']
    def __init__(self, type, name, points):
        operational_graphic.__init__(self, type, name)
        self.shape = points
        
        self.style['LineWidth'] = 2
        self.style['LineStyle'] = 'Solid'
        self.style['LineColor'] = 'RED'
        
        if type in operational_line.paths:
            self.SubElements()
        
    def Center(self):
        out = vect_5D()
        for i in self.shape:
            out += i
        return out * (1.0/len(self.shape))
        
    def SubElements(self):
        '''! \brief Define waypoints and such
        '''
        self.waypoints = []
        
        self.waypoints.append(operational_point('AP', '', self.shape[0]))
        
        for i in self.shape[1:-1]:
            self.waypoints.append(operational_point('WP', '', i))
            
        self.waypoints.append(operational_point('RP', '', self.shape[-1]))

    def BoundingBox(self):
        '''! \brief Overload the BBox
        '''
        mnX = mnY =  1000000000
        mxX = mxY = -1000000000
        
        for i in self.shape:
            mnX = min(mnX, i.x)
            mxX = max(mxX, i.x)
            mnY = min(mnY, i.y)
            mxY = max(mxY, i.y)
            
        return [mnX,mnY,mxX,mxY]
    
class operational_area(operational_graphic):
    '''! \brief A wrapper for the polygon class
    '''
    def __init__(self, gtype, name, polygon):
        operational_graphic.__init__(self, gtype, name)
        
        if type(polygon) == type([]):
            polygon = base_polygon(polygon)
            
        self.shape = polygon
        
        self.style['LineWidth'] = 2
        self.style['LineStyle'] = 'Solid'
        self.style['LineColor'] = 'RED'
        self.style['FillStyle'] = None
        self.style['FillColor'] = None
    def Center(self):
        return self.shape.Centroid()
    def Overlaps(self, other):
        return self.shape.Overlaps(other)

    def PointInside(self, P):
        return self.shape.PointInside(P)
# Overlap
class operational_overlay:
    '''! \brief Contain all the necessary information to overlay to a map for the agent to 
         operate.
         
         An element is a control graphic, its name must be unique.
    '''
    def __init__(self, name = 'OVR-1'):
        #
        
        # Dictionary of control elements (by name)
        self._control = {}
        
        # Identifier
        self.name = name

        
    # Elements manips
    def ListElements(self):
        return self._control.keys()
    
    def ListPoints(self):
        out = []
        for i in self._control.keys():
            if self._control[i].__class__ == operational_point:
                out.append(i)
        return out
    
    def ListLines(self):
        out = []
        for i in self._control.keys():
            if self._control[i].__class__ == operational_line:
                out.append(i)
        return out
    
    def ListAreas(self):
        out = []
        for i in self._control.keys():
            if self._control[i].__class__ == operational_area:
                out.append(i)
        return out    
    
    def AddElement(self, ele):
        '''! \brief Add an element and make sure that the name is unique.
             \return sucess on adding the element.
        '''
        if not ele.Name() in self._control.keys():
            self._control[ele.Name()] = ele
            return True
        return False
    
    def GetElement(self, name):
        '''! \brief Access an element by its name.
        '''
        if self._control.has_key(name):
            return self._control[name]
        return None
    
    def GetElementByTag(self, tag):
        '''! \brief retireve all items with a given tag.
        '''
        out = []
        for i in self._control.keys():
            if i.find(tag) == 0:
                out.append(self.GetElement(i))
        return out
    
    def DeleteElement(self, name):
        '''! \brief Access by full name.
        '''
        if self.GetElement(name):
            del self._control[name]
            return True
        return False
        
    # Information
    def BoundingBox(self):
        '''! \brief Hint for the covered area of the map.
             \return [minx, miny, maxx, maxy]
        '''
        mnX = mnY = 1000000000
        mxX = mxY = -1000000000
        
        for i in self._control.values():
            bbox = i.BoundingBox()
            if bbox[0] != None:
                mnX = min(mnX, bbox[0])
                mnY = min(mnY, bbox[1])
                mxX = max(mxX, bbox[2])
                mxY = max(mxY, bbox[3])
        
        if mnX > mxX:
            return [None, None, None, None]
        return [mnX, mnY, mxX, mxY]
        
    # Meta
    def Pickle(self):
        return dumps(self, HIGHEST_PROTOCOL)
#
#
class GraphicsTest(unittest.TestCase):
    def testCreateOverlay(self):
        a = operational_overlay('A-101')
        box = a.BoundingBox()
        self.assertEqual(box[0], None)
        
    def testAddPoint(self):
        a = operational_overlay('A-101')
        #a.AddElement(operational_point('RP','JIMBO', vect_3D()))
        self.assertTrue(a.AddElement(operational_point('RP','JIMBO', vect_3D())))
    
    def testOverwritePoint(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_point('RP','JIMBO', vect_3D()))
        self.assertFalse(a.AddElement(operational_point('RP','JIMBO', vect_3D())))
        
    def testOverwriteOKPoint(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_point('RP','JIMBO', vect_3D()))
        self.assertEqual(True, a.AddElement(operational_point('RP','JIMBO1', vect_3D())))
        
    def testPointBoundingBox(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_point('RP','JIMBO', vect_3D()))
        self.assertEqual(a.BoundingBox()[0],0.0)
        
    def testlineBoundingBox(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_line('RP','JIMBO', [vect_3D(),vect_3D(1.,1.),vect_3D(0.,2.)]))
        box = a.BoundingBox()
        self.assertEqual(box, [0.0,0.0,1.0,2.0])
    def testDeleteElement(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_line('RP','JIMBO', [vect_3D(),vect_3D(1.,1.),vect_3D(0.,2.)]))
        self.assertEqual(True, a.DeleteElement('RP JIMBO'))
    def testDeleteElement1(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_line('PL','JIMBO', [vect_3D(),vect_3D(1.,1.),vect_3D(0.,2.)]))
        self.assertEqual(False, a.DeleteElement('RP JIMBO1'))
    def testAreaBBox(self):
        a = operational_overlay('A-101')
        a.AddElement(operational_area('OA','JIMBO', base_polygon([vect_3D(),vect_3D(1.,1.),vect_3D(0.,2.)])))
        box = a.BoundingBox()
        self.assertEqual(box, [0.0,0.0,1.0,2.0])             
#
#
if __name__ == "__main__":
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(GraphicsTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)
    
#
#