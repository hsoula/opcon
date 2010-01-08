'''
   Sandbox Geometry module
   A test TDD approach.
'''

# Import section
from vector import vect_3D, vect_5D, NormalizeAngle
from algo_DP import Dynamic_Programming

from numpy import array
from numpy.linalg import det

from random import random, gauss, randint
from copy import copy, deepcopy

from math import pi, cos, acos, sin

class geometry_rubberband:
    '''! \brief Compute a rubberband for an arbitrary set of vertices.
    '''
    def Solve(self, V):
        '''! \brief Solve for the convex polygon inscribing all vertices in V.
             \return The set of V defining the convex polygon
        '''
        # If 3 or less vertices, return as polygon
        if len(V) <= 3:
            return base_polygon(V)
        
        # Kernelize all vertices within the extrema
        # Prune the Dataset from interior vertices, keep extrema vertices
        box = self.Extrema(V)
        if len(box) > 2:
            V = self.KernelizeConvexPolygon(V,box, False)
            
        # Define tracking vars
        # Angle of last "matching"
        A = 0.0
        out = [box[0]]
        V.remove(box[0])
        while(len(V)):
            # Find next vertex
            A, nextv = self.Next(A, out[-1], V)
            
            # Add to solution
            if nextv:
                out.append(nextv)
                V.remove(nextv)
                
            # Kernelize
            if len(out) > 2:
                V = self.KernelizeConvexPolygon(V, out)
                
        return base_polygon(out)
                
    def Next(self, A, C, V):
        '''! \brief Find the next vertex to add to the rubberbanding
             \param C vertex to pivot around.
             \return bearingto (float), vertex
        '''
        next = None
        B = [None,None]
        for v in V:
            # Bearing to candidate
            b = C.BearingTo(v)
            if b[0] < 0.0:
                b[0] += 2*pi
                
            # ahead?
            if b[0] < A:
                continue
            
            # Same A as best, is it farther?
            if (b[0] == B[0] and b[1] > B[1]) or (b[0] == A and B[0] == None):
                next = v
                B = b
                
            # Larger and closer
            if b[0] > A and (b[0] < B[0] or B[0] == None):
                next = v
                B = b
        
        return B[0], next
            
            
            
        
    def Extrema(self, V):
        '''! \brief Compute the Up/down left/right most points
             \return a list of vertices
        '''
        minY = maxY = minX = maxX = V[0]
        for v in V:
            if v.x < minX.x:
                minX = v
            elif v.x > maxX.x:
                maxX = v
                
            if v.y < minY.y:
                minY = v
            elif v.y > maxY.y:
                maxY = v
        
        out = [minX]
        if not maxY in out:
            out.append(maxY)
        if not maxX in out:
            out.append(maxX)
        if not minY in out:
            out.append(minY)
            
        return out
     
    def KernelizeConvexPolygon(self, V, polyV, deletematch = True):
        '''! \brief Remove all vertices in V which are inscribed within polyV
             \param V List of all vertices in set
             \param polyV List of all ordered vertices in polygon
             \param deletematch Delete control points too
             \return A new list of candidate vertices
        '''
        mask = base_polygon(polyV)
        
        toremove = []
        
        for v in V:
            if mask.PointInside(v):
                if deletematch:
                    toremove.append(v)
                elif not v in polyV:
                    toremove.append(v)
        
        for i in toremove:
            V.remove(i)
                    
        return V

def ConvexPolygon(V):
    '''! \brief Solve for the largest convex polygon
         \param V a list of vertices
         \return a Base_polygon
         
         Start with the vertices with the smallest Y component, then run a string clockwise.
         Kernelize by removing all vertices inscribed into the current polygon.
    '''
    # Make sure that there is a polygon
    if len(V) <= 3:
        return base_polygon(V)
        
    # Find the extrema vertices
    minY = maxY = minX = maxX = V[0]
    for v in V:
        if v.x < minX.x:
            minX = v
        elif v.x > maxX.x:
            maxX = v
            
        if v.y < minY.y:
            minY = v
        elif v.y > maxY.y:
            maxY = v
    
    out = [minX]
    if not maxY in out:
        out.append(maxY)
    if not maxX in out:
        out.append(maxX)
    if not minY in out:
        out.append(minY)
        
    # Prune the Dataset from interior vertices
    if len(out) > 2:
        V = KernelizeConvexPolygon(V,out, False)
        
    # The tracking angle
    A = 0.0
    bestA = 10.0
    d = 0.0
    out = [minX]
    while(True):
        # remove useless vertices
        if len(out) >= 3:
            V = KernelizeConvexPolygon(V,out)
            
        # find the vertex with the nearest larger bearing to A
        best = None
        for v in V:
            # Do not consider already added vertices
            if (v in out):
                continue
            
            # Bearing ( in [0.360] range)
            B = out[-1].BearingTo(v)
            if B[0] < 0.0:
                B[0] += (2*pi)
                
            # If on the wrong side of bearing, ignore.
            if B[0] < A:
                continue
            
            # Default best
            if best == None:
                best = v
                bestA = B[0]
                d = B[1]
            else:
                if B[0] < bestA:
                    # Store as best if the closest observed yet
                    best = v
                    bestA = B[0]
                    d = B[1]
                elif B[0] == A and B[1] > d:
                    # Always fetch the farthest vertice
                    best = v
                    bestA = B[0]
                    d = B[1]
                    
        if best != None:
            A = out[-1].BearingTo(best)[0]
            if A < 0.0:
                A += 2*pi
            out.append(best)
        else:
            # Will happen when the next vertices is the first one again.
            return base_polygon(out)
            
                    
            
            

