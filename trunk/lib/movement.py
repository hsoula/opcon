
from random import random
import system_base

'''
   Modeled elements:
   Speed as a function of:
           - terrain
           - Stance 
           - command
           - supression (may abort impulse's movement)
           
   Each impulse of movement increase the supression by a fraction of the friction incurred.
'''
class system_movement(system_base.system_base):
    def __init__(self, speed = 35.0, mode = 'wheeled'):
        system_base.system_base.__init__(self)
        # Max cruise speed
        self['speed'] = speed
        
        # Mode of transportation
        self['mode'] = mode
        
        # Pointer to the map data.
        self.map_frictions = None
        
        # Pointer to the vehicles
        self.vehicles = []
        
        # Suppression due to friction
        self['suppression'] = 0.0

        # Cache the last friction for supression purpose
        self.lastNetFriction = 0.0
        self.lastNetSuppression = 0.0
        
        self.friction_locked = False
        
    def fromXML(self, doc, node):
        '''! \brief Load from XML definition
             Parse speed, mode and friction override.
        '''
        attr = ['speed', 'mode']
        for att in attr:
          X = doc.Get(node, att)
          if X:
            self[att] = X
        

    

    #
    # Interface element ##############################################################
    # Construction of the instances
    def SetVehicles(self, v):
        self.vehicles = v
    def SetFrictions(self, f):
        '''! \brief Get the dictionary of friction as a pointer from the map object.
        '''
        self.map_frictions = f


    # Public Interface (Return Speed and Friction)
    def Speed(self, terrain = 'unrestricted', command = 1.0, stance = 'deployed'):
        '''
                Implement the speed in km/hour for a unit, given the following factors:
                    -- terrain : friction.
                    -- stance  : deployed, withdrawal, retreat, transit.
                    -- suppression : chance to abort movement in this pulse.
        '''
        
        # friction
        self.lastNetFriction = self.Friction(terrain,stance,command)
        self.lastNetSuppression = self.MovementSuppression(self.lastNetFriction)
        # Twice as much if not in road column
        if stance != 'transit':
            self.lastNetSuppression *= 2.0
        
        # Net velocity
        return self['speed'] * self.lastNetFriction
    
    def Friction(self, terrain, stance, command):
        '''
           Compute the friction effected on a unit
        '''
        friction = self.friction_terrain(terrain)
        friction = friction *self.friction_stance(stance)
        friction = friction**self.command_exponent(command)
        return friction
    #
    # Model elements ###########################################################
    def GetModes(self):
        ''' Returns a list of modes for this entity (and vehicles'''
        out = [self['mode']]
        for i in self.vehicles:
            x = i.GetMode()
            if not x in out:
                out.append(x)
        return out
    def command_exponent(self, command):
        return 1.0/float(command)
    

    
    def friction_stance(self, stance):
        '''
                transit, deployed, withdrawal, retreat
        '''
        if stance == 'transit':
            return 1.15
        elif stance == 'deployed':
            return 0.8
        elif stance == 'retreat':
            return 1.0
        else:
            return 0.6
    
    def friction_terrain(self, terrain):
        '''
                Friction incurred by terrain [unobstrcuted, obstructed, severely restricted, imapssable]
        '''
        # Try frictions for each mode and keep the worst
        out = 1.0
        for mode in self.GetModes():
            if self.map_frictions[mode].has_key(terrain):
                if self.map_frictions[mode][terrain] < out:
                    out = self.map_frictions[mode][terrain]
        return out
        
    def friction_dict(self):
        # TODO - do not account for a mixture of vehicles.
        return self.map_frictions[self['mode']]
    
    def MovementSuppression(self, friction):
        '''
           Compute the suppression caused by a given amount of friction.
           Currently modeled such as the supression can go up to friction over 24 hours movement, assuming an impulse of 10 minutes.
        '''
        return 0.007 * random() * friction