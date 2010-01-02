'''!
        Sandbox XML -- XML interface to the Sandbox
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
import xml.dom.minidom as minidom
import re
from datetime import datetime
    
from vector import vect_5D
from logistics import supply_package
from intelligence import sandbox_contact
from sandbox_position import position_descriptor

class XMLParseError(Exception):
    def __init__(self, subtype='', data=''):
        Exception.__init__(self)
        self.message = subtype
        self.data = data
class sandboXML:
    def __init__(self, rootname=None, read = False):
        '''! Create a document with the root set to rootname '''
        if read:
            self.doc = minidom.parse(read)
            self.root = self.doc.firstChild
        else:
            self.doc = minidom.Document()
            self.root = self.doc.createElement(rootname)
            self.doc.appendChild(self.root)
            
        self.ints = re.compile('^\d+$')
        self.floats = re.compile('^\d*\.\d*$')
        self.datetimes = re.compile('^\d+/\d+/\d{4} \d{4}[:\d+]?$')
        
        self.infrastructure_templates = {}
        
    # INPUT methods
    def RootName(self):
        if self.root:
            return str(self.root.tagName)
        
    def SafeGet(self, node, tag='', defaultval=None):
        ''' Returns the value of the defaultval if the node doesn't exist'''
        x = self.Get(node, tag)
        if x != '':
            return x
        else:
            return defaultval
        
    def Get(self, node, tag='', force_list = False):
        '''! \brief Look for an attribute or element with the corresponding tag(s). Return a list of if there is multiple elements.
        '''
        E = [] #node.getElementsByTagName(tag)
        for i in node.childNodes:
            if i.nodeName == tag:
                E.append(i)
                
        # No tag Case
        if tag == '' and len(node.childNodes) == 1:
            if node.childNodes[0].nodeType == 3:
                return self.NumericalTypes(str(node.childNodes[0].nodeValue))
            
        if E:
            # Type 
            for i in range(len(E)):
                E[i] = self.AttemptTyping(E[i])
            if type(E) == type([]) and len(E) == 1 and not force_list:
                return E[0]
            return E
        A = self.NumericalTypes(node.getAttribute(tag))
        # force an empty list
        if force_list and type(A) != type([]):
            if A != '':
                A = [A]
            else:
                A = []
        return A
        
    def AttributesAsDict(self, node):
        out = {}
        al = node.attributes
        for i in range(al.length):
            out[al.item(i).name] = self.NumericalTypes(al.item(i).nodeValue)
        return out
        
    
    def ElementsAsDict(self, node):
        '''! \brief Return an index dictionary of elements.
        '''
        out = {}
        for i in node.childNodes:
            if i.nodeType == 1:
                out[i.nodeName] = self.AttemptTyping(i)
        return out
    
    def ElementAsList(self, node):
        '''! \brief Return a list of element nodes. Lower-level thatn ElementAsDict, but safer if there is more than one children with
             the same tagname.
        '''
        out = []
        for i in node.childNodes:
            if i.nodeType == 1:
                out.append(i)
        return out
        
    # Typing methods
    def AttemptTyping(self, node):
        '''! \brief Attempt to intepret the node and return a sandbox object.
        '''
        tp = self.Get(node, 'type')
        if hasattr(self, 'type_'+tp):
            # CAse where there is an explicit parser for a node based on the type attribute.
            _fn = getattr(self,'type_'+tp)
            return _fn(node)
        elif hasattr(self, 'type_'+node.nodeName):
            # For convenience, in case that the tag of the node correspond to a type.
            _fn = getattr(self,'type_'+node.nodeName)
            return _fn(node)
        elif len(node.childNodes) == 1 and node.childNodes[0].nodeType == 3 and not len(node.attributes):
            # If there is no children, text type and contain no attributes, treate as a potential string/numerical value.
            return self.NumericalTypes(node.firstChild.nodeValue.strip())
        return node
    
    def NumericalTypes(self, s):
        '''! \brief Attempt to automatically type a string as an integer or float.
        '''
        if self.ints.match(s):
            return int(s)
        elif self.floats.match(s):
            return float(s)
        return str(s)
    
    # Automatically type into sandbox objects
    def type_datetime(self, node):
        '''! \brief Return a datetime node. in format
              DD/MM/YYYY HHMM:SS
        '''
        out = str(node.childNodes[0].nodeValue).strip()
        if self.datetimes.match(out):
            out = out.replace('/',' ')
            out = out.replace(':', '')
            out = out.split()
            if len(out) != 5:
                out.append(0)
            dt = datetime(int(out[2]), int(out[1]), int(out[0]), int(out[3][:2]), int(out[3][2:]), int(out[4]))
            return dt
            
        else:
            raise 'XMLDateTimeInvalid', out
        
        
    def type_RGB(self, node):
        out = str(node.childNodes[0].nodeValue).strip().split(',')
        for i in range(len(out)):
            out[i] = int(out[i])
        return tuple(out)
    def type_LOGPAC(self, node):
        out = supply_package()
        out.fromXML(self, node)
        return out
    def type_runway(self, node):
        out = self.AttributesAsDict(node)
        return out
    def type_vect_5D(self, node):
        out = vect_5D()
        # This is weird, but it works.
        temp = [self.Get(node, 'x'), self.Get(node, 'y'), self.Get(node, 'z'), self.Get(node, 'rate'), self.Get(node, 'course')]
        for i in range(len(temp)):
            if temp[i] == '':
                temp[i] = 0.0
        out.x = temp[0]
        out.y = temp[1]
        out.z = temp[2]
        out.course = temp[3]
        out.rate = temp[4]
        return out
    
    def type_contact(self, node):
        '''! \brief Return an instance of contact from a node definition.
        '''
        out = sandbox_contact()
        out.fromXML(self, node)
        return out

    # OUTPUT methods
    def write_vector_5D(self, name, v):
        '''! \brief Write a vect_5D as a node.
        '''
        out = self.NewNode(name, 'vect_5D')
        self.AddField('x', v.x, out)
        self.AddField('y', v.y, out)
        self.AddField('z', v.z, out)
        if hasattr(v,'course'):
            self.AddField('course', v.course, out)
            self.AddField('rate', v.rate, out)
        else:
            # rescue vect_3D
            self.AddField('course', 0.0, out)
            self.AddField('rate', 0.0, out)
        return out
    

    def write_LOGPAC(self, name, logpac):
        '''! \brief Write to a children of node in the LOGPAC format
        '''
        return logpac.toXML(self, name)

    # Tree manip
    def AddField(self, tagname, value, parent, type='', name='', sameas=''):
        temp = self.doc.createElement(tagname)
        if type:
            self.SetAttribute('type',type,temp)
        if name:
            self.SetAttribute('name', name, temp)
        if sameas:
            self.SetAttribute('sameas', sameas, temp)
        # Explicit XML writer
        if hasattr(self, 'write_' + type):
            _fn = getattr(self, 'write_' + type)
            temp.appendChild(_fn(tagname, value))
        # Implicit XML render
        elif hasattr(value, 'toXML'):
            temp.appendChild(value.toXML(self, tagname))
        # Treat as string instead.
        else:
            temp.appendChild(self.doc.createTextNode(str(value)))
        parent.appendChild(temp)
    
    def DateTime(self, tagname, dt):
        '''! \brief return a date time node
        '''
        n = self.doc.createElement(tagname)
        n.setAttribute('type','datetime')
        n.appendChild(self.doc.createTextNode('%d/%d/%d %d:%d:%d'%(dt.day,dt.month,dt.year,dt.hour,dt.minute,dt.second)))
        return n
        
        
    def AddNode(self, child, parent = None):
        if parent == None:
            parent = self.root
        parent.appendChild(child)
        
    def NewNode(self, tagname, type= ''):
        out = self.doc.createElement(tagname)
        if type:
            out.setAttribute('type', type)
        return out
    
    def NewComment(self, comment):
        return self.doc.createComment(comment)
        
    def AttributeDictionary(self, D, node):
        '''! Set each keys as an attribute '''
        for i in D:
            if type(i) == type(''):
                try:
                    node.setAttribute(str(i), str(D[i]))
                except:
                    pass

    def SetAttribute(self, name, value, node):
        node.setAttribute(str(name),str(value))
        
    def __str__(self):
        '''! A pretty version of the document '''
        return '<?xml version="1.0" ?>\n' + self.WriteNode(self.root)
        #return self.doc.toprettyxml()
    
    def WriteNode(self, node, indent=0):
        '''! \brief a more compact and functional render than prettyxml (which sucks...)'''
        out = node.toxml()
        if len(out) <= 100:
            return ('\t'*indent) + out + '\n'
        
        # Break down
        out = '\t'*indent + '<%s'%(node.tagName)
        D = self.AttributesAsDict(node)
        for i in D:
            out += ' %s="%s"'%(i, str(D[i]))
        out += '>\n'
        
        for i in node.childNodes:
            out += self.WriteNode(i,indent+1)
        
        out += '</%s>\n'%(node.tagName)
        return out

    
if __name__ == "__main__":
    a = sandboXML(rootname='world')
    a.AttributeDictionary({'sim':'sandbox','version':'0.7.1'})
    print a