def Intersect(A,B):
    '''
       return the intersecting point of two lines OR none
    '''
    p1 = A[0]
    p2 = A[1]
    p3 = B[0]
    p4 = B[1]
    '''
    # clipped BBox
    box = [None,None,None,None]
    box[0] = max(min(p1.x,p2.x),min(p3.x,p4.x))
    box[1] = max(min(p1.y,p2.y),min(p3.y,p4.y))
    box[2] = min(max(p1.x,p2.x),max(p3.x,p4.x))
    box[3] = min(max(p1.y,p2.y),max(p3.y,p4.y))
    
    # No BBox overlap
    if box[0] >= box[2] or box[1] >= box[3]:
        return None
    '''
    # determinants of the matrix
    determinant = (((p4.y-p3.y)*(p2.x-p1.x))-((p4.x-p3.x)*(p2.y-p1.y)))
    
    if abs(determinant) <= 0.00001:
        # lines are parallel
        return None
    
    u = (((p4.x-p3.x)*(p1.y-p3.y)) - ((p4.y-p3.y)*(p1.x-p3.x))) / determinant
    
    if u < 0.0 or u > 1.0:
        return None
    
    diff = p2-p1
    inter = p1 + (diff * u)
    
    if inter.x >= min(p3.x,p4.x) and inter.x <= max(p3.x,p4.x) and inter.y >= min(p3.y,p4.y) and inter.y <= max(p3.y,p4.y):
        return inter
    return None



def DistancePointToSegment(P, A, B):
    # Compute R
    # AP dot AB
    AP = (P-A)
    AB = (B-A)
    
    # Avoid bugs
    if AB.length() == 0.0:
        return AP.length()
    
    APdotAB = AP.x*AB.x + AP.y*AB.y
    ABsq = AB.length() ** 2
    
    r = APdotAB / ABsq
    if r <= 0.0:
        return (A-P).length()
    elif r >= 1.0:
        return (B-P).length()
    else:
        X = A + (AB * r)
        return (X-P).length()
    
def InterceptPoint(P, A, B):
    # Return the intercept point if applicable.
    # Compute R
    # AP dot AB
    AP = (P-A)
    AB = (B-A)
    
    # Avoid bugs
    if AB.length() == 0.0:
        return None
    
    APdotAB = AP.x*AB.x + AP.y*AB.y
    ABsq = AB.length() ** 2
    
    r = APdotAB / ABsq
    if r <= 0.0 or r >= 1.0:
        return None
    else:
        X = A + (AB * r)
        return X    
        
