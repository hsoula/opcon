
'''
    OPCON Sandbox -- Map Module
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
import os.path
import os
from pickle import loads, dumps, HIGHEST_PROTOCOL
from math import pi, ceil
from copy import deepcopy, copy
from string import digits
from time import time


import Image
import ImageDraw

from vector import *
from FlatLand import FlatLand
from sandbox_XML import sandboXML

# Variables
Sf = {}
Sf['unrestricted'] = 1/1.0
Sf['restricted'] = 1/2.0
Sf['urban'] = 1/2.0
Sf['severely restricted'] = 1/10.0
Sf['impassable'] = 1/100000.0
Sf['water'] = 1/100000.0

# function

# classes
class sandbox_FlatLand(FlatLand):
  def __init__(self, format = 'MGRS'):
    # INherits
    FlatLand.__init__(self)
    
    # Coord format
    self.format = format
    
  def AsString(self, vect, res = 2):
    '''! \brief returns a coord in the prefered coordinate system.
    '''
    # Km to meters
    vect = vect * 1000
    
    # Get XY
    c = self.XYtoUTM(vect)
    
    if self.format == 'MGRS':
      return self.AsMGRS(c,precision=res)
    elif self.format == 'UTM':
      return self.AsUTM(c)
    elif self.format == 'LL':
      return self.AsLatLong(c,dms=True)
    
    return 'Set Reference Point'
  
  def AsVect(self, coord):
    '''! \brief Provide a coord to FlatLand conversion.
    '''
    # Turn into a UTM
    c = self.AsUTM(coord, internal = True)
    c = self.UTMtoXY(c)
    return c * 1000**-1
  
class mgrs_translator_old:
  def __init__(self, refUTM, refvect):
    self.offset = vect_5D()
    self.valid = True
    
    # Zones
    self.zones = {}

    self.subzones = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    self.mgrsNS = ['EDCBAVUTSRQPNMLKJHGF','VUTSRQPNMLKJHJFEDCBA']
    for i in range(2):
      self.mgrsNS[i].reverse()
    self.mgrsEW = ['ABCDEFGH','JKLMNPQR', 'STUVWXYZ', 'ABCDEFGH','JKLMNPQR', 'STUVWXYZ']
    
    self.Bind(refUTM, refvect)
    
  def Bind(self, refMGRS, refVect):
    '''! \brief Define reference points based on Geodesic zones.
         \param refMGRS A string with fully formed MGRS coordinates
         \param refVect A list of XY or a vect_XD instance.
         
         Overwrite if a refMGRS is inside an already referenced zone.
    '''
    # Type casting
    if type(refVect) == type([]):
      refVect = vect_5D(refVect[0],refVect[1])
      
    # Tokenize
    tk = self.Tokenize(refMGRS)
    
    # Offset within zone
    offset = self.OffsetInZone(tk)
    
    # Reference point
    refpoint = refVect - offset
    
    # Store in zone
    self.zones[str(tk[0])+tk[1]] = refpoint
    
    

  # Interface
  def GetZone(self, vect):
    '''! \brief Return the Zone in which the vect is in
    '''
    # Key list
    kl = []
    for i in self.zones.keys():
      kl.append( [int(i[:-1]), i[-1]] )
    kl.sort()
    kl.reverse()
    
    # Find the first match
    besty = None
    bestx = None
    for i in kl:
      k = str(i[0])+i[1]
      temp = vect - self.zones[k]
      
    
  
  def OffsetInZone(self, tk):
    '''! \brief Offset from the bottom corner of a zone. In Km
    '''
    # NS boxes
    NS = self.mgrsNS[tk[0]%2]
    dY = 100. * (NS.find(tk[3]) + float('0.'+tk[5]))
    
    # EW box
    EW = tk[0]%6 - 1
    if EW == -1:
      EW = 5
    EW = self.mgrsEW[EW]
    dX = 100. * (EW.find(tk[2]) + float('0.'+tk[4]))
    
    return vect_5D(dX,dY)
    
    
    
  def GetZoneVect(self, tk):
    '''! \brief Return the vector of the lower left corner of a zone, guess it if unknown
    '''
    zn = str(tk[0])+tk[1]
    if zn in self.zones:
      return self.zones[zn]
    
    # out
    out = vect_5D()
    # FInd nearest zone in longitude
    for i in self.zone.keys():
      lat = int(i[:-1])
      if lat == tk[0]:
        out.x = self.zones[i].x
        break
      elif abs(lat - tk[0]) == 1:
        out.x = (800. * (lat - tk[0])) + self.zones[i].x
        break
      else:
        out.x = (800. * (lat - tk[0])) + self.zones[i].x
        
    # Find the best NS subzone
    for i in self.zone.keys():
      lat = self.subzones.find(i[-1])
      if lat == tk[0]:
        out.y = self.zones[i].y
        break
      elif abs(lat - tk[0]) == 1:
        out.y = (2000. * (lat - tk[0])) + self.zones[i].y
        break
      else:
        out.y = (2000. * (lat - tk[0])) + self.zones[i].y
        
    return out
  
  def AsString(self, vect, res = 2):
    '''
       Return the string from a vector in km
    '''
    if type(vect) == type([]) or type(vect) == type(()):
      vect = vect_5D(vect[0],vect[1])
    # To meters
    vect = (vect * 1000) + self.offset
    tk = self.XYToTokens([vect.x,vect.y])
    
    # Trim tk[4] and tk[5]
    tk[4] = tk[4][:res]
    tk[5] = tk[5][:res]
    
    # Stringify
    for i in range(5):
      tk[i] = str(tk[i])
    
    return ''.join(tk)
  
  def AsVect(self, utm):
    '''
       Make a vector in km from a mgrs string. Center to 1m resolution.
    '''
    tk = self.Tokenize(utm)
    tk = self.PreciseCentre(tk)
    XY = self.TokensToXY(tk)
    return vect_5D(-1*(self.offset.x-XY[0])/1000.0,-1*(self.offset.y-XY[1])/1000.0)
    
  
  def Parse(self, utm):
    '''
       Translate utm into x,y
    '''
    tokens = self.Tokenize(utm)
    return self.TokensToXY(tokens)
    
    
    
    
  def XYToTokens(self, XY):
    '''
       Fill with a 1m resolution
    '''
    tk = ['','','','','','']
    x = XY[0]
    y = XY[1]
    
    # Set
    tk[0] = int(x/800000.0) + 1
    x = x - ((tk[0] -1) * 800000)
    
    # Second token
    tk[1] = self.mgrsNS[0][int(y/2000000.0)]
    y = y - int(y/2000000.0) * 2000000.0
    
    # Third token
    index = (tk[0]%6) - 1
    if index == -1:
      index = 5
    tk[2] = self.mgrsEW[index][int(x/100000.0)]
    x = x - int(x/100000.0) * 100000.0
    
    # Fourth token
    index = index%2
    tk[3] = self.mgrsNS[index][int(y/100000.0)]
    y = y - int(y/100000.0) * 100000.0
    
    # Fifth and Sixth tokens
    tk[4] = str(int(x))
    tk[5] = str(int(y))
    
    # Leading zeros
    for i in [4,5]:
      while len(tk[i]) < 5:
        tk[i] = '0' + tk[i]
    
    return tk
  
  def TokensToXY(self, tk):
    ''' Not perfect, but working if away from the poles.
    '''
    # Set
    myset = tk[0]
    myX = (myset - 1) * 800000.0 # Offset in meters
    
    # Second token
    mystring = self.mgrsNS[myset%2]
    myY = mystring.find(tk[1]) * -100000.0
    
    # Third tokens
    temp = (myset%6) - 1
    if temp == -1:
      temp = 5
    mystring = self.mgrsEW[temp]
    if mystring.find(tk[2]) == -1:
      return [None, None]
    myX = myX + (mystring.find(tk[2]) * 100000.0)
    
    # Fourth Tokens
    myindex = ((myset%6)-1)
    if myindex == -1:
      myindex = 5
    myindex = myindex%2
    mystring = self.mgrsNS[myindex]
    if mystring.find(tk[3]) == -1:
      return [None, None]
    myY = myY + (mystring.find(tk[3]) * 100000.0)
    
    # Ensure a resolution to the meter!
    if len(tk[4]) != 5:
      self.FillTokens(tk)
      
    # Fifth, Sixth token 
    myX = myX + int(tk[4])
    myY = myY + int(tk[5])
    
    return [myX,myY]
    
  def FillTokens(self,tk):
    for i in [-1,-2]:
      while len(tk[i]) < 5:
        tk[i] = tk[i] + '0'
    return tk
  def PreciseCentre(self, tk):
    ''' Make it to the centre of the grid square, down to a 1 m resolution
    '''
    for i in [-1,-2]:
      while len(tk[i]) < 5:
        tk[i] = tk[i] + '5'
    return tk
    
  def Tokenize(self, utm):
    token = []
    
    # find the sector number
    cur = 0
    temp = ''
    while cur < len(utm):
      if utm[cur] in digits:
        temp = temp + utm[cur]
      else:
        token.append(int(temp))
        break
      cur = cur + 1
    
    # Letter of major sector
    token.append(utm[cur])
    
    utm = utm[cur+1:]
    
    # Is there a sub-grid?
    if utm:
      token.append(utm[0])
      token.append(utm[1])
      utm = utm[2:]
    
    # Resolution
    if utm:
      # Split in half
      a = int(len(utm)/2.0)
      token.append(utm[:a])
      token.append(utm[a:])
    return token
      
      

  
class sandbox_map:
  code_terrain = {}
  def __init__(self, mapenv = None):
    #self.path = os.path.join(os.getcwd(),'maps')
    # Linear transform from km to pixels (mX + B)
    self.m = 1.0
    self.B = [0,0]
    
    if not mapenv:
      mapenv = 'blankworld'

    self.mapenv = mapenv
    # Set path and initialize the data
    self.path = os.path.join(os.environ['OPCONhome'],'maps',mapenv)
    
    # Metadata
    self.data = {'climate':'temperate','width':100,'ref XY':vect_3D(),'ref coord':'00d00\'00" 00d00\'00"'}
    self.frictions = {}
    # Catch missing data, create default structures
    self.CreateMap()
    self.Initialize()
      
    # For path finding
    self.pathspan = 2.0
    
    if not self.data.has_key('climate'):
      self.data['climate'] = 'temperate'
      
    # Path Cache
    self.pathcache = PathCACHE(self.MGRS,os.path.join(self.path,'path_cache.dat'))
    self.pathcache.Load()
    
  def Name(self):
    return self.mapenv
  def CreateMap(self):
    '''! \brief Remedy to the lack of a file structure for an environment
    '''
    # Make the path
    if not os.path.exists(self.path):
      os.mkdir(self.path)
    
    # Make the graphic file
    if not os.access(os.path.join(self.path,'main.png'),os.F_OK):
      # A blank file with white background
      temp = Image.new('RGB',(1000,500),(255,255,255))
      temp.save(os.path.join(self.path,'main.png'),'PNG')
    
    self.graphicfile = 'main.png'
      
    # Make the terrain file
    if not os.access(os.path.join(self.path,'terrain.png'),os.F_OK):
      # A boring plain
      temp = Image.new('RGB',Image.open(os.path.join(self.path,'main.png')).size,(255,255,255))
      self.terrainfile = os.path.join(self.path,'main.png')
      temp.save(os.path.join(self.path,'terrain.png'),'PNG')
    self.terrainfile = 'terrain.png'
      
    # Frictions
    self.frictions[''] = {}
    for i in self.code_terrain:
      self.frictions[''][i] = 1.0
      
    # Infrastructure file
    self.infrastructurefile = os.path.join(self.path,'infrastructure.xml')
      
    # TODO, write as a XML instead.
    # Create the data and fill in with default values
    if not os.access(os.path.join(self.path,'main.xml'),os.F_OK):
      myfile = open(os.path.join(self.path,'main.xml'),'w')
      myfile.write(str(self.AsXML()))
      myfile.close()
      
    
    
  def GetClimate(self):
    return self.data['climate']
  
  def SampleTerrain(self, poly):
    '''! \brief Read the terrain under the polygon.
    '''
    # Bounding box
    box = poly.BoundingBox()
    minpoint = self.PixelCoord(vect_3D(box[0],box[1]))
    maxpoint = self.PixelCoord(vect_3D(box[2],box[3]))
    box = [minpoint[0], minpoint[1], maxpoint[0], maxpoint[1]]
    
    # If this is a very small footprint (1px)
    if minpoint == maxpoint:
      data = [self.terrain.getpixel(minpoint)]
    else:
      # Polygon
      mypoly = []
      for i in poly.vertices():
        pt = self.PixelCoord(i)
        mypoly.append( (pt[0]-minpoint[0], pt[1]-minpoint[1] ) )
  
      # Subset of data
      temp = self.terrain.crop(box).copy()
      
      # Mask (Negative of a mask)
      msk = Image.new('L',temp.size,color = 256)
      ImageDraw.Draw(msk).polygon(mypoly,fill=0,outline=0)
      voidcolor = (13,13,13)
      temp.paste(voidcolor,(0,0)+temp.size,msk)
      
      # Get the pixel data
      data = list(temp.getdata())
    
    # Extract the data
    out = {}
    for i in sandbox_map.code_terrain.values():
      out[tuple(i)] = 0
    
    for i in data:
      try:
        out[i] = out[i] + 1
      except:
        if i != voidcolor:
          pass
          #print i
        pass # Mask pixels 
    
    # Summarise
    tot = float(sum(out.values()))
    if tot != 0:
      for i in out:
        out[i] = out[i]/tot 
      
    # Clean list
    for i in out.keys():
      if out[i] == 0.0:
        del out[i]
        
    # Rebuild with string litterals
    final = {}
    for i in sandbox_map.code_terrain.keys():
      if sandbox_map.code_terrain[i] in out.keys():
        final[i] = out[sandbox_map.code_terrain[i]]
        
    if final == {}:
      final['off map'] = 1.0
      
    # return normalized sample
    return final
  
  def SampleTerrain_(self, pt, radius):
    '''!
       Read the terrain in a circle and integrate the data and returns a dictionary of terrain.
       pt --> vect_5D
       radius --> in Km
    '''
    # Bounding box
    c = self.PixelCoord(pt)
    r = max (1,int(radius * self.m))
    box = [c[0]-r,c[1]-r,c[0]+r,c[1]+r]

    # Subset of data
    temp = self.terrain.crop(box).copy()
    
    # Mask (Negative of a mask)
    msk = Image.new('L',temp.size,color = 256)
    ImageDraw.Draw(msk).ellipse(temp.getbbox(),fill=0,outline=0)
    voidcolor = (13,13,13)
    temp.paste(voidcolor,(0,0)+temp.size,msk)
    
    # Get the pixel data
    data = list(temp.getdata())
    
    # Extract the data
    out = {}
    for i in sandbox_map.code_terrain.values():
      out[i] = 0
    
    for i in data:
      try:
        out[i] = out[i] + 1
      except:
        if i != voidcolor:
          print i
        pass # Mask pixels 
    
    # Summarise
    tot = float(sum(out.values()))
    if tot != 0:
      for i in out:
        out[i] = out[i]/tot 
      
    # Clean list
    for i in out.keys():
      if out[i] == 0.0:
        del out[i]
        
    # Rebuild with string litterals
    final = {}
    for i in sandbox_map.code_terrain.keys():
      if sandbox_map.code_terrain[i] in out.keys():
        final[i] = out[sandbox_map.code_terrain[i]]
        
    if final == {}:
      final['off map'] = 1.0
      
    # return normalized sample
    return final
    
    
  def MeanFriction(self,poly, mode='LOS'):
    '''
       compute the mean friction in the polygon "poly"
    '''
    # Terrain profile
    terrain = self.SampleTerrain(poly)
    
    # Mean friction from terrain alone (no
    out = 0.0
    for i in terrain:
      out = out + (self.frictions[mode][i] * terrain[i])
    
    return out
  def Initialize(self):
    '''! \brief Read in the XML definition and take appropriate action
    '''
    if not os.access(os.path.join(self.path,'main.xml'),os.F_OK):
      raise 'InvalidMapDefinition'
    
    # Obtain XML
    doc = sandboXML(read=os.path.join(self.path,'main.xml'))
    
    # Load Graphics
    f = doc.Get(doc.root,'filename')
    if f:
      self.graphics = Image.open(os.path.join(self.path,f))
      self.graphicfile = os.path.join(self.path,f)
    
    # Load Terrain
    self.ParseXMLterrain( doc, doc.Get(doc.root,'terrain') )
        
    # Load friction data
    self.frictions = {'':{}}
    self.ParseXMLfrictions( doc, doc.Get(doc.root, 'friction') )

    # Metadata and linear parameters
    self.ParseXMLData(doc, doc.root)
    
    # Setup Flatland
    self.MGRS = sandbox_FlatLand()
    self.MGRS.Bind( self.data['ref XY'],self.data['ref coord'],)
    
    # Do we need to keep this?
    #self.copy = self.terrain.copy()
    #self.TerrainDraw = ImageDraw.Draw(self.copy)
    self.copy = self.TerrainDraw = None
    
  def ParseXMLData(self, doc, node):
    '''! \brief Metadata
       Load map data.
    '''    
    # Climate
    self.data['climate'] = doc.SafeGet(node, 'climate', self.data['climate'])
    
    # Width
    self.data['width'] = doc.SafeGet(node, 'width',self.data['width'])
    
    # ref coord
    self.data['ref coord'] = doc.SafeGet(node, 'ref_coord', self.data['ref coord'] )
    
    # ref XY
    self.data['ref XY'] = doc.SafeGet(node, 'ref_XY', self.data['ref XY'])
    
    # LatLon
    if doc.Get(node, 'LatLonQuad'):
      coord = doc.Get(doc.Get(node, 'LatLonQuad'), 'coordinates')
    
    self.LinearParameters()
 
  def ParseXMLfrictions(self, doc, node):
    if node:
      mds = doc.Get(node,'mode')
      if type(mds) != type([]):
        mds = [mds]
      # Find base mode (mandatory by definition)
      temp = {'':{},'sameas':{}}
      for i in mds:
        if doc.Get(i,'name') == 'base':
          base = {}
          for j in doc.Get(i,'terrain'):
            base[doc.Get(j,'name')] = float(j.childNodes[0].nodeValue)
          temp[''] = base
      
      # All modes of locomotion
      for i in mds:
        nm = doc.Get(i,'name')
        if nm == 'base':
          continue
        # Use as base either template or sameas attribute.
        if doc.Get(i,'sameas'):
          temp[nm] = deepcopy(temp[doc.Get(i,'sameas')])
          temp['sameas'][nm] = doc.Get(i,'sameas')
        else:
          temp[nm] = deepcopy(temp[''])
        # Update explicitely defined terms.
        for j in doc.Get(i,'terrain',True):
            temp[nm][doc.Get(j,'name')] = float(j.childNodes[0].nodeValue)
      
      # Update
      self.frictions = temp
  
  def ParseXMLterrain(self, doc, node):
    if node:
      h = doc.Get(node,'filename')
      self.terrain = Image.open(os.path.join(self.path,h))
      self.terrainfile = os.path.join(self.path,h)
      h = doc.Get(node,'class')
      for i in h:
        nm = doc.Get(i,'name')
        rgb = doc.Get(i,'color')
        self.code_terrain[nm] = rgb
    

    
  def FlushCache(self):
    del self.pathcache
    self.pathcache = PathCACHE(self.MGRS,os.path.join(self.path,'path_cache.dat'))

    
  def DrawCache(self):
    '''
       Draw all path in a terrain png
    '''
    for i in self.pathcache._paths.values():
      self.DrawPath(i[0])
      
    self.copy.show()
    

  
  def AsXML(self):
    '''! \brief A XML render of the map data.
    '''
    doc = sandboXML('map')
    root = doc.root
    
    # Name
    doc.AddField('name',self.mapenv, root)
    # filename
    fn = os.path.split(self.graphicfile)[-1]
    doc.AddField('filename',fn, root)
    # width
    doc.AddField('width',self.data['width'],root)
    # Climate
    doc.AddField('climate', self.data['climate'], root)
    # ref coord
    doc.AddField('ref_coord', self.data['ref coord'],root)
    # ref XY
    doc.AddNode(doc.write_vector_5D('ref_XY',self.data['ref XY']), root)
    
    # Terrain definition
    F = doc.NewNode('terrain')
    doc.SetAttribute('filename',os.path.split(self.terrainfile)[-1],F)
    for i in self.code_terrain:
      nn = doc.NewNode('class')
      doc.SetAttribute('name', i,nn)
      a = self.code_terrain[i]
      doc.AddField('color', '%d,%d,%d'%tuple(a), nn, 'RGB')
      doc.AddNode(nn,F)
    
    doc.AddNode(F,root)
    
    # Frictions
    ref = self.frictions['']
    fr = doc.NewNode('friction')
    for i in self.frictions:
      if i == 'sameas':
        continue
      if i == '':
        # base case
        nn = doc.NewNode('mode')
        doc.SetAttribute('name', 'base', nn)
        for j in self.frictions[i]:
          doc.AddField('terrain', str(self.frictions[i][j]),nn,name= j)
        doc.AddNode(nn, fr)
      else:
        nn = doc.NewNode('mode')
        doc.SetAttribute('name', i, nn)
        if i in self.frictions['sameas']:
          doc.SetAttribute('sameas', self.frictions['sameas'][i], nn)
          ref = self.frictions[ self.frictions['sameas'][i] ]
        else:
          ref = self.frictions['']
        for j in self.frictions[i]:
          if self.frictions[i][j] != ref[j]:
            doc.AddField('terrain', str(self.frictions[i][j]),nn,name= j)
        doc.AddNode(nn, fr)
        
    doc.AddNode(fr, root)
          
    
    return doc
    
  def PointOnMap(self, pt):
    '''
       Returns true if point is on map
    '''
    temp = self.PixelCoord(pt)
    if temp[0] >= 0 and temp[0] <= self.terrain.size[0] and temp[1] >= 0 and temp[1] <= self.terrain.size[1]:
      return True
    return False
  
  # Interface
  def FindPath(self, route, friction):
    '''
       The full routine and PathCACHING
       route must be a prepare list of vectors
    '''
    wp = route
    out = []
    i = 0
    while i < len(wp) -1:
      # Check the cache
      temp = self.pathcache.Query(wp[i],wp[i+1], friction)
      if temp == None:
          t = time()
          temp = self.KinkSegment(wp[i],wp[i+1], frict=friction)
          temp = self.OptimizePath(temp, frict=friction)
          dtime = time() - t
          # Cache the solution if the pathfinding took more than 0.5s
          if dtime > 0.5:
              self.pathcache.Add(temp,friction,dtime)
      if out:
          temp = temp[1:]
      out = out + temp
      i = i + 1
    return out
  
  def PathLength(self, path):
    '''
       Returns the physical distance in km
    '''
    out = 0.0
    cur = path[0]
    for i in range(len(path)):
      if i == 0:
        continue
      out = out + (cur-path[i]).length()
      cur = path[i]
    return out
      
    
  def EffectivePathLength(self, path, sample = 0.2, frict = Sf):
    '''
       Return a pathlength adjusted by friction.
       INPUT : path --> a list of waypoints
               sample --> the distance between samplses for friction.
               frict --> A vector of friction for the unit (default values)
       OUTPUT : the Adjusted distance in km
    '''
    # Sample the path finely
    allsamples = self.SamplePath(path, sample)
    
    # Sample frictions
    return self._effectivepathlength(allsamples, frict)
    
  
  def _effectivepathlength(self, allsamples, frict = Sf):
    '''
       Private methods that accepts samples instread of high level wp in km coord.
    '''
    sample = (allsamples[1]-allsamples[0]).length()
    frictions = []
    for i in allsamples:
      f = self.TerrainUnder(i)
      if frict[f]:
        frictions.append(sample * (1.0/frict[f]))
      else:
        frictions.append(sample * (1000000))
        
    return sum(frictions)
  
  def TerrainUnder(self, coord):
    '''
       Process any coordinate and return a terrain.
       INPUT : 
           coord --> in km coord
          return impasable if out of the map.
    '''
    # Slow implementation
    C = self.PixelCoord(coord)
    if not self.PointOnMap(coord):
      # Out of map
      mypix = (0,0,0)
    else:
      mypix = self.terrain.getpixel(C)
      if mypix == (0,255,0):
        print 1
    
    # Translate into string
    return self._terrainfrompixels(mypix)
  
  #
  # Arbitrary conventions  
  def _terrainfrompixels(self, pix):
    ''' 
       Tranlate color into a terrain
    '''
    for i in self.code_terrain.keys():
      t = self.code_terrain[i]
      if pix == t:
        return i
    return 'off map'
    '''
    if pix[0]:
      if pix[1]:
        if pix[2]:
          return 'unrestricted'
        return 'restricted'
      elif pix[2]:
        return 'urban'
      return 'severely restricted'
    if pix[2]:
      return 'water'
    return 'impassable'
    '''

  # PathFinding
  def OptimizePathSlide(self, path, frict = Sf):
    '''
       Optimize by sliding WP along segments
    '''
    i = 0
    while i+2 < len(path):
      temp = self.SlideMove(path[i],path[i+1],path[i+2],frict=frict)
      if temp == None:
        # remove path[i+1]
        path.remove(path[i+1])
        # Keep i unchanged
      else:
        index = path.index(path[i+1])
        path.insert(index, temp)
        i = i + 1
    return path
  
  def OptimizePath(self, path, frict = Sf):
    '''
       Take a path and optimize it.
       # Phase 1: remove long flat (friction) segements (greedy)
       # Phase 2: Remove neighbors on the basis of Effective length of segements (N^2).
    '''
    # Streamline path by removing nodes whic aren't improving the effective length of the path if removed
    mytime = time()
    while time() < mytime + 60.0:
      # Whole path
      whole = self.EffectivePathLength(path, frict = frict)
      i = 0
      bestj = None
      best = [-1,-1,0]
      while i < len(path)-2:
        j = i + 2
        while j < len(path)-1:
          multi = self.EffectivePathLength(path[i:j+1], frict = frict)
          direct = self.EffectivePathLength([path[i], path[j]],frict = frict)
          #direct = self.EffectivePathLength(self.KinkSegment(path[i], path[j], frict=frict),frict = frict)
          if ((multi - direct) > best[2] ):
              # We have a potential location of deletion
              # Need at least a 1% improvement
              if (multi-direct)/whole > 0.01:
                best = [i,j, multi-direct,multi,direct]
          j = j + 1
        i = i + 1
  
      if best[2]:
        i = best[0]
        j = best[1]
        #print 'redo wp%d to %d with predicted benefit of %f'%(i,j,best[2])
        # Redo the path
        newpath = self.KinkSegment(path[i],path[j])
        #newpath = [path[i],path[j]]
        #print 'Optimized to %f, predicted to %f and originally %f'%(self.EffectivePathLength(newpath),best[4],best[3])
        # Replace the paths
        mynewpath = []
        cc = 0
        while path[cc] != newpath[0]:
          mynewpath.append(path[cc])
          cc = cc + 1
        mynewpath = mynewpath + newpath
        while path[cc] != mynewpath[-1]:
          cc = cc + 1
        cc = cc + 1
        while cc < len(path):
          mynewpath.append(path[cc])
          cc = cc + 1
        path = mynewpath
      else:
        return path
    
    '''    
    A = 0
    while A < len(path)-1:
      B = A + 2
      while B < len(path):
        sample, fr, mid = self.ProfileSegment(path[A],path[B],frict)
        if min(fr) != max(fr):
          if B - 1 >= A + 2:
            # flatten
            print "flatten", A, B
            path = path[:A+1]+path[B:]
          # Move to next neighbor
          break
        B = B + 1
      A = A + 1
    '''
    
    return path
  def SlideMove(self, wp1 , wp2, minpoint, cutoff = 0.2, frict = Sf):
    '''
       Attempt to slide a point along the wpX-minpoint segements to shorten the segment pair.
       May collapse minpoint if it turns out to be within cutoff of either wpX
    '''
    crosspath = self.SamplePath([wp1,minpoint]) + self.SamplePath([wp2,minpoint])
    changed = None
    mineflen = self.EffectivePathLength([wp1,minpoint,wp2], frict=frict)
    print (wp1-wp2).length()
    print 'Before: ', mineflen
    # First leg
    for point in range(len(crosspath)):
      eflen = self.EffectivePathLength([wp1,crosspath[point],wp2], frict=frict)
      if eflen < mineflen:
        mineflen = eflen
        minpoint = crosspath[point]
        changed = True

    # Output
    if (minpoint-wp2).length() < cutoff or (minpoint-wp1).length() < cutoff:
      print 'Collapse :', self.EffectivePathLength([wp1,wp2], frict=frict)
      return None
    print 'After: ', mineflen
    return minpoint
  
  def ThreePointsMin(self, beg, mid, end, frict):
    '''
       Try to minimize the lenght of beg-to-end by sliding mid.
    '''
    mineflen = eflen = self.EffectivePathLength([mid,beg], frict=frict) + self.EffectivePathLength([mid, end], frict=frict)
    minpoint = mid * 1.0
    crosspath = self.SamplePath([beg,mid])
    for point in crosspath[:-1]:
      eflen = self.EffectivePathLength([point,beg], frict=frict) + self.EffectivePathLength([point, end], frict=frict)
      if eflen < 0.99 * mineflen:
        mineflen = eflen
        minpoint = point
      else:
        pass #break
      crosspath = self.SamplePath([minpoint,end])
      for point in crosspath[:-1]:
        eflen = self.EffectivePathLength([point,beg], frict=frict) + self.EffectivePathLength([point, end], frict=frict)
        if eflen < 0.99 * mineflen:
          mineflen = eflen
          minpoint = point
        else:
          pass #break
      # Does all this made  difference?
      if (mid-minpoint).length() > 0.1:
        return minpoint
      else:
        return False
    
  def KinkSegment(self, wp1, wp2, cutoff = 0.2, frict = Sf):
    '''
       Take two points and find the best way to kink it by minimizing the effective distance.
    '''
    # Should we do it?
    if (wp1-wp2).length() < cutoff:
      #print 'too short to tesselate'
      return [wp1,wp2]
    before = self.EffectivePathLength([wp1,wp2],frict=frict)
    
    # do the dirty work!
    samples, fr, mid = self.ProfileSegment(wp1,wp2, frict)
    
    # Other chances to bail out
    if len(samples) == 2:
      return [wp1,wp2]
    # homogeneous path
    if min(fr) == max(fr):
      return [wp1,wp2]
    indexofmin = samples.index(mid)
    if indexofmin == 0 or indexofmin == len(samples)-1:
      # Should be obsolete
      print 'midpoint matches ends'
      print fr
      if len(samples) > 4:
        indexofmin = int(len(samples)/2.0)
      else:
        return [wp1,wp2]
    
    # Alright, do the dirty minimization!
    # +/- pi/2 from midpoint and over up to 2 segement lengths
    # Look for the minimum effective length
    minpoint = deepcopy(mid)
    mineflen = self._effectivepathlength(samples[:indexofmin+1],frict) + self._effectivepathlength(samples[indexofmin:],frict)
    # Bounding box
    topleft = self.KmCoord([0,0])
    lowright = self.KmCoord(self.terrain.size)
    
    # Search to the left, then right
    for myangle in [pi/-2.0, pi/2.0]:
      bearingfromwp1 = wp1.BearingTo(mid)
      endpoint = mid.ToBearing([bearingfromwp1[0] + myangle, self.pathspan*bearingfromwp1[1]])
      searchsamples = self.SamplePath([mid,endpoint])
      # Scan the range
      for point in searchsamples:
        # if not in map, quit
        if point.x < topleft[0] or point.x > lowright[0] or point.y < topleft[1] or point.y > lowright[1]:
          continue
        eflen = self.EffectivePathLength([wp1,point], frict=frict) + self.EffectivePathLength([point, wp2], frict=frict)
        if eflen < mineflen:
          # We have a new best path
          minpoint = point
          mineflen = eflen
          # If the path is as good as it get (give about 10% error), stop searching
          if (((minpoint-wp1).length() + (minpoint-wp2).length())/ mineflen)> 0.9:
            break
    
    # Case where path is a crossover between terrain deisgnation and there is nothing 
    # possible to make it better
    if (mid-minpoint).length() < cutoff:
      # count friction transition
      count = 0
      cfr = fr[0]
      for i in fr[1:-1]:
        if i != cfr:
          count = count + 1
          cfr = i
          if count > 2:
            break
      if count == 1:
        # Case of a transition
        # Set minpoint to the first point on the other side.
        newindex = 1
        while newindex < len(fr):
          if fr[newindex] != fr[newindex-1]:
            return [wp1,samples[newindex-1],samples[newindex],wp2]
          newindex = newindex + 1
      else:
        # Return the path as such
        return [wp1,wp2]
    # Try to shorten the two legs, greedily
    # From wp to minpoint 
    # to do only if minpoint isn't mid
    else:
      crosspath = self.SamplePath([wp1,minpoint])
      changed = None
      for point in crosspath[:-1]:
        eflen = self.EffectivePathLength([point,wp1], frict=frict) + self.EffectivePathLength([point, wp2], frict=frict)
        if eflen < 0.99 * mineflen:
          mineflen = eflen
          minpoint = point
          changed = True
        else:
          pass #break
      if 1:
        crosspath = self.SamplePath([wp2, minpoint])
        for point in crosspath[:-1]:
          eflen = self.EffectivePathLength([wp1,point], frict=frict) + self.EffectivePathLength([point, wp2], frict=frict)
          if eflen < 0.99 * mineflen:
            mineflen = eflen
            minpoint = point
            changed = True
          else:
            pass #break   
    
        
    # Proceed into recursion
    a = self.KinkSegment(wp1,minpoint, frict=frict)[:-1]
    b = self.KinkSegment(minpoint, wp2, frict=frict)

    # Streamline connection between segments (smooth path)
    if self.EffectivePathLength([a[-1],b[0]], frict=frict) > self.EffectivePathLength([a[-1],b[1]], frict=frict):
      b = b[1:]
    # Return the final path from wp1 to wp2
    after = self.EffectivePathLength(a+b,frict=frict)
    if after > before:
      return [wp1,wp2]
    return a + b

      
  # Private methods
  def SamplePath(self, path, sample = 0.2):
    '''!
       Convert a path so it loosely is made of waypoints of length = sample.
       \param path a list of waypoints
       \param sample [200m] distance between samples
       \return a list of points
    '''
    out = []
    
    if len(path) <= 1:
      return path
    
    index = 1
    while index < len(path):
      vec = path[index-1] - path[index]
      N = int(vec.length() / sample)
      if N == 0:
        return path
      temp = path[index]
      i = 0
      while i <= N:
        out.append(path[index] + vec * (i*(1.0/N)))
        i = i + 1
      index = index + 1
      
    return out
      
  def ProfileSegment(self, p1, p2, frict = Sf):
    '''
       Take a path of two points, sample it and return a list of frictions
       p1 and p2 must be in km!
    '''
    # sample the segment
    samples = self.SamplePath([p1,p2])

    # Get all friction factors
    fr = []
    for i in samples:
      tunder = self.TerrainUnder(i)
      if frict[tunder]:
        fr.append(1.0/frict[tunder])
      else:
        fr.append(1000000)
      
    # Too short
    if len(samples) == 2:
      return samples, fr, None # Will be ignored anyway
    elif len(samples) == 3:
      return samples, fr, samples[1]
      
    # Find the max
    mmax = max(fr[1:-1])
    
    # Count the max
    count = 0.0
    for i in fr[1:-1]:
      if i == mmax:
        count = count + 0.5
        
    # Midpoint
    count = int(ceil(count))
    
    # Find the midpoint's index
    for i in range(len(samples)):
      if fr[i] == mmax:
        # We really don't want to pick either end for this.
        if i == 0 or i == len(samples)-1:
          continue
        count = count - 1
        if count == 0:
          return samples, fr, samples[i]
    
    
  #
  # Initialize
  def LoadData(self, pname):
    '''
       Load the dictionary of data
    '''
    # Get the file
    try:
      myfile = open(os.path.join(self.path,'%s.wre'%(pname)),'rb')
      self.data = loads(myfile.read())
      myfile.close()
    except:
      print 'Creating datafile for new map.'
      myfile = open(os.path.join(self.path,'%s.wre'%(pname)),'wb')
      myfile.write(dumps({},HIGHEST_PROTOCOL))
      myfile.close()
    
  def LinearParameters(self):
    if self.data.has_key('width'):
      # Get width of map in pixels
      self.m = self.graphics.size[0] / self.data['width'] # In pixels per Km
    else:
      self.B = [0,0]
  
  #
  # Coordinates manips
  def DistanceInPixels(self, km):
    return km * self.m
  
  def PixelCoord(self, coord):
    '''
       Convert km into pixels
    '''
    return ( int((coord.x-self.B[0])*self.m) , int((coord.y-self.B[1])*self.m) )
  
  def KmCoord(self, coord):
    '''
       Pixels to Km
    '''
    return [ coord[0]/self.m + self.B[0]/self.m, coord[1]/self.m + self.B[1]/self.m ]


  def FromMGRS(self, mgrs):
    '''
       solve the (X,Y) from a mgrs coordinate
    '''
    return self.MGRS.AsVect(mgrs)
     
  # drawing routines
  def DrawWaypoint(self, coord):
    '''
       Draw a waypoint at coord [vect_5D]
    '''
    mypoint = self.PixelCoord(coord)
    bbox = [mypoint[0] - 5, mypoint[1] - 5, mypoint[0] + 5, mypoint[1] + 5]
    self.TerrainDraw.ellipse(bbox, fill=(0,255,0))
    
  def DrawEdge(self, P1, P2):
    mp1 = self.PixelCoord(P1)
    mp2 = self.PixelCoord(P2)
    self.TerrainDraw.line([mp1,mp2], fill=(0,255,0))
    
  def DrawPath(self, path):
    i = 0
    while i < len(path):
      self.DrawWaypoint(path[i])
      if i + 1 < len(path):
        self.DrawEdge(path[i],path[i+1])
      i = i + 1


    
  def DrawMGRSGrid(self):
    ''' Draw the MGRS grid on a copy of the graphics map and return the modified grid. '''
    # The surface
    mysurf = self.graphics.copy()
    # The DC
    gdraw = ImageDraw.Draw(mysurf)
    
    # The lower corner
    upc = self.MGRS.AsString(vect_5D(),res=2)
    lwc = self.MGRS.AsString(vect_5D(self.KmCoord(self.graphics.size)[0], self.KmCoord(self.graphics.size)[1]),res=2)
    
    # Iterators
    X = upc[-4:-2]
    Y = upc[-2:]
    gd = upc[-6:-4]
    
    lineX = []
    lineY = []
    
    # Lines in X
    x = X
    stub = upc[:-4]
    pixl = [0,0]
    while pixl[0] <= mysurf.size[0]:
      # Get the pixel coord for a given x
      pixl = self.PixelCoord(self.MGRS.AsVect(stub+x+'00'+Y+'00'))
      if pixl[0] < 0:
        pass
      else:
        # Store pixel in x + label
        lineX.append([pixl[0],x])
        
      # change x to next string
      x = ('0' + str(int(x) + 1))[-2:]
      # change grid ref 
      if x == '00':
        # Get A MGRS just right of line 
        v = self.KmCoord([pixl[0]+self.m+1,pixl[1]])
        stub = self.MGRS.AsString(v,res = 2)[:-4]
    
    y = Y
    stub = upc[:-4]
    pixl = [0,0]
    while pixl[1] <= mysurf.size[1]:
      # Get the pixel coord for a given x
      pixl = self.PixelCoord(self.MGRS.AsVect(stub+X+'00'+y+'00'))
      if pixl[1] < 0:
        pass
      else:
        # Store pixel in x + label
        lineY.append([pixl[1],y])
        
      # change x to next string
      y = ('0' + str(int(y) + 1))[-2:]
      # change grid ref 
      if y == '00':
        # Get A MGRS just right of line 
        v = self.KmCoord([pixl[0],pixl[1]+self.m+1])
        stub = self.MGRS.AsString(v,res = 2)[:-4]
        
    # Draw the buggers
    mX = mysurf.size[0]
    mY = mysurf.size[1]
    for i in lineX:
      if int(i[1]) % 10 == 0 and i[1] != '00':
        gdraw.line([i[0],0,i[0],mY], fill=(250,255,10))
      elif i[1] != '00':
        gdraw.line([i[0],0,i[0],mY])
      else:
        gdraw.line([i[0],0,i[0],mY], fill=(250,10,10))
      
    for i in lineY:
      if int(i[1]) % 10 == 0 and i[1] != '00':
        gdraw.line([0 ,i[0] ,mX ,i[0]], fill=(250,255,10))
      elif i[1] != '00':
        gdraw.line([0 ,i[0] ,mX ,i[0]])
      else:
        gdraw.line([0 ,i[0] ,mX ,i[0]], fill=(250,10,10))
        
    mysurf.show()
    return mysurf
    
class PathCACHE:
  def __init__(self, translator, fname=''):
    # The MGRS-base mapping structure key = MGRS
    self._key = {} # MGRS as key
    # The data
    self._paths = {} # ID as Keys
    # The file location
    self._archive = fname
    # Translator
    self.translator = translator
    # ID cursor
    self.cursor = 0
    
  def Add(self, path, friction, dtime):
    '''
       Add a path to the instance.
       This path is conditional to a friction dictionary.
       The time required to solve this path is also stored to be used later for pruning.
    '''
    # Begin
    begin = self.translator.AsString(path[0],2)
    end = self.translator.AsString(path[-1],2)
    
    # Make sure it doesn't exist
    temp = self.Query(path[0], path[-1], friction)
    
    if temp == None:
      # Add the path
      self._paths[self.cursor] = [path,friction,1,dtime]
      
      # Default
      if not self._key.has_key(begin):
        self._key[begin] = []
      if not self._key.has_key(end):
        self._key[end] = []
        
      # Add the keys
      self._key[begin].append(self.cursor)
      self._key[end].append(self.cursor)
      
      # update cursor
      self.cursor = self.cursor + 1
      return True
    return False
  
  def Query(self, begin, end, friction):
    '''
       Return a Path or None
    '''
    # Begin
    try:
      lbegin = self._key[self.translator.AsString(begin,2)]
    except:
      return None
    # End 
    try:
      lend = self._key[self.translator.AsString(end,2)]
    except:
      return None
    
    # Find a mathing pair
    soln = None
    for b in lbegin:
      for e in lend:
        if b == e:
          if self._paths[b][1] == friction:
            mypath = self._paths[b][0]
            self._paths[b][2] = self._paths[b][2] + 1
            # Determine the direction
            pbegin = self.translator.AsString(mypath[0],2)
            if pbegin == self.translator.AsString(begin,2):
              return mypath
            else:
              mypath.reverse()
              return mypath
    return None
  
  def Prune(self, N = 1000):
    ''' 
       Delete such that there is only N path.
    '''
    # Don't bother for less than N
    if len(self._paths) < N:
      return False
    
    # List all saved time values
    T = []
    for f in self._paths.keys():
      i  = self._paths[f]
      T.append(i[2]*i[3])
      # Decay the benefit of existing path to get a chance of getting rid of long old paths
      i[2] = i[2] * 0.8
    T.sort()
    
    cutoff = T[999]
    
    # Remove all path ID which are less than the cutoff (may delete less than needed, oh well...)
    to_delete = []
    for i in self._paths.keys():
      t = self._paths[i]
      if t[2]*t[3] < cutoff:
        to_delete.append(i)
        
    # remove all relevant path
    for i in to_delete:
      self.Remove(i)
      
  def ClearAll(self):
    for i in self._paths.keys():
      self.Remove(i)
      
  def Remove(self, ID):
    beg = self.translator.AsString(self._paths[ID][0][0],2)
    end = self.translator.AsString(self._paths[ID][0][-1],2)
    
    # remove map in _key
    self._key[beg].remove(ID)
    self._key[end].remove(ID)
    
    if len(self._key[beg]) == 0:
      del self._key[beg]
    if len(self._key[end]) == 0:
      del self._key[end]
    
    del self._paths[ID]
      
      
  def Save(self):
    '''
       Save.
    '''
    # Clean up just in case
    self.Prune()
    # Save
    fh = open(self._archive,'wb')
    fh.write(dumps([self._key,self._paths,self.cursor],HIGHEST_PROTOCOL))
    fh.close()
  
  def Load(self):
    try:
      fh = open(self._archive,'rb')
      dat = loads(fh.read())
      self._key = dat[0]
      self._paths = dat[1]
      self.cursor = dat[2]
    except:
      self.Save()
      #fh = open(self._archive,'w')
      #fh.close()
  
    



from random import random
CASE = 'DATA'
if __name__ == '__main__':
  if CASE == 'DATA':
    mymap = sandbox_map('Anzio')
    
  if CASE == 'UTMGRID':
    mymap = sandbox_map('Anzio')
    mymap.DrawMGRSGrid()
  
  if CASE == 'MGRS':
    # Testing the MGRS tranlator
    a = mgrs_translator('18SUU836014',vect_5D())
    print a.AsString(vect_5D()), a.AsVect(a.AsString(vect_5D()))
    print a.AsString(vect_5D(100,0)), a.AsVect(a.AsString(vect_5D(100,0)))
    print a.AsString(vect_5D(-300,0),2), a.AsVect(a.AsString(vect_5D(-300.0)))

  if CASE == 'PATHFINDING':
    mymap = sandbox_map('Anzio')
    
    # Points to join
    d = mymap.KmCoord([682,289])
    c = mymap.KmCoord([644,158])
    c = vect_5D(c[0],c[1])
    d = vect_5D(d[0],d[1])
    p = mymap.KinkSegment(c,d)
    print mymap.EffectivePathLength(p)
    o = mymap.OptimizePath(p)
    print mymap.EffectivePathLength(o)
    #o = mymap.OptimizePathSlide(o)
    #print mymap.EffectivePathLength(o)
    #mymap.DrawPath(p)
    mymap.DrawPath(o)
    mymap.copy.show()