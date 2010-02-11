''' 
   Renderer to KML
   Christian Blouin (2010)
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

from pysmirk import *
from sandbox_map import sandbox_map

class KML_renderer:
    ''' Initialize the renderer with a map from the map folder. This is necessary for converting internal
        coordinates and RL ones.
    '''
    def __init__(self, mapname='blankworld'):
        # Instanciate the map
        self.map = sandbox_map(mapname)
        
    def WriteOverlay(self, overlay):
        ''' Convert an OPCON overlay to a sandboxKML structure.
        '''
        # Create the folder
        out = KMLFolder(overlay.name)
        
        # Write each items
        points = KMLFolder('DATUMS')
        lines  = KMLFolder('LINES')
        areas  = KMLFolder('AREAS')
        out.AddItem(points)
        out.AddItem(lines)
        out.AddItem(areas)
        
        flatland = self.map.MGRS
        for i in overlay.ListPoints():
            e = overlay.GetElement(i)
            # Get the external coordinates
            coord = flatland.AsLatLong(flatland.XYtoUTM(e.GetShape()))
            x = KMLIconPlacemark(e.name, coord[0], coord[1])
            points.AddItem(x)
            