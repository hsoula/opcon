'''
    A simple implementation of a vector for geographic coordinate system. Don't let you fool by the z attribute, this
    vector classes are not considering the z component in operations. z is just there to provide layering to a 2D
    world.
    
    These classes are utilities to the OPCON Sandbox project. 
    
    CoordConverter/FlatLand -- Interconversion between four geographic coordinate systems: LonLat (decimal), 
    LonLat (DMS), UTM and MGRS as well as FlatLand Projection (based on False Eastings).
    Copyright (C) 2007  Christian Blouin

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
    
    Christian Blouin -- cblouin @ cs dal ca
'''

# import
from math import *

# function

def NormalizeAngle(A):
  '''
     Convert angle values ]-pi,pi]
  '''
  if A >= -pi and A <= pi:
    return A
  
  # Multiple turn compensation
  while abs(A) > 2*pi:
    if A > 0:
      A = A - (2*pi)
    else:
      A = A + (2*pi)
      
  if A >= -pi and A <= pi:
    return A
  
  excess = abs(A) - pi
  nA = pi - excess
  if A < -pi:
    return nA
  else:
    return -nA

# classes

class vect_3D:
  def __init__(self, x=0.0,y=0.0,z=0.0):
    # basic data
    self.x = float(x)
    self.y = float(y)
    self.z = float(z)
    
    # A label that can be use to identify reference
    self.reference = None
    
  def __cmp__(self, other):
    '''
       Same within 7 places
    '''
    if other == None:
      return 1
    dist = (self-other).length()
    return not dist <= 0.0000001
  
  def __str__(self):
    return 'vect_3D( %f, %f, %f )'%(self.x,self.y,self.z)
    
  def length(self):
    '''
       Euclidian distance
    '''
    return (self.x**2 + self.y**2 + self.z**2)**0.5
  
  def __add__(self, other):
    return self.__class__(self.x+other.x,self.y+other.y,self.z+other.z)
  
  def __sub__(self, other):
    return self.__class__(self.x-other.x,self.y-other.y,self.z-other.z)
  
  def __mul__(self, other):
      '''
         Cross product!
      '''
      if type(other) == type(1.0) or type(other) == type(1):
        nx = self.x * other
        ny = self.y * other
        nz = self.z * other
      else:
        nx = (self.y*other.z) - (self.z*other.y)
        ny = (self.x*other.z) - (self.z*other.x)
        nz = (self.x*other.y) - (self.y*other.x)
      
      return self.__class__(nx,ny,nz)
    
  def list2D(self):
    return [self.x,self.y]

  
  def Normal(self):
    '''
       Normalize the vector so it has a length of 1.0
    '''
    mylen = self.length()
    
    self.x = self.x / mylen
    self.y = self.y / mylen
    self.z = self.z / mylen
    
  def BearingTo(self, other):
    ''' 
       Returns a bearing to other in the format [bearing,distance]
    '''
    rel = other - self

    angle = 0.0
    vrange = rel.length()
    
    if vrange == 0.0:
      return [0.0,0.0]
    
    angle = asin(rel.x/vrange)
    
    if rel.y < 0:
      t = (pi/2.0) - abs(angle)
      if rel.x < 0:
        angle = -pi/2.0 - t
      else:
        angle = pi/2.0 + t
        
    return [NormalizeAngle(angle),vrange]
  
  def ToBearing(self, B):
    '''
       Project to a point in space given by bearing
    '''
    # Normalize angle
    B[0] = NormalizeAngle(B[0])
    
    newx = B[1] * sin(B[0]) 
    newy = B[1] * cos(B[0])
    
    
    return self.__class__(self.x + newx, self.y + newy, self.z)
      

class vect_5D(vect_3D):
  def __init__(self,x=0.0, y=0.0, z=0.0 ,course=0.0, move=0.0):
    vect_3D.__init__(self, x,y,z)
    self.course = course
    self.rate = move
    
  def __str__(self):
    return 'vect_5D( %f, %f, %f, course= %f, rate= %f )'%(self.x,self.y,self.z,self.course, self.rate)
  def asBearing(self, mult = 1.0):
    return [self.course,self.rate*mult]

  def Step(self, unit=1.0):
    '''
       move by unit * rate
    '''
    try:
      temp = self.Project(unit)
      self.x = temp.x
      self.y = temp.y
      self.z = temp.z
    except:
      pass
    
  def Project(self, unit=1.0):
    '''
       Return a vector to the next position.
    '''
    return self.ToBearing(self.asBearing(unit))
  

    
    