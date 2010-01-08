'''!
        Sandbox Infrastructure -- Definition of infrastructure within the Sandbox world
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

# For unit testing only
if __name__ == '__main__':
    import syspathlib
    
# import section
from sandbox_graph import *
from sandbox_XML   import *
from sandbox_geometry import geometry_rubberband, base_polygon
from sandbox_position import position_descriptor

import FlatLand

import os.path
import os

class sandbox_node(vertex):
    '''! \brief Data structure to store a location/area in the simulated environment.
    
         templatename --> The name of the template [string] to reconstitute the structure of the node if needed.
         infrastructure --> A list of infrastructure instances contained within the node.
         coordinates --> A string litteral of the coordinate of the node, if available.
    '''
    def __init__(self, name=''):
        vertex.__init__(self, name)

        # Find the right template by name
        self.templatename = ''
        
        # List of structure present in the node.
        self.infrastructure = []
        
        # Coordinate position
        self.coordinate = None
        self.kind = ''
    
    def fromXML(self, doc, node):
        '''! \brief Load Data from XML.
        '''
        # templating
        
        # name
        if doc.Get(node, 'name'):
            self.name = doc.Get(node,'name')
        # kind
        if doc.Get(node, 'kind'):
            self.kind = doc.Get(node, 'kind')
        # Coordinates
        self.coordinate = doc.Get(node, 'coord')
        
        # Infrastructure
        for i in doc.Get(node, 'infrastructure', True):
            infra = sandbox_infrastructure()
            infra.fromXML(doc, i)
            self.infrastructure.append(infra)
        
    
    
    # Information
    def Instrastructures(self):
        '''! \brief return a list of infrastructure
        '''
        return self.infrastructure
    
    def Coordinates(self):
        '''! \return the coordinate of a node
        '''
        return self.coordinate
    
    def AsArea(self):
        '''! \brief Return the area which is the union of all infrastructure's footprint.
        '''
        out = []
        for i in self.Instrastructures():
            out.extend(i.vertices())
        if out:
            a = base_polygon(geometry_rubberband().Solve(out))
            b = a.Centroid()
            return position_descriptor(b.x, b.y, a)
        else:
            return None
    
    # Game progress
    def Step(self, pulse):
        '''! \brief implement a step routine for nodes.
        '''
        pass
    
class sandbox_edge(edge):
    '''! \brief An edge in the graph, sandbox-style.
    '''
    def __init__(self, begin, end, length = 0.0, pathname='', gtype='road'):
        edge.__init__(self, begin, end, length)
        self.pathname = pathname
        self.type = gtype
        
class sandbox_infrastructure(dict):
    '''! \brief Data structure to store the nature and details of an infrastructure.
    '''
    def __init__(self):
        # name
        self.name = ''
        # Footprint
        self.footprint = None
        
        # Size (H4 targetting [vsmall, small, medium, large, vlarge] )
        self.size = 'small'
        
        # Damage points (H$)
        self.DP = 1
        
        # Perimeter [none, hasty, prepared, hardened, fortified]
        self.perimeter = 'none'
        
        # Non-cargo capacity
        self.accomodation = 0
        self.parking = 0
        self.medical = 0
        self.mechanics = 0
        self.power = 0.0
        
        # LOGPAC values
        self.consumption = None
        self.capacity = None
        self.cargo = None
        
        
        
    def fromXML(self, doc, node):
        '''!
        '''
        template = doc.Get(node,'template')
        if template:
            self.fromXML(doc,doc.infrastructure_templates[template])
        
        # Load Attributes
        for i in doc.AttributesAsDict(node):
            if i == 'template':
                continue
            self[i] = doc.Get(node,i)
            
        # Load Elements
        e = doc.ElementsAsDict(node)
        for i in e:
            self[i] = e[i]
        

class sandbox_path(dict):
    def __init__(self, name=''):
        self[name] = ''
        self.sequence = []
        
class sandbox_network(G):
    '''! \brief The network of nodes in a simulated world.
    
         This class implment a graph made of nodes (topological location) and interconnecting edges of various semantic types. The interface
         to the network is via XML files: which makes use of templates. The road edge type thus connect various nodes by means to transit across the 
         simulated environment. Other connections can be railroad, landline, secure landline, watermain, pipelines, powerlines, microwave beams, or less substancial
         connections such as radio contact or ethnic affiliations.
         
         A node is a vertex in the graph as well as a container for a list of infrastructure elements. Infrastructures elements are object in
         the world which possess either a strategic or tactical value to the completion of a scenario: building, installations, facilites. 
    '''
    def __init__(self):
        G.__init__(self)
        
        self.xmldoc = None
        
    # Input methods
    def LoadFromXML(self, x, node=None):
        '''! \brief Extract the data from an instance of sandboxXML.
        '''
        if node == None:
            node = x.root
        # Get Top node
        tag = node.tagName
        importer = '_Load%s'%(tag)
        if hasattr(self, importer):
            _fn = getattr(self, importer)
            _fn(x, node)
            
    def _Loadnetwork(self, doc, node):
        '''! \brief Load a network in the instance.
        '''
        # template
        templates = doc.Get(node,'templates','force_list')
        for ts in templates:
            for t in doc.Get(ts, 'infrastructure','force_list'):
                name = doc.Get(t,'name')
                doc.infrastructure_templates[name] = t
        # nodes
        nodes = doc.Get(node,'nodes',True)
        for ns in nodes:
            for n in doc.Get(ns,'node',True):
                n = self._Loadnode(doc, n)
                self.AddVertex(n)
        # routes
        routes = doc.Get(node,'roads',True)
        for rs in routes:
            for r in doc.Get(rs,'road',True):
                route = self._LoadRoute(doc, r)
                self.ThreadRoute(route)
        pass
            
    def _Loadnode(self, doc, node):
        '''! \brief Load a node
        '''
        # Create a node and parse data.
        temp = sandbox_node()
        temp.fromXML(doc, node)
        
        return temp
    
    def _Loadinfrastructure(self, doc, node):
        '''! \brief Create and return an instance of infrastructure.
        '''
        out = sandbox_infrastructure()
        return out
    def _LoadRoute(self, doc, node):
        '''!
        '''
        out = sandbox_path()
        # Route attributes
        temp = doc.AttributesAsDict(node)
        out.update(temp)
        
        # Route Sequence
        for n in doc.Get(node,'node',True):
            name = doc.Get(n,'name')
            if not name in self.V.keys():
                # Must add the node to the network
                if not doc.Get(n,'name') and doc.Get(n,'coord'):
                    doc.SetAttribute('name',doc.Get(n,'coord'),node)
                    name = doc.Get(n,'coord')
                nd = self._Loadnode(doc, n)
                self.AddVertex(nd)
            # Get Node
            out.sequence.append(self.Vertex(name).name)
        return out
    
    # Information methods
    #
    def GetNode(self, name):
        '''! \brief Return a node object, if it exist
        '''
        return self.Vertex(name)
    
    # Building methods
    def ThreadRoute(self, route):
        '''! \brief Add edges between linked nodes.
        '''
        calc = FlatLand.FlatLand()
        for i in range(len(route.sequence)-1):
            # empty edge
            v1 = self.Vertex(route.sequence[i])
            v2 = self.Vertex(route.sequence[i+1])
            e = sandbox_edge( v1, v2,1.,route['name'],'road')
            d = calc.HaversineDistance(v1.coordinate,v2.coordinate)
            e.length = d * route['curve'] * (1000.**-1)
            self.E.append(e)
# Test Units
import unittest

class InfrastructureTest(unittest.TestCase):
    
    def setUp(self):
        self.folder = os.getcwd()
        
        # Anzio infrastructure file
        self.anziofile = os.path.join(os.path.split(self.folder)[0], 'maps','Anzio','infrastructure.xml')
        
    def OpenFile(self, fname):
        return sandboXML(read=fname)
    
    def tearDown(self):
        pass
    
    def testReadAnzioFile(self):
        xml = self.OpenFile(self.anziofile)
        self.assertTrue(xml)
        
    def testParseAnzioFile(self):
        xml = self.OpenFile(self.anziofile)
        
        
        net = sandbox_network()
        net.LoadFromXML(xml)
        
        self.assertTrue(net)
        
    def testPathFinding(self):
        xml = self.OpenFile(self.anziofile)
        
        net = sandbox_network()
        net.LoadFromXML(xml)
        a = net.Path('Aprilia','Borgo Faiti')
        
        self.assertTrue(net)
        

#
#
if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(InfrastructureTest))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)