class base_polygon:
    '''! \brief A polygon object
    
         \param pts a list of vect_XD instances.
         
         Access the internal data through .vertices rather than self.pts because some inherited class do not have explicit pts defined (such as the circle).
         
    '''
    def __init__(self, pts = None):
        self.pts = pts
        self.SortPts(pts)

    def __mul__(self, other):
        # returns a scaled copy of the polygon
        if type(other) == type(1) or type(other) == type(1.0):
            out = copy(self)
            out.Scale(other)
            return out
        else:
            raise TypeError

    
    def __len__(self):
        return len(self.pts)
    
    # Properties
    def Radius(self):
        '''! \brief Average distance from the centroid
        '''
        # from the centroid
        center = self.Centroid()
        v = self.vertices()
        cum = 0.0
        for i in v:
            cum += (center-i).length()
        return cum / len(v)
    
    def Area(self):
        '''! \brief Triangulate then sum the area of all triangles.
        '''
        out = 0.0

        # triangle
        T = self.Triangulate()
        
        for i in T:
            out += i.Area()
            
        return out
    
    def BoundingBox(self, pts = None):
        ''' Can overide pts with self.pts'''
        if pts == None:
            pts = self.pts
            
        # Not enough points
        if len(pts) == 1:
            return [pts[0].x, pts[0].y, pts[0].x, pts[0].y]
        
        # Set from first point
        minx = pts[0].x
        maxx = pts[0].x
        miny = pts[0].y
        maxy = pts[0].y
        
        for i in pts[1:]:
            # x
            if i.x < minx:
                minx = i.x
            elif i.x > maxx:
                maxx = i.x
            # y
            if i.y < miny:
                miny = i.y
            elif i.y > maxy:
                maxy = i.y
        
        return [minx,miny,maxx,maxy]
    
    def Centroid(self):
        '''! \brief Runtime computation of the centroid.
        '''
        out = vect_3D()
        for i in self.pts:
            out = out + i
        return out * (1.0/len(self.pts))
    
    def vertices(self):
        return self.pts
    
    # Tests
    def Overlaps(self, other):
        '''
           Return True is other overlaps self.
        '''
        # Stage 1 - Bounding box
        me = self.BoundingBox()
        it = other.BoundingBox()
        
        # Boxes have no overlap
        if me[0] > it[2] or me[2] < it[0] or me[1] > it[3] or me[3] < it[1]:
            return False
        
        # Any vertice into the other
        for i in self.vertices():
            if other.PointInside(i):
                return True
        for j in other.vertices():
            if self.PointInside(j):
                return True
            
        # Any edge crossing another.
        sv = self.vertices()
        ov = other.vertices()
        for s in range(len(sv)):
            for o in range(len(ov)):
                if Intersect([sv[s-1],sv[s]],[ov[o-1],ov[o]]) != None:
                    return True
        
        return False
    def PointInside(self, pt):
        '''! \brief based on the method of even/odd crossing of edges.
             Choose a random ray betwee 0 and pi and hope that no vertices aren't in the way.
        '''
        # Accumulate bearing
        B = []
        for v in self.vertices():
            bear = pt.BearingTo(v)
            if bear[1] == 0.0:
                # Point matching exactly this vertex
                return True
            B.append(bear[0])
        
        # Count crossing
        crossing = 0
        
        # Pick a ray between 0 and 1 radian
        ray = 0.0
        while ray in B:
            ray = random()
            
        for i in xrange(len(B)):
            mn = min(B[i-1],B[i])
            mx = max(B[i-1],B[i])
            if mn < ray and mx > ray and mx-mn < pi:
                crossing += 1
            elif mx-mn == pi:
                return True
                
        # 0 or even crossing is false
        if crossing == 0:
            return False
        
        # Inside if odd number
        return int(crossing) % 2

    


    def DistanceTo(self, P):
        '''! \brief Find the nearest point to all segments of a polygon.
        '''
        d = None
        for i in range(len(self.pts)-1):
            temp = DistancePointToSegment(P, self.pts[i], self.pts[i+1])
            if d == None or temp < d:
                d = temp
        return d
    
    # Convenience
    def RandomPointInside(self, N = 1):
        '''
           Return a/a list of random points that are inside the polygon.
        '''
        mybox = self.BoundingBox()
        dx = mybox[2]-mybox[0]
        dy = mybox[3]-mybox[1]
        out = []
        while len(out) < N:
            temp = vect_5D(mybox[0]+random()*dx,mybox[1]+random()*dy)
            if self.PointInside(temp):
                out.append(temp)
        if N == 1:
            return out[0]
        return out
    
    # Transformation
    def Normalize(self):
        '''! \brief Bring centroid to coordinate origin
        '''
        ct = self.Centroid()
        for i in range(len(self.pts)):
            self.pts[i] = self.pts[i] - ct
            
    def Translate(self, offset):
   
        v = self.vertices()
        for i in range(len(v)):
            v[i] = v[i] + offset
            
    def Rotate(self, angle, center = None):
        # By default scale to centroid
        if center == None:
            center = self.Centroid()
        
        v = self.vertices()
        for i in range(len(v)):
            diff = center.BearingTo(v[i])
            diff[0] += angle
            v[i] = center.ToBearing(diff)
            
    def Scale(self, factor, center = None):
        # By default scale to centroid
        if center == None:
            center = self.Centroid()
        
        v = self.vertices()
        for i in range(len(v)):
            diff = (v[i] - center) * factor
            v[i] = center + diff
        
            
        
    def Extend(self, offset):
        # Make the polygon extend by offset for each vertice from the centroid
        # such that the bounding box is twice as large.
        box = self.BoundingBox()
        # Original dimentions
        dx = box[2] - box[0]
        dy = box[3] - box[1]
        # New corner
        ncx = box[0] - offset
        ncy = box[1] - offset
        # New dimentions
        ndx = dx + 2*offset
        ndy = dy + 2*offset
        
        # reposition all vertices.
        for i in range(len(self.pts)):
            tempx = (self.pts[i].x - box[0])/dx
            tempy = (self.pts[i].y - box[1])/dy
            self.pts[i].x = ncx + (ndx*tempx)
            self.pts[i].y = ncy + (ndy*tempy)
        

    
    # IO
    def fromXML(self, doc, node):
        '''! \brief Write as an array of points.
        '''
        pass
        
        
    # Internal Methods    
    def AlignTo(self,other):
        '''! \brief Privide a 1-1 correcpondance for each vertices.
        '''
        M = []
        for i in range(len(self)):
            temp = []
            for j in range(len(other)):
                temp.append((self.pts[i]-other.pts[j]).length())
            M.append(temp)
        # Accumulate matrix
        A = copy(M)
        for i in range(len(self)-1,-1,-1):
            for j in range(len(other),-1,-1):
                print i,j
        print M
            
    def Triangulate(self):
        '''
           Knock one vertex at the time until there is only a collection of triangles.
           Use recursion to do that.
        '''
        # Stop recusion if polygon is a triangle
        if len(self.vertices()) == 3:
            return [triangle(copy(self.vertices()))]
        
        # Chip a triangle ###################
        for i in range(len(self.vertices())):
            if i == 0:
                temp = [self.vertices()[-1]] + self.vertices()[:2]
            else:
                temp = self.vertices()[i-1:i+2]
            if len(temp) == 3:
                temp = triangle(temp)
                # Point inside polygon
                if self.PointInside(temp.Centroid()):
                    # make a sligntly shorter edge for crossing test
                    v = self.vertices()
                    edge = [(v[i-1]*0.99)+(v[i+1]*0.01), (v[i-1]*0.01)+(v[i+1]*0.99)]
                    nooverlap = True
                    for j in range(1,len(v)-1):
                        if Intersect(edge,v[j-1:j+1]):
                            nooverlap = False
                            break
                    if nooverlap:
                        pts = copy(self.vertices())
                        pts.remove(pts[i])
                        return [temp] + base_polygon(pts).Triangulate()
        raise Exception, 'Failure to chip a triangle off a polygon'
        
        
    def PositiveAngle(self, A):
        '''
           Return angle in the [0,2pi[ range
        '''
        if A >= 0:
            while A > 2*pi:
                A = A - 2*pi
            return A
        # negative angle
        while A < 0.0:
            A = A + 2*pi
        return A
    
    def SolveInternalAngles(self):
        ''' match the pts '''
        self.angles = []
        
        for i in range(len(self.pts)):
            AB = self.pts[i].BearingTo(self.pts[i-1])
            if i < len(self.pts) - 1:
                AC = self.pts[i].BearingTo(self.pts[i+1])
            else:
                # complete the loop
                AC = self.pts[i].BearingTo(self.pts[0])

        self.angles.append(self.PositiveAngle(AC[0] - AB[0]))
    def SortPts(self, pts):
        if not pts:
            return
        # Keep track of the bearing change relative to the centroid.
        ref = self.Centroid()
        
        # The cummulative score
        A = []
        v = self.vertices()

        for i in range(len(v)):
            A.append( ref.BearingTo(v[i])[0])

    
