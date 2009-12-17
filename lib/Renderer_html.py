'''
    Utilities to write to the HTML format.
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

def Table(data):
  '''!
     Take the table, fist item on list is header.
  '''
  lb = 'style="text-align: left;" border="0" cellpadding="5" cellspacing="0"'
  header = ''
  try:
    for i in data[0]:
      header = header + Tag('td',Tag('STRONG',i))
    header = Tag('tr',header,' style="text-decoration: underline;"')
    
    overall = ''
    for i in data[1:]:
      line = ''
      for j in i:
        line = line + Tag('td', j)
      overall = overall + Tag('tr',line)
    out = Tag('tbody', header+overall)
    
    out = Tag('Table',out,lb)
    return out
  except:
    pass
  

  return out
def Tag(tag,str, attr = ''):
  # convert the attr
  if attr == 'red':
    attr = 'style="color: rgb(255, 0, 0);"'
  elif attr == 'blue':
    attr = 'style="color: rgb(0, 0, 255);"'
    
  if str.find('\n') != -1:
    if attr:
      return '<%s %s>\n%s\n</%s>\n'%(tag,attr,str,tag)
    return '<%s>\n%s\n</%s>\n'%(tag,str,tag)
  return '<%s %s>%s</%s>'%(tag,attr,str,tag)

def italic(S):
  return Tag('span',S, 'style="font-style: italic;"')
  
  
def HTMLfile(title, body):
  '''
      Return a fully formed HTML file as a string
  '''
  # Header
  hd = '<meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">\n'
  hd = hd + Tag('title',title)
  # <style type="text/css"> body { font-family: Courier New,Courier,monospace;} </style>
  hd = hd + Tag('style', 'body { font-family: monospace; font-size: small; width: 500px} ', 'type="text/css"')
  hd = Tag('head',hd)
  
  out = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">\n'
  out = out + Tag('HTML',hd+Tag('body',body))
  return out
  
def AppendtoHTML(htmlfile, newtext):
  '''! \brief Append newtext to the existing file by insterting BEFORE the </body> tag.
  '''
  # Split htmlfile
  index = htmlfile.rfind('</body>')
  if index == -1:
    index = htmlfile.rfind('</BODY>')
  if index == -1:
    # do nothing! This isn't a valid HTML file
    return htmlfile
  
  # top/bottom
  return htmlfile[:index] + newtext + htmlfile[index:]

