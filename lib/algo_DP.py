'''!
        Dynamic Programming - Generic algorithm
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
from copy import deepcopy

class Dynamic_Programming:
    '''! Assume a minimization of the cost! Not an optimization of the score!
       
         This isn't a generic, standard implementation of Needleman-Wunch. Use only if you know why you need it.
    '''
    def __init__(self, gap_open = 1.0, gap_extension = 0.0, max_gap = 1E10):
        self.go = gap_open
        self.ge = gap_extension
        self.maxgap = max_gap
        
    def Solve(self, S):
        '''! \brief return a list of pairs to be aligned.
             \param S A matrix of cost scores.
        '''
        # Copy the matric
        M = deepcopy(S)
        P = deepcopy(S)
        
        # Accumulate the matrix
        for y in range(len(M[0])-2,-1,-1):
            for x in range(len(M)-2,-1,-1):
                if abs(x-y) > self.maxgap:
                    M[x][y], P[x][y] = None, None
                else:
                    M[x][y], P[x][y] = self.Square(x,y, M, S)
                    
        # Find path starts
        sp = []
        for row in range(len(M)):
            if M[row][0] != None:
                sp.append([row,0])
        for col in range(len(M[0])):
            if M[0][col] != None:
                sp.append([0,col])
        
        # Find best path
        mpi = 0
        for i in range(len(sp)):
            if M[sp[i][0]][sp[i][1]] < M[sp[mpi][0]][sp[mpi][1]]:
                mpi = i
           
        # Return path
        return self.Path(sp[mpi][0], sp[mpi][1], M, P )
            
    def Square(self, i, j, M, S):
        '''! \brief Return the best score for i,j in M, given the gap penalties defined in the instance.
        '''
        out = []
        # Direct increment
        out.append([S[i][j] + M[i+1][j+1],(i+1,j+1)])
        
        # Row
        if j+1 != len(M[0]):
            for k in range(len(M[i+1][j+1:])):
                if M[i+1][j+k] == None:
                    continue
                out.append([self.go +  S[i][j] + (k * self.ge) + M[i+1][j+k], (i+1,j+k)]  )
        
        # Column
        if i+1 != len(M):
            for k in range(len(M)-(i+1)):
                if M[i+k][j+1] == None:
                    continue
                out.append([self.go + S[i][j] + (k * self.ge) + M[i+k][j+1], (i+k,j+1)])
                
        return min(out)
    
    def Path(self, i, j, M, P):
        '''! \brief Trace a path and return it as a list of list, as well as the final score
        '''
        out = [[i,j]]
        while i < len(M[0]) and j < len(M):
            if type(P[i][j]) == type(1) or type(P[i][j]) == type(1.0):
                break
            i, j = P[i][j][0], P[i][j][1]
            out.append([i,j])
        return out
        
    
    
if __name__ == '__main__':
    a = [[0,1,2,3],[0,2,1,2],[1,0,1,2],[3,2,1,0],[3,3,1,1]]
    b = Dynamic_Programming(1,0.5,1)
    x = b.Solve(a)
    
    for i in x:
        print i
        