class triangle(base_polygon):
    def __init__(self, pts = None):
        # ensure the right number of vertices
        if len(pts) != 3:
            if len(pts) > 3:
                pts = pts[:3]
            else:
                return
            
        # base class
        base_polygon.__init__(self, pts)
        
        # Internal angles and edge length
        self.SolveParams()
        
        # Circumcenter
        self.Circumcenter()
    
    def Area(self):
        '''
           Area = Base * h
           base = AC (b)
           sin(A) = h/c -> h = c sin(A)
           Area = bc sin(A)
        '''
        return 0.5 * self.c * self.b * sin(self.A)
        
        
        
    def PointInCircle(self, pt):
        return (pt-self.circumcenter).length() <= self.circumradius

    
    # Private Interface
    
    def Circumcenter(self):
        self.Circumradius()
        a = array([[0,0,1.],[0,0,1.],[0,0,1.]])
        myarray = array([[0,0,1.],[0,0,1.],[0,0,1.]])
        for i in range(len(self.pts)):
            myarray[i][0] = (self.pts[i].x**2) + (self.pts[i].y**2)
            myarray[i][1] = self.pts[i].y
            a[i][0] = self.pts[i].x
            a[i][1] = self.pts[i].y
            # index 2 is already set to 1
        a = det(a)
        bx = -1.0 * det(myarray)
        for i in range(len(self.pts)):
            myarray[i][0] = (self.pts[i].x**2) + (self.pts[i].y**2)
            myarray[i][1] = self.pts[i].x
            # index 2 is already set to 1
        by = det(myarray)
        self.circumcenter = vect_3D(-bx/(2*a),-by/(2*a))
        a = 1
        '''
        self.Circumradius()
        R = self.circumradius
        
        # The square triangle from mid-AC can be used
        angle = acos((self.b/2.0)/R)
        angleratio = angle/self.A
        
        temp = (self.pts[2] * (1.0-angleratio)) + (self.pts[1] * angleratio)
        temp = self.pts[0].BearingTo(temp)[0]
        
        self.circumcenter = self.pts[0].ToBearing([temp, R])
        '''
    
    def Circumradius(self):
        a = self.a
        b = self.b
        c= self.c
        
        s = (a+b+c)/2.0
        up = a*b*c
        down = 4*(s*(a+b-s)*(a+c-s)*(b+c-s))**0.5
        self.circumradius = up/down

    def SolveParams(self):
        # define all angles and lenghts
        p = self.pts
        
        AB = p[0].BearingTo(p[1])
        AC = p[0].BearingTo(p[2])

        self.A = self.PositiveAngle(AC[0] - AB[0])
        self.c = AB[1]
        self.b = AC[1]

        BC = p[1].BearingTo(p[2])
        BA = p[1].BearingTo(p[0])
        self.B = self.PositiveAngle(BA[0] - BC[0])
        self.a = BC[1]

        CA = p[2].BearingTo(p[0])
        CB = p[2].BearingTo(p[1])
        self.C = self.PositiveAngle(CB[0] - CA[0])
        

        
    def SortPts(self, pts):
        # Centroid
        self.centroid = (pts[0] + pts[1] + pts[2]) * 0.333333

        # Bearings
        bearing = []
        for i in range(3):
            bearing.append(self.PositiveAngle(self.centroid.BearingTo(pts[i])[0]))

        # index
        self.pts = []
        while bearing:
            val = min(bearing)
            for i in range(len(bearing)):
                if val == bearing[i]:
                    self.pts.append(pts[i])
                    pts.remove(pts[i])
                    bearing.remove(val)
                    break




