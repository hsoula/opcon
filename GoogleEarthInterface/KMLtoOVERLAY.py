''' Convert all overlays in a KML file to a XML version of an OPCON overlay.
'''
import os
import os.path
import sys

# Get the OPCON libraries
temp = os.path.join(os.environ['OPCONhome'], 'lib')
if not temp in sys.path:
    sys.path.append(temp)

from pysmirk import *
from sandbox_graphics import *
from FlatLand import FlatLand
from vector import vect_3D

# class map
_classmap = {KMLPolygon:operational_area, KMLPoint:operational_point, KMLLineString:operational_line}
   
    
def SetupFlatLand(flat, coord):
    # Get the first coordinate
    if type(coord) == type([]):
        x = coord[0]
    else:
        x = coord
    
    flat.Bind(vect_3D(), x)
    
    
    

def KMLtoOVERLAY(ov):
    ''' create an overlay instance from a KML folder instance
    '''
    # Instanciate
    out = operational_overlay(ov.name)
    
    # Create a FlatLand instance
    flatland = FlatLand()
    unbound = True
    
    # Iterate over each item in ov
    for item in ov.items:
        # Get the appropriate OPCON class
        _myclass = _classmap[item.geometry.__class__]
        
        # Split the name
        gtype = item.name.split()[0]
        gname = item.name.split()[1]
        
        # Coordinates
        try:
            coordinates = item.geometry.outerBoundaryIs.coordinates.split()
        except:
            coordinates = item.geometry.coordinates.split()
        for i in range(len(coordinates)):
            x = float(coordinates[i].split(',')[0])
            y = float(coordinates[i].split(',')[1])
            coordinates[i] = [x,y]
            
        # Setup FlatLand with the first time
        if unbound:
            SetupFlatLand(flatland, coordinates)
            unbound = False
        
        # Case 1 a point
        if _myclass == operational_point:
            coordinates = flatland.UTMtoXY(flatland.LLtoUTM(coordinates[0]))
        else:
            for i in range(len(coordinates)):
                coordinates[i] = flatland.UTMtoXY(flatland.LLtoUTM(coordinates[i]))
        
        # Instanciate the overlay item
        ovitem = _myclass(gtype, gname, coordinates)
        
        # Add to the overlay
        out.AddElement(ovitem)
    
    # Cache the RL coordinates for all control points.
    out.ExternalCoordinates(flatland)
        
    return out
        
        
        
    
    
    
    
# Executable section
if __name__ == '__main__':
    
    # Check for the number of argument
    if len(sys.argv) < 3:
        print 'KMLtoOVERLAY.py infile.kml outfile.xml'
        sys.exit()
        
    # infile in KML format
    infile = sys.argv[1]
    
    # outfile in XML format (OPCON)
    outfile = sys.argv[2]
    
    # Get the document
    try:
        kml = sandboxKML(read=infile)
    except:
        print 'Error reading in the KML file.'
        
    # Open the output document
    out = sandboXML('OPCON')
    
    # Get the master overlay folder
    folders = kml.Get(kml.root, 'Folder', True)
    
    for folder in folders:
        if folder.name == 'OVERLAYS':
            for item in folder.items:
                if item.tag == 'Folder':
                    # Convert to an OPCON instance
                    overlay = KMLtoOVERLAY(item)
                    
                    # Write to XML
                    out.AddNode(overlay.toXML(out), out.root)
    
    
    # Write the output.
    with open(outfile,'w') as fout:
        fout.write(str(out))
    
    