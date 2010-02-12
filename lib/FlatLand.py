'''
   Conversion of coordinates from decimal LatLong, UTM and MGRS zone.
   
   Limitation: doesn't do UPS so do not venture above lat +84 and below Lat -80.
   
   Contact:
   Python reimplementation including the MGRS conversion by Christian Blouin <cblouin @ cs dal ca>
   
   Credits: 
   C code written by Chuck Gantz- chuck.gantz@globalstar.com
   Original python port for all but MGRS stuff Converted to Python by Russ Nelson <nelson@crynwr.com>
   
   Reference ellipsoids derived from Peter H. Dana's website- 
   http://www.utexas.edu/depts/grg/gcraft/notes/datum/elist.html
   Department of Geography, University of Texas at Austin
   Internet: pdana@mail.utexas.edu
   3/22/95
   
   Source
   Defense Mapping Agency. 1987b. DMA Technical Report: Supplement to Department of Defense World Geodetic System
   1984 Technical Report. Part I and II. Washington, DC: Defense Mapping Agency
   
   Interfacing with the Translator
   
   LonLat
         1 - as a list of decimal longitude, latitude
         2 - Degrees[d], Minute['] [seconds]["] Degrees[d], Minute['] [seconds]["]
   UTM
         1 - 18T 1111111.0 1111111.0
   MGRS 
         1 - 18T UF 23232323
         2 - 18TUF23232323
         
   License and notes:
         This code is distributed under a GPL license (http://www.gnu.org/licenses/gpl.txt for modalities). It was written as
         an utility for a game/simulator project. It is NOT intended for real world navigation, although it probably is good 
         enough for as long as you stay firm within the UTM region (Lat -80 to Lat +84). Anyone want to implment the UPS coordinate
         system?
         
         Please let me know if you use this code, and whether you have found bugs into it!
         
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

from CoordConverter import CoordTranslator

from vector import *

from copy import copy
        
    
class FlatLand(CoordTranslator):
    '''! \brief FlatLand is an attempt to project the earth into a 2D world.
               
         The XY coordinate system is made of a UTMzone and is using vect_XD internal data, Easting and Northing in a continuous axis, centered at the false meridian
         and the equator.
    '''
    def __init__(self, ellipsoid = 23):
        # The base class
        CoordTranslator.__init__(self, ellipsoid)
        
        # The specifics of FlatLand
        # XY coordinates for different UTM zones
        self.refpoint = {}
        
        # In meter
        self._equatorialCircumference = 40075.16 * 1000
        self._zonewidth = self._equatorialCircumference / 60.
        
    # Operate on internal coordinates only
    def UTMtoXY(self, utm, useref = True):
        '''! \brief Convert Northing to a XY system.
        '''
        # Make sure that utm is in internal structure.
        utm = self.AsUTM(utm,internal=True)
        N = utm[3]
        E = utm[2]
        
        if self._NSzones.find(utm[1]) < self._NSzones.find('N'):
            N =  N - 10000000.0
            
        if useref and self.refpoint:
            if utm[0] == self.refpoint.keys()[0]:
                out = vect_5D(E,N) - self.GetOffset()
            else:
                # recast from refpoint 1
                nref = self.refpoint.keys()[0]
                utm1 = self.RecastMeridian(nref,utm)
                return self.UTMtoXY(utm1)
        else:
            out = vect_5D(E,N)
        
        
        return out
    
    def XYtoUTM(self, XY, internal = False):
        '''! \brief Build a UTM coordinate (internal data) from XY (vect_5D) and a zone.
        
             \todo Catch the case where a XY is in a referencial for which there is no refpoint. Until this is done, 
             don't delete any refpoint nor manually assign reference to a vector.
        '''
        # Cannot execute if unbound.
        if len(self.refpoint) == 0:
            return None
        
        zone = self.refpoint.keys()[0]
        
        XY = XY + self.GetOffset()
        
        if XY.y < 0.0:
            XY.y = 10000000. + XY.y
            south = True
        else:
            south = False
            
        # Find the subzone
        if south:
            for c in self._NSzones:
                span = self._AllowedNorthingFromZone(c)
                if XY.y >= span[0] and XY.y < span[1]:
                    subzone = c
                    break
        else:
            for c in self._NSzones[10:]:
                span = self._AllowedNorthingFromZone(c)
                if XY.y >= span[0] and XY.y < span[1]:
                    subzone = c
                    break
        
        if internal:
            return [ zone, subzone, XY.x, XY.y ]
        else:
            # Get UTM
            out = self.ValidateUTM(self.AsUTM([ zone, subzone, XY.x, XY.y ],internal = True))
            return self.AsUTM(out)
        
    
    def ValidateUTM(self, utm):
        '''! \brief Make sure that the UTM coordinate is valid (right zone and False Easting).
        '''
        # Convert to LL
        LL = self.UTMtoLL(utm)
        return self.LLtoUTM(LL)
        
    # Setup
    def Bind(self, XY, coord):
        '''! \brief Find the XY coordinate for the intersection of a zone's meridian and the equator. The axis of the
             coordinate system is oriented as per the Northing in the norther hemisphere.
             
             coord must be a valid LL (string DMS or Decimal list), UTM or MGRS (string)
        '''
        # Get the Coord into UTM
        temp = self.ParseCoord(coord)
        if temp[1] == 'Invalid':
            raise 'Invalid Coordinates'
        
        # Conversion to UTM
        if temp[1] == 'LL':
            coord = self.LLtoUTM(temp[0])
        elif temp[1] == 'MGRS':
            coord = self.MGRStoUTM(temp[0])
        elif temp[1] == 'UTM':
            coord = temp[0]
        
        # Forget previous refpoint (if any)
        self.refpoint.clear()
            
        # Jiggle the Northing component to UTM' system.
        xy = self.UTMtoXY(coord)
        
        # Substract point offset to get xy @ flatland origin in UTM' coordinate space.
        xy = xy - XY
            
        # Store up to 1 refpoint per UTM zone.
        self.refpoint[int(coord[0])] = xy
        
    # Private methods
    def GetOffset(self):
        '''! \brief Return the vector setting the offset of a zone to the flatland origin.
        '''
        if self.refpoint:
            return self.refpoint.values()[0] 
        
        # All else fails
        return vect_5D()
    
    def RecastMeridian(self, newzone, utm):
        '''! \brief Force the false Easting of utm to be set toth central meridian to the sector newzone.
        
             Expect distortion due to error on the computation of the latitudinal small circle as well as, apparently, floating point
             precision issue (maybe just a small circle issue).
             
             A backhanded correction is applied to preseve the global position of Recast coordinates (see last few lines of method).
        '''
        # SHortest offset
        O = int(utm[0])
        N = newzone
        
        # diff is the number of zone from N
        diff  = O - N
        # diff2 is the other way around 
        diff2 = diff + (abs(diff)/diff) * -60
        
        # Shortest way (set diff2 as shortest if appropriate
        if abs(diff) > abs(diff2):
            diff = diff2
            
        # Offset at equator
        diff = diff * self._zonewidth
        
        # Latitude of utm
        Lat = self.UTMtoLL(utm)[0]
        
        # Modified offset with latitude
        diff *= cos(radians(Lat))
        
        # Residual vector along Lat line for point within original zone
        res = utm[2] - 500000.
        
        # New Offset is made of meridian in new zone + diff + residual (unmod by lat)
        newE = 500000. + diff + res
        
        # Replace zone and Easting and return
        out = copy(utm)
        out[0] = newzone
        out[2] = newE
        
        # Correction to remove distortion
        utm3 = self.ValidateUTM(out)
        out[2] -= (utm3[2]-utm[2])
        
        return out
        
if __name__ == '__main__':
    # Create an instance of FlatLand
    a = FlatLand()
    
    # Get The UTM internal data structure
    utm = a.AsUTM([-10., .1], True)
    
    # The XY value is out of left field here because the UTM zone hasn't been bound to FlatLand
    print a.UTMtoXY(utm)
    
    # Bind such that utm is really (100,50) in FlatLand
    a.Bind(vect_5D(100,50),utm)
    
    # Feels better
    print a.UTMtoXY(utm)
    
    # Get a UTM from a flatland coordinate
    print a.XYtoUTM(vect_5D(100,100))
    
    utm2 = a.RecastMeridian(30,utm)
    # 
    print a