class circle(base_polygon):
    # Number of vertices to return for the virtual polygon
    vertice_resolution = 16
    def __init__(self, center, radius):
        base_polygon.__init__(self, [center])
        self.center = center
        self.radius = radius
    def Centroid(self):
        return self.center
    def Radius(self):
        return self.radius
    
    def PointInside(self, pt):
        return (pt-self.center).length() <= self.radius
    
    def Area(self):
        return pi*(self.radius**2)
    
    def BoundingBox(self):
        c = self.center
        r = self.radius
        return [c.x-r,c.y-r,c.x+r,c.y+r]
    def vertices(self):
        out = []
        a = 2*pi/circle.vertice_resolution
        for i in range(circle.vertice_resolution):
            out.append( self.center.ToBearing([i*a,self.radius]) )
        return out
    
    def Rotate(self, angle, center = None):
        '''
           Rotation would be a waste of time for a circle if center == centroid
        '''
        if center == None:
            return
        
        # Rotate around an arbitratry center
        bearing = center.BearingTo(self.center)
        bearing[0] += angle
        self.center = center.ToBearing(bearing)
    def Scale(self, factor, center = None):
        if center == None:
            center = self.center
            
        V = self.center - center
        V = V * factor
        self.center = center + V
        self.radius *= factor
        
        
        
    def SortPts(self, pts):
        pass
    def Translate(self, offset):
        self.center = self.center + offset
    def Extend(self, offset):
        # overload this method
        self.radius += 2*offset
    def Normalize(self):
        '''! Bring center to origin.
        '''
        self.center = vect_3D()
        
        
class morphable_polygon(base_polygon):
    '''! A polygon which morph from one shape to another according to a delta value.
    '''
    def __init__(self, start, end):
        '''! \brief Create from a start and end polygon.
        '''
        base_polygon.__init__(self)
        self.start = start
        self.end = end
        
        self.map = []
        
        self.delta = 0.0
        
        self.__compute()
    
    def __compute(self):
        '''! \brief simple implementation of a polygon alignment.
        '''
        # randomly insert point duplicates
        while len(self.start) < len(self.end):
            r = randint(0,len(self.start)-1)
            self.start.pts.insert(r,self.start.pts[r] * 1.0)
        while len(self.end) < len(self.start):
            r = randint(0,len(self.end)-1)
            self.end.pts.insert(r,self.end.pts[r] * 1.0)
            
        self.pts = range(len(self.end))
            
        # Set Delta to 0
        self.SetDelta(0.0)
            
        
    def _compute(self):
        '''! \brief Compute the morphable polygon by creating an alignment of vertices.
              Eraseme.
        '''
        S = deepcopy(self.start)
        S.Normalize()
        E = deepcopy(self.end)
        E.Normalize()
        gap = abs(len(S)-len(E))
        
        # Alignment object
        DP = Dynamic_Programming(max_gap = gap)
        
        # Distance matrix
        DM = []
        for i in S.vertices():
            temp = []
            for j in E.vertices():
                temp.append((i-j).length())
            DM.append(temp)
        
        # Get aligned path
        mapp = DP.Solve(DM)
        
        # Complete mapping
        L = max( len(self.start), len(self.end) )
        self.map.append(range(L))
        self.map.append(range(L))
        
        ls = 0
        le = 0
        for i in mapp:
            pass
        
        
        
    def SetDelta(self, D):
        self.delta = D
        for i in range(len(self.pts)):
            self.pts[i] = (self.end.vertices()[i] * self.delta) + (self.start.vertices()[i] * (1-self.delta)) 
        
