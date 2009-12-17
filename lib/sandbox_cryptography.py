'''
    Encrypt module : Simple and not so secure, but OK for obfuscating strings.
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

from operator import xor

def Encrypt(msg,key):
        '''! Simple encryption using the XOR technique. Decrypt by simply encrypting 
        an encrypted string while using the same key.
        '''
        out = ''
        a = len(key)
        for i in range(len(msg)):
                out = out + chr(xor(ord(msg[i]),ord(key[i%a])))
        return out