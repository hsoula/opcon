'''
   Log interface
'''

# import

# funtion

# class
class sandbox_log:
  def __init__(self):
    self.lines = []
    self.beginwith = 0
    
  def __str__(self):
    '''Must reconstitute from file in the low memory version!! TODO'''
    out = ''
    for i in self.lines:
      out = out + i + '\n'
    return out + '\n'
  
  def fileUpdate(self, fh):
    '''Wite to file handle the leftover part of the logs'''
    # Low memory version
    for line in self.lines:
      fh.write(line + '\n')
    self.lines = []
    self.beginwith = 0
    # High memory version
    for line in self.lines[self.beginwith:]:
      fh.write(line + '\n')
    self.beginwith = len(self.lines)
    
  def Add(self, entry):
    ''' 
       
    '''
    self.lines.append(entry)