# Test Units
import unittest

class GeometryTest(unittest.TestCase):
    def setUp(self):
        pass
    
    def testbPolygonPointIn(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = base_polygon([v1,v2,v3])
        self.assertEqual(a.PointInside(vect_3D(0.1,0.1)), True)
        
    def testbPolygonPointOut(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = base_polygon([v1,v2,v3])
        self.assertEqual(a.PointInside(vect_3D(-0.1,0.1)), False)   
        
    def testbPolygonPointOnLine(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = base_polygon([v1,v2,v3])
        self.assert_(a.PointInside(vect_3D(0.5,0.0)))
        
    def testbPolygonPointOnPoint(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = base_polygon([v1,v2,v3])
        self.assert_(a.PointInside(vect_3D(0.0,0.0)))
        
    def testbPolygonCentroid(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        v4 = (v1+v2+v3)*(1.0/3.0)
        a = base_polygon([v1,v2,v3])
        self.assertAlmostEqual(a.Centroid().length(),v4.length())
        

    def testTriangleInit(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        v4 = vect_3D(1.0, 1.0)
        a = triangle([v1,v2,v3,v4])
        self.assertEqual(len(a.pts),3)
        
    def testTrianglePointIn(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = triangle([v1,v2,v3])
        self.assertEqual(a.PointInside(vect_3D(0.1,0.1)), True)
        
    def testTrianglePointOut(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = triangle([v1,v2,v3])
        self.assertEqual(a.PointInside(vect_3D(-0.1,0.1)), False)   
        
    def testTrianglePointOnLine(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = triangle([v1,v2,v3])
        self.assert_(a.PointInside(vect_3D(0.5,0.0)))
        
    def testTrianglePointOnPoint(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = triangle([v1,v2,v3])
        self.assert_(a.PointInside(vect_3D(0.0,0.0)))
        
    def testTriangleCentroid(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        v4 = (v1+v2+v3)*(1.0/3.0)
        a = triangle([v1,v2,v3])
        self.assertAlmostEqual(a.Centroid().length(),v4.length())
        
    def testTriangleArea(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(1.0, 0.0)
        v3 = vect_3D(0.0, 1.0)
        a = triangle([v1,v2,v3])
        self.assertAlmostEqual(a.Area(),0.5)
        
    def testTriangleArea2(self):
        v1 = vect_3D(0.0, 0.0)
        v2 = vect_3D(0.5, 0.0)
        v3 = vect_3D(0.0, 10.0)
        a = triangle([v1,v2,v3])
        self.assertAlmostEqual(a.Area(),2.5)
        
    def testtriangleCircumCenter(self):
        # Test 100 random triangles
        trs = []
        for i in xrange(100):
            trs.append(self.RandomTriangleOnCircle())
            
        dst = []
        for i in trs:
            dst.append((i[0].circumcenter - i[1]).length())
            
        dst.sort()
        
        self.assert_(dst[-1] < 0.001, 'Max dst= %f'%(dst[-1]))
        
    def testtriangleCircumRadius(self):
        # Test 100 random triangles
        trs = []
        for i in xrange(100):
            trs.append(self.RandomTriangleOnCircle())
            
        dst = []
        for i in trs:
            dst.append(i[0].circumradius - i[2])
            
        dst.sort()
        
        self.assertAlmostEqual(dst[-1],0.0 )  
        
    def testtriangleInCircumRadius(self):
        # Test 100 random triangles
        trs = []
        for i in xrange(100):
            trs.append(self.RandomTriangleOnCircle())
            
        dst = []
        for i in trs:
            # A point 
            pt = i[1].ToBearing([pi*2*random(),2.0*i[2]*random()])
            dst.append( i[0].PointInCircle(pt) == ((pt-i[1]).length() <= i[2]))
            
        dst.sort()
        
        self.assertFalse(False in dst)  
            
    def RandomTriangleOnCircle(self):
        center = vect_3D(0.5 - random(), 0.5 - random())
        radius = abs(gauss(1.0,2.0)) 
        
        angles = []
        for i in xrange(3):
            angles.append(random()*2*pi)
            
        pt = []
        for i in angles:
            pt.append(center.ToBearing([i,radius]))
            
        return triangle(pt), center, radius
        
        
    def testtriangleInternalAngles(self):
        out = []
        for i in xrange(100):
            myt = self.RandomTriangleOnCircle()[0]
            out.append(abs(myt.A+myt.B+myt.C-pi) < 0.001)
        self.assert_(not False in out)
    def testOverlapPosCase1(self):
        A = base_polygon([vect_3D(0,0),vect_3D(1,0),vect_3D(0,1)])
        B = base_polygon([vect_3D(0.1,0.1),vect_3D(1.1,0.1),vect_3D(0.1,1.1)])
        self.assertEqual(A.Overlaps(B),True)
        
    def testOverlapPosCase2(self):
        A = base_polygon([vect_3D(0,0),vect_3D(1,0),vect_3D(0,1)])
        B = base_polygon([vect_3D(1,0),vect_3D(1,1),vect_3D(2,0)])
        self.assertEqual(A.Overlaps(B),True)
        
    def testOverlapPosCase3(self):
        A = base_polygon([vect_3D(0,0),vect_3D(1,0),vect_3D(0,1)])
        B = base_polygon([vect_3D(0.6,0.6),vect_3D(0.7,0.7),vect_3D(0.65,-10.0)])
        self.assertEqual(A.Overlaps(B),True)
        
    def testOverlapNegCase1(self):
        A = base_polygon([vect_3D(0,0),vect_3D(1,0),vect_3D(0,1)])
        B = base_polygon([vect_3D(0.6,0.6),vect_3D(1.6,0.6),vect_3D(0.6,1.6)])
        self.assertEqual(A.Overlaps(B),False)
        
    def testOverlapNegCase2(self):
        A = base_polygon([vect_3D(0,0),vect_3D(0.9,0),vect_3D(0,0.9)])
        B = base_polygon([vect_3D(1,0.1),vect_3D(0,1.0),vect_3D(1,1)])
        self.assertEqual(A.Overlaps(B),False)

    def testVerticesPoly(self):
        v1 = vect_3D(-10.0, 0.0)
        v2 = vect_3D(1.0, -10.0)
        v3 = vect_3D(0.0, 1.0)
        a = base_polygon([v1,v2,v3])
        self.assertEqual(a.vertices(),a.pts)
        
    def testVerticesCircle(self):
        a = circle(vect_3D(), 1.0)
        self.assertAlmostEqual((a.vertices()[10]-vect_3D(-0.707107,-0.707107)).length(), 0.0, places = 6)
        
    def testCircleRotate(self):
        a = circle(vect_3D(),1.0)
        center = vect_3D(1.0,0.0)
        angle = pi
        a.Rotate(angle,center)
        self.assertAlmostEqual((a.Centroid()-vect_3D(2.0,0.0)).length(), 0.0)
    def testPolyTriangulate(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,0.5)
        v2 = vect_3D(0.7,-0.5)
        v3 = vect_3D(-0.7,-0.5)
        v4 = vect_3D(-1,0.5)
        a = base_polygon([v0,v1,v2,v3,v4])
        self.assertEqual(len(a.Triangulate()),3)

    def testPolyArea(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,1)
        v2 = vect_3D(1,0)
        v3 = vect_3D(0,0)
        a = base_polygon([v0,v1,v2,v3])
        self.assertAlmostEqual(a.Area(),1.0)
    def testPolyArea2(self):
        v0 = vect_3D(-1,0)
        v1 = vect_3D(-1,-1)
        v2 = vect_3D(0,0.5)
        v3 = vect_3D(1,1)
        v4 = vect_3D(1,0)
        a = base_polygon([v0,v1,v2,v3,v4])
        self.assertAlmostEqual(a.Area(),1.5)
    
    def testPolyScale(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,1)
        v2 = vect_3D(1,0)
        v3 = vect_3D(0,0)
        a = base_polygon([v0,v1,v2,v3])
        a.Scale(2.0)
        ct = a.Centroid()
        self.assertAlmostEqual((ct-vect_3D(0.5,0.5)).length(),0.0)
    def testPolyScale2(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,1)
        v2 = vect_3D(1,0)
        v3 = vect_3D(0,0)
        a = base_polygon([v0,v1,v2,v3])
        a.Scale(2.0,vect_3D())
        ct = a.Centroid()
        self.assertAlmostEqual((ct-vect_3D(0.5,0.5)).length(),(2**0.5)/2.0)   
        
    def testCircleScale(self):
        a = circle(vect_3D(),1.0)
        a.Scale(2.0)
        self.assertAlmostEqual(a.radius,2.0)
    def testCircleScale2center(self):
        a = circle(vect_3D(),1.0)
        a.Scale(2.0, vect_3D(1,1))
        center = (a.center-vect_3D(-1,-1)).length()
        self.assertAlmostEqual(center,0.0)
    def testCircleScale2radius(self):
        a = circle(vect_3D(),1.0)
        a.Scale(2.0, vect_3D(1,1))
        self.assertAlmostEqual(a.radius,2.0)   
    def testPolyTranslate(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,1)
        v2 = vect_3D(1,0)
        v3 = vect_3D(0,0)
        a = base_polygon([v0,v1,v2,v3])
        a.Translate(vect_3D(-0.5, -0.5))
        self.assertEqual(a.Centroid(),vect_3D())
    def testPolyRotatecentroid(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,1)
        v2 = vect_3D(1,0)
        v3 = vect_3D(0,0)
        a = base_polygon([v0,v1,v2,v3])
        a.Rotate(pi/2.0)
        self.assertEqual(a.Centroid(),vect_3D(0.5,0.5))
    def testPolyRotateCorner(self):
        v0 = vect_3D(0,1)
        v1 = vect_3D(1,1)
        v2 = vect_3D(1,0)
        v3 = vect_3D(0,0)
        a = base_polygon([v0,v1,v2,v3])
        a.Rotate(pi/2.0)
        self.assertEqual(a.vertices()[0],vect_3D(1,1))
    def testConvexSquare(self):
        # Should return the same square
        v = []
        v.append(vect_3D(-1,-1))
        v.append(vect_3D(-1,1))
        v.append(vect_3D(1,1))
        v.append(vect_3D(1,-1))
        
        self.assertEqual(len(geometry_rubberband().Solve(v).vertices()),4)
        
    def testConvexSquare1(self):
        # Should return the same square
        v = []
        v.append(vect_3D(-1,-1))
        v.append(vect_3D(-1,1))
        v.append(vect_3D(1,1))
        v.append(vect_3D(1,-1))
        v.append(vect_3D(0,0))
        
        
        self.assertEqual(len(geometry_rubberband().Solve(v).vertices()),4)    
    
    def testConvexSquare2(self):
        # Should return the same square
        v = []
        v.append(vect_3D(-1,-1))
        v.append(vect_3D(-1,1))
        v.append(vect_3D(1,1))
        v.append(vect_3D(1,-1))
        v.append(vect_3D(2,0))

        self.assertEqual(len(geometry_rubberband().Solve(v).vertices()),5)      
        
    def testConvexSquare3(self):
        # Should return the same square
        v = []
        v.append(vect_3D(-1,-1))
        v.append(vect_3D(-1,1))
        v.append(vect_3D(1,1))
        v.append(vect_3D(1,-1))
        v.append(vect_3D(2,0))
        v.append(vect_3D(0.7,0.7))


        self.assertEqual(len(geometry_rubberband().Solve(v).vertices()),5)  
        
    def testConvexSquare4(self):
        # Should return the same square
        v = []
        v.append(vect_3D(0,1))
        v.append(vect_3D(.7,.7))
        v.append(vect_3D(1,0))
        v.append(vect_3D(.7,-.7))
        v.append(vect_3D(0,-1))
        v.append(vect_3D(-0.7,-0.7))
        v.append(vect_3D(-1, 0))
        v.append(vect_3D(-.7, 0.7))
        


        self.assertEqual(len(geometry_rubberband().Solve(v).vertices()),8)  
        
    def testConvexSquare6(self):
        # Test the kernelization
        v = []
        for i in xrange(100):
            v.append(vect_3D(gauss(0.0,1.0), gauss(0.0,1.0)))

        self.assert_(len(geometry_rubberband().Solve(v).vertices()))     
        
    def testConvexSquare5(self):
        # Test the kernelization
        v = []
        for x in xrange(13):
            for y in xrange(13):
                X = -6 + x
                Y = -6 + y
                if (X**2 + Y**2)**0.5 <= 6.01:
                    v.append(vect_3D( float(X), float(Y)))

        self.assertEqual(len(geometry_rubberband().Solve(v).vertices()),12)  

    def testLineIntersect(self):
        l1 = [vect_3D(-1,-1),vect_3D(1,1)]
        l2 = [vect_3D(-1,1),vect_3D(1,-1)]
        self.assertEqual(Intersect(l1, l2), vect_3D())
        
    def testLineIntersect1(self):
        l1 = [vect_3D(-1,-1),vect_3D(1,1)]
        l2 = [vect_3D(-1,-1),vect_3D(-10,1)]
        self.assertEqual(Intersect(l1, l2), vect_3D(-1,-1))
        
    def testLineIntersect2(self):
        l1 = [vect_3D(-1,-1),vect_3D(-0.01,0.01)]
        l2 = [vect_3D(-1,1),vect_3D(-10,1)]
        self.assertEqual(Intersect(l1, l2), None)
    def testAlignToSelf(self):
        a = base_polygon([vect_3D(1,1),vect_3D(1,-1),vect_3D(-1,-1)])
        b = base_polygon([vect_3D(1,1),vect_3D(1,-1),vect_3D(1,-3),vect_3D(0,-3),vect_3D(-1,-1)])
        
        x = morphable_polygon(a,b)
        x.SetDelta(0.5)
        self.assertTrue(True)
#
#
if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(GeometryTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)