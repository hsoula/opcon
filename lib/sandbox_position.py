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
    def __init__(self, X=0.0, Y=0.0, footprint = None, translator=None):
        # The coordinate translator
        self.MGRS = translator

        # the footprint
        self.footprint = footprint
        if type(self.footprint) == type([]):
            self.footprint = sandbox_geometry.base_polygon(self.footprint)

        if hasattr(X,'x'):
            # case where a vector is provided as first argument
            vect_5D.__init__(self, X.x, X.y)
        else:
            # case where the data is passed as intended
            vect_5D.__init__(self,X,Y)

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
        # Make sure that the footprint is a geometrical object, then attach and set 
        # position to the new footprint's centroid
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

    def toXML(self, doc, node, coord_translator):
        '''Unusual interface that doesn't create a node, but add to an existing one.'''
        # Case of location defined as a coordinate
        mycoord = coord_translator.XYtoUTM(self)
        nd = doc.NewNode('location')
        doc.SetAttribute('type', 'coordinates', nd)
        nd.appendChild(doc.doc.createTextNode(mycoord))
        # Add location to position descriptor
        doc.AddNode(nd, node)

        # Altitude TODO

        # FOOTPRINT TODO

    def fromXML(self, doc, node):
        # Not in use because it needs to be handled at the sim level (to solve for coordinates).
        # Location node
        loc = doc.Get(node, 'location')
        if loc != '':
            self.fromXMLlocation(doc, loc)
            
    def fromXMLlocation(self, doc, node):
        ''' Load in the location node only (useful as it is an option in scenario deifinition.
        '''
        # Full PD node
        nl = doc.Get(node, 'named_location')
        if nl:
            # TODO, yet to be supported feature
            pass
        
        # Coordinates
        cd = doc.Get(node, 'coordinates')
        if cd and self.sim and self.sim.map:
            # Create a position descriptor from scratch
            vec = self.translator.AsVect(cd)
            self.x = vec.x
            self.y = vec.y
        