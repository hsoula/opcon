'''
   SMIRK - a KML python wrapper
   cblouin@cs.dal.ca
   
'''
# import section
import xml.dom.minidom as minidom
import re

class sandboXML:
    def __init__(self, rootname=None, read = False, root=None):
        '''! Create a document with the root set to rootname '''
        self.ints = re.compile('^\d+$')
        self.floats = re.compile('^\d*\.\d*$')
        self.datetimes = re.compile('^\d+/\d+/\d{4} \d{4}[:\d+]?$')
        
        if read:
            self.doc = minidom.parse(read)
            self.root = self.Get(self.doc.firstChild, 'Document')
        else:
            self.doc = minidom.Document()
            self.root = self.doc.createElement('Document')
            self.doc.appendChild(self.root)
        
        
    # INPUT methods
    def RootName(self):
        if self.root:
            return str(self.root.tagName)
        
    def Get(self, node, tag='', force_list = False):
        '''! \brief Look for an attribute or element with the corresponding tag(s). 
             Return a list of if there is multiple elements.
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
        if len(out) <= 100 or node.nodeType == 3:
            return ('\t'*indent) + out + '\n'
        
        # Break down
        out = '\t'*indent + '<%s'%(node.tagName)
        D = self.AttributesAsDict(node)
        for i in D:
            out += ' %s="%s"'%(i, str(D[i]))
        out += '>\n'
        
        for i in node.childNodes:
            out += self.WriteNode(i,indent+1)
        
        out += ('\t'*indent) + '</%s>\n'%(node.tagName)
        return out
    

    
class sandboxKML(sandboXML):
    def __init__(self, rootname=None, read = False):
        sandboXML.__init__(self, rootname, read)
        

    def type_Camera(self, node):
        out = KMLCamera()
        out.fromXML(node, self)
        return out
    
    def type_description(self, node):
        out = KMLDescription()
        out.fromXML(node, self)
        return out
    
    def type_Folder(self, node):
        out = KMLFolder()
        out.fromXML(node, self)
        return out
    
    def type_LookAt(self, node):
        out = KMLLookAt()
        out.fromXML(node, self)
        return out
    
    def type_Icon(self, node):
        out = KMLIcon()
        out.fromXML(node, self)
        return out
    
    def type_IconStyle(self, node):
        out = KMLIconStyle()
        out.fromXML(node, self)
        return out
    def type_LineString(self, node):
        out = KMLLineString()
        out.fromXML(node, self)
        return out
    def type_LineStyle(self, node):
        out = KMLLineStyle()
        out.fromXML(node, self)
        return out

    def type_LinearRing(self, node):
        out = KMLLinearRing()
        out.fromXML(node, self)
        return out
    def type_Placemark(self, node):
        out = KMLPlacemark()
        out.fromXML(node, self)
        return out
    def type_Point(self, node):
        out = KMLPoint()
        out.fromXML(node, self)
        return out
    def type_Polygon(self, node):
        out = KMLPolygon()
        out.fromXML(node,self)
        return out
    def type_PolyStyle(self, node):
        out = KMLPolyStyle()
        out.fromXML(node, self)
        return out
    def type_Style(self, node):
        out = KMLStyle()
        out.fromXML(node, self)
        return out
    
    def type_StyleMap(self, node):
        out = KMLStyleMap()
        out.fromXML(node, self)
        return out
    

    def __str__(self):
        '''! A pretty version of the document '''
        return '<?xml version="1.0" ?>\n<kml xmlns="http://earth.google.com/kml/2.1">\n' + self.WriteNode(self.root) + u'</kml>\n'
        #return self.doc.toprettyxml()        

    # High level access Methods
    def GetElement(self, node, classname, name):
        ''' Find the an element of a certain class type, and of a given name
        '''
        # Go over all elements
        for nd in self.ElementAsList(node):
            print type(nd), nd.__class__
            x = self.Get(nd, name)
            if x:
                return x
        # Return Nothing
        return ''
    
    # OPCON specific access Methods
    def GetOVERLAYS(self):
        ''' Fetch all overlays from the OVERLAYS folder and return them as instance.
        '''
        # Mandatorily returns as a list
        out = []
        
        # Fetch the folder named OVERLAYS
        home = self.GetElement(self.root, 'Folder', 'OVERLAYS')
    
        # out
        return home
                
        
        
class KMLbase:
    def __init__(self, tag, id=''):
        self.id = id
        self.tag = tag
        
    def toXML(self, xml):
        out = xml.NewNode(self.tag)
        if self.id:
            xml.SetAttribute(u'id', unicode(self.id), out)
        
        return out

    
    def fromXML(self, node, xml):
        self.id = xml.Get(node,'id')
    
    def ExtractFeatures(self, node, xmldoc):
        out = []
        # features
        features = ['Placemark', 'Folder'] # ,'ScreenOverlay', 'GroundOverlay'] 
        for x in xmldoc.ElementAsList(node):
            z = xmldoc.AttemptTyping(x)
            if hasattr(z, 'tag') and (getattr(z, 'tag') in features):
                out.append(z)
        return out
                
class KMLDocument(KMLbase):
    '''
       name (string) Document name (filename)
       styles (dictionary) Dict of styles and stylemaps
       items (list) List of features.
    '''
    def __init__(self, docname=''):
        KMLbase.__init__(self,'Document')
        
        # Elements
        self.name = docname
        
        # Style keys are id fields
        self.styles  =  {}
        self.items =  []
    
    # Mutator
    def SetName(self, name):
        self.name = name
        
    def AddItem(self, item):
        self.items.append(item)
    def AddStyle(self, style):
        self.styles[style.id] = style
        
    def fromXML(self, filename):
        xmldoc = sandboxKML(read = open(filename))
        self.name = xmldoc.Get(xmldoc.root, 'name')
        
        # Styles
        temp = xmldoc.Get(xmldoc.root, 'Style', True)
        temp += xmldoc.Get(xmldoc.root, 'StyleMap', True)
        for i in temp:
            self.styles[i.id] = i
        
        self.items = self.ExtractFeatures(xmldoc.root, xmldoc)
        
    def toXML(self, xml):
        node = xml.root
        if self.id:
            xml.SetAttribute(u'id', unicode(self.id), xml.root)
            
        # Name
        xml.AddField(u'name', unicode(self.name), node)
        
        # Styles
        for i in self.styles:
            i = self.styles[i]
            xml.AddNode(i.toXML(xml), node)
            
        # Objects
        for i in self.items:
            xml.AddNode(i.toXML(xml), node)
            
        return node
    
    def WriteXML(self, fname=''):
        xml = sandboxKML()
        self.toXML(xml)
        
        if not fname:
            fname = self.name
        
        if not fname.endswith('.kml'):
            fname += '.kml'
            
        fout = open(fname,'w')
        fout.write(str(xml))
        fout.close()

class KMLStyleMap(KMLbase):
    def __init__(self, id='', normal = '', highlight = ''):
        KMLbase.__init__(self, 'StyleMap', id)
            
        #  Elements
        self.normal = normal
        self.highlight = highlight
        
        
    def fromXML(self,  node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        for pair in xmldoc.Get(node, 'Pair', True):
            if xmldoc.Get(pair, 'key') == 'normal':
                self.normal =  xmldoc.Get(pair,'styleUrl')[1:]
            elif xmldoc.Get(pair, 'key') == 'highlight':
                self.highlight =  xmldoc.Get(pair,'styleUrl')[1:]
                
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        pair1 = xml.NewNode('Pair')
        xml.AddField(u'key', u'normal', pair1)
        xml.AddField(u'styleUrl', u'#'+ unicode(self.normal), pair1)
        xml.AddNode(pair1, node)
        
        pair2 = xml.NewNode('Pair')
        xml.AddField(u'key', u'highlight', pair2)
        xml.AddField(u'styleUrl', u'#'+ unicode(self.highlight), pair2)
        xml.AddNode(pair2, node)
    
        return node
        
        
class KMLStyle(KMLbase):
    def __init__(self, id=''):
        KMLbase.__init__(self, 'Style', id)
        
        # Elements
        self.IconStyle = None
        self.LabelStyle = None
        self.LineStyle = None
        self.PolyStyle = None
        self.BaloonStyle = None
        self.ListStyle = None
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        self.IconStyle = xmldoc.Get(node, 'IconStyle')
        self.LabelStyle = xmldoc.Get(node, 'LabelStyle')
        self.LineStyle = xmldoc.Get(node, 'LineStyle')
        self.PolyStyle = xmldoc.Get(node, 'PolyStyle')
        self.BaloonStyle = xmldoc.Get(node, 'BaloonStyle')
        self.ListStyle = xmldoc.Get(node, 'ListStyle')
    
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        for i in ['Icon', 'Label', 'Line', 'Poly', 'Baloon', 'List']:
            att = getattr(self, i + 'Style')
            if att:
                xml.AddNode(att.toXML(xml), node)
        
        return node

    def SetStyle(self, style):
        if isinstance(style, KMLIconStyle):
            self.IconStyle = style
        elif isinstance(style, KMLLineStyle):
            self.LineStyle = style
        elif isinstance(style, KMLPolyStyle):
            self.PolyStyle = style
        elif isinstance(style, KMLLabelStyle):
            self.LabelStyle = style
        # List and Baloon aren't implemented yet.
            
class KMLColorStyle(KMLbase):
    def __init__(self, tag):
        KMLbase.__init__(self, tag)
        self.color = self.SetColor(0,0,0)
        self.colorMode = 'normal'
        
    def SetColor(self, r=0, g=0, b=0, a=0):
        a = hex(a)[:-2].rjust(2,'0')
        r = hex(r)[:-2].rjust(2,'0')
        g = hex(g)[:-2].rjust(2,'0')
        b = hex(b)[:-2].rjust(2,'0')
        self.color = a + b + g + r
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        x = xmldoc.Get(node, 'color')
        if x:
            self.color = x
        
        x = xmldoc.Get(node, 'colorMode')
        if x:
            self.colorMode = x
            
    def toXML(self, xml):
        out = KMLbase.toXML(self, xml)
        
        xml.AddField(u'color', unicode(self.color), out)
        xml.AddField(u'colorMode', unicode(self.colorMode), out)
        
        return out
        

class KMLLabelStyle(KMLColorStyle):
    def __init__(self, color='ffffffff', scale=1.0, colormode='normal'):
        KMLColorStyle.__init__(self, 'LabelStyle')
        self.color = color
        self.scale = scale
        self.colorMode = colormode
        
    def fromXML(self, node, xmldoc):
        KMLColorStyle.fromXML(self, node, xmldoc)
        
        self.scale = xmldoc.Get(node, 'scale')
        
    def toXML(self, xml):
        node = KMLColorStyle.toXML(self,xml)
        
        xml.AddField(u'scale', unicode(self.scale), node)
        return node
    
class KMLIconStyle(KMLColorStyle):
    def __init__(self, iconurl='', scale=1.0, heading='', hotspot=None):
        KMLColorStyle.__init__(self, 'IconStyle')
        
        self.scale = scale
        self.heading = heading
        
        if isinstance(iconurl, KMLIcon):
            self.Icon = iconurl
        else:
            self.Icon = KMLIcon(href=iconurl)
            
        if hotspot:
            self.hotSpot = hotspot
        else:
            self.hotSpot = {'x':"0.5", 'y':"0.1", 'xunits':"fraction", 'yunits':"fraction"}
        
    def fromXML(self, node, xmldoc):
        KMLColorStyle.fromXML(self, node, xmldoc)
        
        x = xmldoc.Get(node, 'scale')
        if x: 
            self.scale = x
        x = xmldoc.Get(node, 'heading')
        if x: 
            self.heading = x
            
        self.Icon = xmldoc.Get(node, 'Icon')

        x = xmldoc.Get(node, 'hotSpot')
        if x: 
            self.hotSpot = xmldoc.AttributesAsDict(x)
        
    def toXML(self, xml):
        node = KMLColorStyle.toXML(self,xml)
        
        xml.AddField(u'scale', unicode(self.scale), node)
        if self.heading != '':
            xml.AddField(u'heading', unicode(self.heading), node)
        
        xml.AddNode(self.Icon.toXML(xml), node)
        
        hp = xml.NewNode('hotSpot')
        xml.AttributeDictionary(self.hotSpot, hp)
        xml.AddNode(hp, node)
        
        return node
    

class KMLLineStyle(KMLColorStyle):
    def __init__(self):
        KMLColorStyle.__init__(self, 'LineStyle')
        
        self.width = 1
        
    def fromXML(self, node, xmldoc):
        KMLColorStyle.fromXML(self, node, xmldoc)
        x = xmldoc.Get(node, 'width')
        if x:
            self.width = x
    
    def toXML(self, xml):
        node = KMLColorStyle.toXML(self, xml)
        xml.AddField(u'width', unicode(self.width), node)
        
        return node
    
class KMLPolyStyle(KMLColorStyle):
    def __init__(self, id=''):
        KMLColorStyle.__init__(self, 'PolyStyle')
        
        self.outline = 1
        self.fill = 1
        
    def fromXML(self, node, xmldoc):
        KMLColorStyle.fromXML(self, node, xmldoc)
        x = xmldoc.Get(node, 'fill')
        if x != '':
            self.fill = x
        x = xmldoc.Get(node, 'outline')
        if x != '':
            self.outline = x
    
    def toXML(self, xml):
        node = KMLColorStyle.toXML(self, xml)
        if not self.fill:
            xml.AddField(u'fill', unicode(self.fill), node)
        if not self.outline:
            xml.AddField(u'outline', unicode(self.outline), node)
        
        return node
    
class KMLIcon(KMLbase):
    def __init__(self, href='', id=''):
        KMLbase.__init__(self, 'Icon', id)
        
        self.href = href
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        
        self.href = xmldoc.Get(node, 'href')
        
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        xml.AddField(u'href', unicode(self.href), node)
        
        return node
        
class KMLFeature(KMLbase):
    def __init__(self, tag, id=''):
        KMLbase.__init__(self, tag, id)
        
        self.name = ''
        self.visibility = 1
        self.open = 1
        self.description = ''
        self.styleUrl = ''
        self.AbstractView = None
        self.TimePrimitive = ''
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        
        self.name = xmldoc.Get(node, 'name')
        self.visibility = int(bool(xmldoc.Get(node, 'visibility')))
        self.open = int(bool(xmldoc.Get(node, 'open')))
        self.styleUrl = xmldoc.Get(node, 'styleUrl')[1:]
        self.description = xmldoc.Get(node, 'description')
        self.TimePrimitive = xmldoc.Get(node, 'TimePrimitive')
        
        self.AbstractView = xmldoc.Get(node, 'LookAt')
        if not self.AbstractView:
            self.AbstractView = xmldoc.Get(node, 'Camera')
        
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        xml.AddField(u'name', unicode(self.name), node)
        xml.AddField(u'visibility', unicode(self.visibility), node)
        xml.AddField(u'open', unicode(self.open), node)
        if self.styleUrl:
            xml.AddField(u'styleUrl', u'#' + unicode(self.styleUrl), node)
        
        if self.description:
            xml.AddNode(self.description.toXML(xml), node)
        if self.AbstractView:
            xml.AddNode(self.AbstractView.toXML(xml), node)
        if self.TimePrimitive:
            xml.AddNode(self.TimePrimitive.toXML(xml), node)
        
        return node
    # Mutator
    def SetDescription(self, desc):
        if isinstance(desc, KMLDescription):
            self.description = desc
        else:
            self.description = KMLDescription(text=desc)
    
    def Visible(self, i=True):
        self.visibility = i
        
    def Open(self, i=True):
        self.open = i
        
    def SetName(self, name):
        self.name = name
        
    def SetStyleUrl(self, su):
        self.styleUrl = su
        
class KMLFolder(KMLFeature):
    def __init__(self, name = '', id = ''):
        KMLFeature.__init__(self, 'Folder', id)
        
        self.name = name
        
        self.items = []
        
    def AddItem(self, item):
        self.items.append(item)
        
    def fromXML(self, node, xmldoc):
        KMLFeature.fromXML(self, node, xmldoc)
        self.items = self.ExtractFeatures(node, xmldoc)
        
    def toXML(self, xml):
        node = KMLFeature.toXML(self, xml)
        
        for i in self.items:
            xml.AddNode(i.toXML(xml), node)
        return node
            
class KMLPlacemark(KMLFeature):
    geometries = ['Point', 'LineString', 'LineRing', 'Polygon', 'MultiGeometry', 'Model']
    def __init__(self, id =''):
        KMLFeature.__init__(self, "Placemark", id)
        
        self.geometry = ''
    
    def SetExtrude(self, i=True):
        if self.geometry:
            self.geometry.extrude = int(i)
            
    def SetAltitudeMode(self, mode):
        if self.geometry:
            self.geometry.altitudeMode = mode
        
    def fromXML(self, node, xmldoc):
        KMLFeature.fromXML(self, node, xmldoc)
        
        for i in KMLPlacemark.geometries:
            self.geometry = xmldoc.Get(node, i)
            if self.geometry:
                break
        
    def toXML(self, xml):
        node = KMLFeature.toXML(self, xml)
        xml.AddNode(self.geometry.toXML(xml), node)
        return node
            
        

class KMLGeometry(KMLbase):
    '''
       Abstract Data type, attributes aren't officially assigned to this object, but are 
       implmented here for convenience.
    '''
    def __init__(self, tag, id=''):
        KMLbase.__init__(self, tag, id)
        
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        
        if hasattr(self, 'extrude'):
            self.extrude = xmldoc.Get(node, 'extrude')
        
        if hasattr(self, 'altitudeMode'):
            self.altitudeMode = xmldoc.Get(node, 'altitudeMode')
            
        if hasattr(self, 'coordinates'):
            self.coordinates = xmldoc.Get(node, 'coordinates')
            
        if hasattr(self, 'tesselate'):
            self.tesselate = xmldoc.Get(node, 'tesselate')
            
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        if hasattr(self, 'extrude')  and self.extrude:
            xml.AddField(u'extrude', unicode(self.extrude), node)
        
        if hasattr(self, 'altitudeMode') and self.altitudeMode:
            xml.AddField(u'altitudeMode', unicode(self.altitudeMode), node)
            
        if hasattr(self, 'tesselate'):
            xml.AddField(u'tesselate', unicode(self.tesselate), node)
            
        if hasattr(self, 'coordinates'):
            if hasattr(self.coordinates, 'toXML'):
                xml.AddNode(self.coordinates.toXML(xml), node)
            else:
                xml.AddField(u'coordinates', unicode(self.coordinates), node)
            
        return node
            
            
class KMLPoint(KMLGeometry):
    def __init__(self, id='', coordinates=''):
        KMLGeometry.__init__(self, 'Point', id)
        
        self.extrude = 0
        self.altitudeMode = 'relativeToGround'
        self.coordinates = coordinates
        
    def fromXML(self, node, xmldoc):
        KMLGeometry.fromXML(self, node, xmldoc)
        
    def toXML(self, xml):
        return KMLGeometry.toXML(self, xml)


class KMLPolygon(KMLGeometry):
    def __init__(self, id=''):
        KMLGeometry.__init__(self, 'Polygon', id)
        
        self.extrude = 0
        self.tesselate = 0
        self.altitudeMode = 'relativeToGround'
        
        self.outerBoundaryIs = ''
        self.innerBoundaryIs = ''
        
    def fromXML(self, node, xmldoc):
        KMLGeometry.fromXML(self, node, xmldoc)
        
        x = xmldoc.Get(node, 'outerBoundaryIs')
        if x:
            self.outerBoundaryIs = xmldoc.Get(x, 'LinearRing')
        
        x = xmldoc.Get(node, 'innerBoundaryIs')
        if x:
            self.innerBoundaryIs = xmldoc.Get(x, 'LinearRing')
    
    def toXML(self, xml):
        node = KMLGeometry.toXML(self, xml)
        
        if self.outerBoundaryIs:
            x = xml.NewNode('outerBoundaryIs')
            xml.AddNode(self.outerBoundaryIs.toXML(xml), x)
            xml.AddNode(x, node)
        
        if self.innerBoundaryIs:
            x = xml.NewNode('innerBoundaryIs')
            xml.AddNode(self.innerBoundaryIs.toXML(xml), x)
            xml.AddNode(x, node)
        
        return node
    

class KMLLinearRing(KMLGeometry):
    def __init__(self, tag='LinearRing', id=''):
        KMLGeometry.__init__(self, tag, id)
        
        self.extrude = 0
        self.altitudeMode = 'relativeToGround'
        self.coordinates = None
        self.tesselate = 0
    
    def fromXML(self, node, xmldoc):
        KMLGeometry.fromXML(self, node, xmldoc)

    def toXML(self, xml):
        node = KMLGeometry.toXML(self, xml)
        
        return node
        
class KMLLineString(KMLLinearRing):
    def __init__(self, id=''):
        KMLLinearRing.__init__(self, 'LineString', id)
class KMLAbstractView(KMLbase):
    ''' Abstract class for Camera/LookAt
    '''
    def __init__(self, tag, id=''):
        KMLbase.__init__(self, tag, id)
        
        self.longitude = 0
        self.latitude  = 0
        self.altitude  = 0
        self.tilt      = 0
        self.heading   = 0
        self.altitudeMode = 'relativeToGround'
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        
        for i in ['longitude','latitude','altitude','tilt','heading','altitudeMode']:
            setattr(self, i, xmldoc.Get(node, i))
            
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        for i in ['longitude','latitude','altitude','tilt','heading','altitudeMode']:
            xml.AddField(unicode(i), unicode(getattr(self, i)), node)
        return node
        
class KMLLookAt(KMLAbstractView):
    def __init__(self, id=''):
        KMLAbstractView.__init__(self, 'LookAt', id)
        
        self.range = 1000
        
    def fromXML(self, node, xmldoc):
        KMLAbstractView.fromXML(self, node, xmldoc)
        
        self.range = xmldoc.Get(node, 'range')
        
    def toXML(self, xml):
        node = KMLAbstractView.toXML(self, xml)
        xml.AddField(u'range', unicode(self.range), node)
        return node
class KMLCamera(KMLAbstractView):
    def __init__(self, id=''):
        KMLAbstractView.__init__(self, 'LookAt', id)
        
        self.roll = 0
        
    def fromXML(self, node, xmldoc):
        KMLAbstractView.fromXML(self, node, xmldoc)
        
        self.range = xmldoc.Get(node, 'roll')
        
    def toXML(self, xml):
        node = KMLAbstractView.toXML(self, xml)
        xml.AddField(u'roll', unicode(self.roll), node)
        return node    
    

class KMLDescription(KMLbase):
    def __init__(self, id='', text=''):
        KMLbase.__init__(self, 'description', id)
        
        self.text = text
        
    def SetText(self, text):
        self.text = text
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
        
        self.text = node.childNodes[0].nodeValue
    
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        x = xml.doc.createCDATASection(self.text)
        xml.AddNode(x, node)
        
        return node
    
class KMLXXX(KMLbase):
    def __init__(self, id=''):
        KMLbase.__init__(self, 'description', id)
        
        
    def fromXML(self, node, xmldoc):
        KMLbase.fromXML(self, node, xmldoc)
    
    def toXML(self, xml):
        node = KMLbase.toXML(self, xml)
        
        return node
    

# Less Abstract Classes ###
# Icon Placemark
class KMLIconPlacemark(KMLPlacemark):
    def __init__(self, name, lat=0.0, lon=0.0, alt=0.0, style='', point=None):
        KMLPlacemark.__init__(self)
        
        if point:
            self.geometry = point
        else:
            x = '%f,%f,%f'%(lon, lat, alt)
            self.geometry = KMLPoint(coordinates = x)

        self.SetName(name)
        self.SetStyleUrl(style)
    
if __name__ == "__main__":
    # Dynamically generate a KML file
    x = KMLDocument('gendoc.kml')
    x.AddItem( KMLFolder('Blah') )
    myfolder = KMLFolder('B/3-15IN')
    x.AddItem( myfolder )
    myfolder.AddItem(KMLIconPlacemark('A Plt', lat=46.8125, lon=-71.2185, alt= 10))
    #x.AddItem( KMLPlacemark().MakeIcon('Test', lat=46.812, lon=-71.218, alt= 1000) )
    x.WriteXML()
    # Read and Write
    a = KMLDocument()
    a.fromXML('test.kml')
    a.WriteXML('out.kml')
