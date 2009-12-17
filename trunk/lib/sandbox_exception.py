'''!
        Exception  -- Exception data structure
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

class SandboxException(Exception):
    def __init__(self, name, data=None):
        Exception.__init__(self)
        self.name = name
        self.data = data