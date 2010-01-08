'''
    Scheduler class -- Scheduling for the simulation
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

# Import
from datetime import datetime, timedelta


class sandbox_event:
  def __init__(self, parent, fn = None, args = ()):
    # Make sure that a one argument is really a tuple
    if type(args) != type((1,1)) and type(args) != type({}):
      args = (args,)
      
    # Set the parent, necessary for PostPickle
    self.parent = parent
    
    # Default callback function
    self._fn = None
    
    # Default arguments in args or keywords
    self._args = ()
    self._keyw = {}
    
    # Set the fn and args
    if fn != None:
      self.SetFunction(fn)
      self.SetArgs(args)
    
  def Execute(self):
    # Execute the event
    if self._fn != None:
      self._fn(*self._args, **self._keyw)
    
  def SetFunction(self, fn , args = ()):
    ''' Set function and can pass args as a convenience.'''
    self._fn = fn
    if args != ():
      self.SetArgs(args)
      
  def SetArgs(self, args = ()):
    if type(args) == type(()):
      self._args = args
    else:
      self._keyw = args
    
    
  def PrePickle(self):
    ''' Make the event serializable '''
    # again, to get around the stupid problem of serializing pointers to entities.
    try:
      if self.parent.has_key('uid'):
        self.parent = self.parent['uid']
    except:
      pass
    # Function name
    if self._fn != None:
      self._fn = self._fn.__name__
      
  def PostPickle(self, parent = None):
    ''' Reconstitute the event '''
    # Instance pointer
    if parent != None:
      self.parent = parent
    # Instancemethod pointer
    if self._fn != None:
      self._fn = getattr(self.parent,self._fn)
    
    

'''
   A scheduler entry which doesn't execute any code but can use to post data and an identifying tag.
'''
class sandbox_memo(sandbox_event):
  def __init__(self, tag, data = '', parent = None):
    sandbox_event.__init__(self, parent)
    # Tag for fast searching
    self.tag = tag
    # data to post (likely to be a dictionary which should be pickleable)
    self.data = data
  
  def GetData(self):
    '''Returns the data'''
    return self.data

class sandbox_Scheduler:
  '''! General purpose Scheduling class using time structure as keys for lists of events. 
  
      Design purpose :
      Post any function call to be executed from the scheduler while the simulation will be stepping throug the time.
      
      sim.PostEvent(self.clock+self.pulse, sandbox_event(self, self.AddEntity, (newconvoy,)))
      sim.PostEvent(self.clock+self.pulse, sandbox_event(self.OOB[2], self.OOB[2].AdjustMoral, (0.25,)))
      
      or (using an alternative constructor):
      sim.PostEvent(self.clock+self.pulse, self.OOB[2], self.OOB[2].AdjustMoral, (0.25,))
      

  '''
  def __init__(self):
    # Pointer to the owner (unit/world)
    self.parent = None
    # Dictionary using datetime object as keys, the values will be list of events
    self.events = {}
    
  # Adding
  def PostEvent(self, timestamp, event, fn = None, args = None):
    '''! Add an event to the Scheduler 
        if fn and args are not None, the method will make an event.
    '''
    # Convenience built an event
    if fn != None:
      if args == None:
        args = ()
      event = sandbox_event(event, fn, args)
      
    # Add the key if needed
    if not self.events.has_key(timestamp):
      self.events[timestamp] = []
      
    # Update the datastructure
    self.events[timestamp].append(event)
    
  # Pruning
  def ShredUpTo(self, timestamp):
    '''! \brief Remove from Scheduler all items that occured before, and exactly on, a threshold
         \param timestamp [datetime] The threshold.
    '''
    off = self.events.keys()
    off.sort()
    
    for i in off:
      if i <= timestamp:
        del self.events[i]
      else:
        return
    
  # Retrieval
  def NextEventTimeStamp(self, timestamp):
    '''! Retrieve the time of the next posted event.'''
    # Get the keys in a list
    temp = self.events.keys()
    temp.sort()
    for i in temp:
      if i > timestamp:
        return i
    return None

      
  def EventList(self, timestamp):
    '''! Return the event list at a given timestamp'''
    # No events
    if not self.events.has_key(timestamp):
      return []
    # Do the deeds
    return self.events[timestamp]
  
  
  # Operators #######################################################################
  # #################################################################################
  def __getitem__(self, key):
    if type(key) == type(datetime()):
      return self.EventList(key)
    else:
      print 'Key of type %s not implemented'%(str(type(key)))
    

  def PrePickle(self):
    for i in self.events.keys():
      for j in range(len(self.events[i])):
        self.events[i][j].PrePickle()
    
  def PostPickle(self, sim):
    for i in self.events.keys():
      for j in range(len(self.events[i])):
        self.events[i][j].PostPickle(sim)

'''
if __name__ == '__main__':
  class debug:
    def __init__(self, aa):
      self.ts = str(aa)
      self.counter = 0
    def Echo(self):
      print '%s printed %d times'%(self.ts,self.counter)
      self.counter = self.counter + 1
    def PrintTime(self, mytime):
      print 'called for ', str(mytime)
      self.counter = self.counter + 1
  
  mysched = sandbox_Scheduler()
  
  from random import randint, choice
  instances = []
  for i in range(10):
    instances.append(debug(randint(0,1000)))
  
  td = timedelta(seconds = 60)
  nw = datetime.now()
  
  # Fill a schedule randomly
  for i in range(100):
    newtime = nw + randint(0,20)*td
    inst = choice(instances)
    if randint(0,1):
      mysched.PostEvent(newtime,sandbox_event(inst, inst.PrintTime, (newtime) ))
    else:
      mysched.PostEvent(newtime, sandbox_event(inst, inst.Echo))
      
  # Walk to time and execute everything in due time
  print "Begin : ", nw
  nw = mysched.NextEventTimeStamp(nw)
  while nw != None:
    print '\n', nw, len(mysched.EventList(nw)), 'events'
    for i in mysched.EventList(nw):
      i.Execute()
    nw = mysched.NextEventTimeStamp(nw)
'''  
  
    
    