'''!
        Sandbox Graph -- Abstract Discrete structure
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
class G:
    '''! \brief Basic Graph's methods.
          The attribute V is a dictionary of vertices indexed by a string name.
          The attribute E is a list of edges.
          self.directed is a BOOL flag indicating that the order of the v in a edge matters
          _vertex is a pointer to the class for this graph's vertices
          _edge is a pointer to the class for this graph's edge.
    '''
    def __init__(self,V={}, E=[]):
        self.V = V
        self.E = E
        self.directed = False
        
        self._vertex = vertex
        self._edge   = edge
        
        # Options for filtering neighbor nodes
        self.SOURCE = 1
        self.DESTINATION = 2
        
    # Low-level Access - Information
    def Vertex(self, v):
        '''! \brief Retrieve the vertex of name v, if v is a node, return v back.
        '''
        if type(v) == type(''):
            if v in self.V:
                return self.V[v]
            else:
                return None
        else:
            return v
        
    def Edge(self, v1, v2):
        '''! \brief Retrieve an edge from two nodes Consider direction if applicable.
             \return a edge or None
        '''
        # Get underlying node if necessary
        v1 = self.Vertex(v1)
        v2 = self.Vertex(v2)
        
        # Fetch all edges from v1
        out = self.Edges(v1)
        for i in out:
            if v2 in i:
                if i.directed:
                    if v2 == i[1]:
                        return i
                return i
        return None
    
    def Edges(self, v):
        '''! \brief Returns all edges connected to vertice v.
        '''
        v = self.Vertex(v)
        if not v.name in self.V:
            raise 'VerticeNotFound'

        out = []
        for i in self.E:
            if v in i:
                out.append(i)
        return out

    def Neighbors(self, v, direction=False):
        '''! List all vertices that v is connected from v.
             \todo Better performance with sorted list of vertices.
        '''
        e = self.Edges(v)

        out = []
        for i in e:
            # Ignore wrong arrow in directed graphs.
            if i.directed and direction:
               if direction == self.SOURCE:
                   if v == i[0]:
                       continue
               elif direction == self.DESTINATION:
                   if v == i[1]:
                       continue
            out.extend(i)
        out = set(out)
        try:
            out.remove(v)
        except:
            pass
        return list(out)
    
    # Add/remove
    def AddVertex(self, v):
        if not isinstance(v, vertex):
            v = self._vertex(v)
        if not v.name in self.V:
            self.V[str(v.name)] = v
            return v
        return False

    def AddEdge(self, v1, v2, glenght=1, directed = False):
        # Add Vertices, if necessary.
        temp = self.Vertex(v1)
        if not temp:
            v1 = self.AddVertex(v1)
        else:
            v1 = temp
        temp = self.Vertex(v2)
        if not temp:    
            v2 = self.AddVertex(v2)
        else:
            v2 = temp
        
        # Retrieve edge to assert existance
        e = self.Edge(v1,v2)
        if not e:
            self.E.append(self._edge(v1,v2, glenght, directed))

    

    def Remove(self, v1, v2=None):
        '''\brief Remove according to the following rules:
           \param v2 A vertex/string, remove the edge v1,v2
           \param v1 A vertex/string or edge, remove the vertex or edge
        '''
        if v2 != None:
            e = self.Edge(v1, v2)
            if e:
                return self.RemoveEdge(e)
            else:
                raise 
                
        if isinstance(v1, self._edge):
            return self.RemoveEdge(v1)
        else:
            return self.RemoveVertex(v1)
    
    def RemoveVertex(self, v1):
        ''' \brief remove vertex and all adjacent edges
        '''
        v1 = self.Vertex(v1)
        if v1 == None:
            raise
        
        for i in self.Edges(v1):
            self.RemoveEdge(i)
            
        del self.V[v1.name]
    
    def RemoveEdge(self, e):
        '''\brief Remove an edge'''
        self.E.remove(e)
        
    # Algorithm
    def Path(self, v1, v2):
        '''! \brief DP solution using edge distance method if available.
             \todo Implement two-ended search for better efficiency.
        '''
        # typing
        v1 = self.Vertex(v1)
        v2 = self.Vertex(v2)
        
        # Case 1 - destination same as start, return 1-element path
        if v1 == v2:
            return [v1]

        # dict keeps track of distance to v1 node and last node to get to it.
        s = {v1:[0,v1]}
        bestdist = None
        newnodes = [v1]
        while newnodes:
            for i in newnodes:
                # Get all neighbors
                temp = self.Neighbors(i, self.DESTINATION)
                # Get current best distance to node i
                bdist = s[i][0]
                
                # If i is no longer an option, delete it
                if bestdist != None and bdist > bestdist:
                    del s[i]
                    continue
                
                # Iterate over all neighbors
                for j in temp:
                    e = self.Edge(i,j)
                    # Get New distance
                    edist = bdist + e.Length()
                    # If new path is crappy, ignore. 
                    if bestdist != None and edist > bestdist:
                        continue
                    # If j doesn't exist in the solution space, add it.
                    if not j in s.keys():
                        s[j] = [edist,i]
                        newnodes.append(j)
                    # If there is a shorter way to get to j, update.
                    elif edist < s[j][0]:
                        s[j] = [edist,i]
                        newnodes.append(j)
                        
                    # remembers shortest path distance
                    if j == v2:
                        if bestdist == None:
                            bestdist = edist
                        else:
                            if edist < bdist:
                                bestdist = edist
                # Is this buggy?
                newnodes.remove(i)
                
                if v2 in newnodes:
                    newnodes.remove(v2)
        
        # Reconstitute the path by creeping up the chain.
        if v2 in s.keys():
            out = [v2]
            cursor = v2
            while cursor != v1:
                out.insert(0,s[cursor][1])
                cursor = s[cursor][1]
            return out
        else:
            # No path
            return None
                    
    
    def Distance(self, v1, v2 = None):
        '''! \brief Undirected graph distance by default.
              Rely on path routine.
              \param v2 If none, assumes that v1 is a list of nodes forming a path.
        '''
        if v2 != None:
            path = self.Path(v1,v2)
        elif type(v1) == type([]):
            path = v1
            
        # Add distances
        d = 0.0
        for i in range(len(path)-1):
            d += self.Edge(path[i],path[i+1]).Length()
        return d

    # Output
    def ToDot(self, fname):
        '''! \brief Make Dot file which can render the network with GraphViz.'''
        out = 'graph MyNet {\n'
        
        for e in self.E:
            out += '\t\"%s\" -> \"%s\";\n'%( e[0].name , e[1].name )
        
        out += '}\n'
        # Write to file
        f = open(fname, 'w')
        f.write(out)
        f.close()
        
class vertex:
    '''! \brief Basic vertex object implementation
    '''
    def __init__(self, name = ''):
        self.name = name
        
class edge(list):
    '''! \brief Basic Edge information
    '''
    def __init__(self, begin, end, length=1, directed = False):
        self.append(begin)
        self.append(end)
        self.length = length
        self.directed = directed
    
    def Length(self):
        return self.length
    
if __name__ == '__main__':
    a = G()
    a.directed = True
    a.AddEdge('A','B',2)
    a.AddEdge('A','C',3)
    a.AddEdge('B','D',4)
    a.AddEdge('C','B',1, directed=True)
    x = a.Path('A', 'D')
    y = a.Path('B','C')
    print a