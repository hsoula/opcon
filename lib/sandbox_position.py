'''
   Position descriptors
'''

import sandbox_geometry

from vector import *


class position_descriptor(vect_5D):
    '''! \ brief A class which treats the position of an entity as a polygon instead of a point.
    Now that the position is no longer a point, some assumption made in earlier version of the code may not work, keep an eye for this.
    Regardless, point manips can still be done on the positition descriptor as they get applied to he centroid of the polygon instead.
    
    '''
    def __init__(self, X=0.0, Y=0.0, footprint = None):
        # the footprint
        self.footprint = footprint
        if type(self.footprint) == type([]):
            self.footprint = sandbox_geometry.base_polygon(self.footprint)
        if hasattr(X,'x'):
            vect_5D.__init__(self, X.x, X.y)
        else:
            vect_5D.__init__(self,X,Y)
    
    '''    
    def __getattr__(self, name):
        ''! \brief Attempts to pass on the call to the footprint.
        ''
        try:
            ''if hasattr(self, name):
                return getattr(self, name)''
            if hasattr(self.footprint, name):
                return getattr(self.footprint, name)
        except:
            pass
      
        # All else fail  
        raise AttributeError, name
    '''
    
    # Information
    def AsVect(self):
        '''! \brief Similar as type casting to a vect_5D
        '''
        return vect_5D(self.x, self.y, self.z, self.course, self.rate)
    
    def Radius(self):
        '''!
           Mean distance for all vertices to centroid.
        '''
        return self.footprint.Radius()
    
    def PointInside(self, P):
        return self.footprint.PointInside(P)
    
    def Overlaps(self, poly):
        '''! \brief call the method on the foot print.
        '''
        return self.footprint.Overlaps(poly)
    def BoundingBox(self):
        return self.footprint.BoundingBox()

    # Modification
    def ToCentroid(self):
        '''! \brief Set location to centroid of the footprint
        '''
        if self.footprint:
            ct = self.footprint.Centroid()
            self.x = ct.x
            self.y = ct.y
            self.z = ct.z
            return True
        return False
    def Set(self, pos):
        '''
           Set position and footprint centered around centroid.
           pos must be a vect_XD.
        '''
        # Compute offset
        offset = pos - self
        
        # offset
        self.x = pos.x
        self.y = pos.y
        self.z = pos.z
        if pos.__class__ == vect_5D().__class__:
            self.course = pos.course
            self.rate = pos.rate
            
        # Set Footprint
        self.footprint.Translate(offset)        
        
    
    
    def SetFootprint(self, fp):
        # Make sure that the footprint is a geometrical object
        try:
            ref = fp.Centroid()
        except:
            return False
        
        # Set the fp's centroid to current position
        # pos = ref + diff
        # diff = pos - ref
        #diff = self - ref
        #fp.Translate(diff)
        self.footprint = fp
        self.ToCentroid()
        
    def Step(self):
        vect_5D.Step(self)
        # Move all the footprint control point
        trans = vect_5D(course=self.course,move=self.rate).Project()
        self.footprint.Translate(trans)