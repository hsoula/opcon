'''
   The Open-Ended Machine
   OPCON Sandbox implementation
   Christian Blouin, bongotatic@gmail.com
   http://www.opcon.org
'''
from random import random, shuffle

from sandbox_exception import SandboxException

class TOEMargument:
    def __init__(self, argument, outcome='', base_prob='neutral', skill_level=''):
        # The argument
        self.argument = argument
        
        # The outcome
        self.outcome = outcome
        
        # Concept mapping
        self.concept = {}
        self.BuildConcepts()
        
        # Base prob
        self.base_prob = 0
        self.SetBaseProb(base_prob)
        
        # Skill level
        self.SetSkillLevel(skill_level)
        
        # Arguments
        self.pro = []
        self.con = []
        self.failedpro = []
        self.blame = None
        
        # Outcome
        self.increment = None
        
    def __str__(self):
        if not self.IsTrue() and self.increment != None:
            
            out = 'INNEFFECTIVE %s'%(self.argument)
            if self.Blame():
                out += ' BECAUSE:\n'
            else:
                return out
            count = 1
            for i in self.Blame():
                out += '\t%d) %s\n'%(count, i)
                count += 1
            return out
        elif self.increment == None:
            return 'Unresolved %s'%(self.argument)
        else:
            return 'Successful %s'%(self.argument)
        
    def BuildConcepts(self):
        # map words to values
        x = self.concept
        
        x[''] = x['neutral'] = 0
        x['unlikely'] = -2
        x['very unlikely'] = -4
        x['likely'] = 1
        x['very likely'] = 2
        
        x['basic task'] = 4
        x['trained task'] = 0
        x['expert task'] = -4
        
        # Skill level
        x['untrained'] = -2
        x['green'] = 0
        x['professional'] = x['regular'] = 2
        x['elite'] = 4
        
    def ConceptValue(self, concept):
        ''' Returns the concept's TOEM integer value. '''
        if concept in self.concept:
            return self.concept[concept]
        raise SandboxException('InvalidTOEMconcept',concept)
    
    def SetBaseProb(self, x):
        ''' The first thing to do when setting up.
        '''
        # from a concept
        if x in self.concept:
            self.base_prob = self.concept[x]
        else:
            raise SandboxException('TOEM: Invalid concept.',x)
        
    def SetSkillLevel(self, x):
        # Adjust with skill level
        if x in self.concept:
            self.base_prob += self.concept[x]
        else:
            raise SandboxException('TOEM: Invalid skill level.', x)
            
    def GetPvalue(self):
        # Get p-value as per version 1.0 of the rule.
        p = self.base_prob
        return max(1, 2**(p+1)-1) / 2.0**(abs(p)+1)
    
    def AddPro(self, x):
        '''
           Add a pro argument.
        '''
        self.pro.append(x)
        
    def AddCon(self, x):
        '''
           Add a con argument.
        '''
        self.con.append(x)
        
    def IsTrue(self):
        # returns true is the argument is resolved and worked
        if self.increment == None:
            return False
        return self.increment >= 0
    
    def Increment(self):
        return self.increment
    
    def Resolve(self, dice=None):
        '''
           Resolve all pro/con arguments, then the argument itself.
        '''
        # Nevermind if the increment already exists
        if self.increment != None:
            return self.IsTrue()
        
        # The dice roll
        if dice == None:
            dice = random()
        
        # Sort out pros
        for i in self.pro:
            if type(i) == type(''):
                self.base_prob += 1
            else:
                if i.Resolve():
                    self.base_prob += 1
                else:
                    self.failedpro.append(i)
                
        # Sort out cons
        for i in self.con:
            if type(i) == type(''):
                self.base_prob -= 1
            else:
                if i.Resolve():
                    self.base_prob -= 1
                    
        # Determine the increment
        if dice <= self.GetPvalue():
            # It worked!
            temp = self.base_prob
            self.base_prob -= 1
            while dice <= self.GetPvalue():
                self.base_prob -= 1
            self.increment = self.base_prob - temp + 1
        else:
            # It failed.
            temp = self.base_prob
            self.base_prob += 1
            while dice >= self.GetPvalue():
                self.base_prob += 1
            self.increment = temp - self.base_prob 
            
        # Shuffle arguments (for blaming later)
        shuffle(self.con)
        shuffle(self.failedpro)
            
        return self.IsTrue()
    
    def Blame(self):
        ''' Identify the cause of a failure
        '''
        # Returns nothing if it didn't failed.
        if self.IsTrue():
            return []
        
        # If it is already done, returns it
        if self.blame != None:
            return self.blame
        
        # The number of things to complain about
        n = abs(self.Increment())
        self.blame = []
        
        for i in self.failedpro:
            self.blame.append(i)
            n -= 1
            if n == 0:
                break
        
        if n:
            for i in self.con:
                self.blame.append(i)
                n -= 1
                if n == 0:
                    break
        return self.blame
        
        
import unittest

class TOEMTesting(unittest.TestCase):
    def testNoResolve(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        self.assertEqual(x.IsTrue(), False)

    def testDefaultProb(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        self.assertEqual(x.base_prob, 0)
        
    def testUnlikelyProb(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery', 'unlikely')
        self.assertEqual(x.base_prob, -2)
        
    def testVeryUnlikelyProb(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery', 'very unlikely')
        self.assertEqual(x.base_prob, -4)
        
    def testLikelyProb(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery', 'likely')
        self.assertEqual(x.base_prob, 1)
        
    def testVeryLikelyProb(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery', 'very likely')
        self.assertEqual(x.base_prob, 2)
      
    def testUnlikelyBasic(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery', 'unlikely', 'basic task')
        self.assertEqual(x.base_prob, 2)
        
    def testVeryUnlikelyGreen(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.SetBaseProb('very unlikely')
        x.SetSkillLevel('green')
        self.assertEqual(x.base_prob, -4)
        
    def testLikelyProfessional(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.SetBaseProb('likely')
        x.SetSkillLevel('professional')
        self.assertEqual(x.base_prob, 3)
        
    def testExpertTaskProfessional(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.SetBaseProb('expert task')
        x.SetSkillLevel('professional')
        self.assertEqual(x.base_prob,-2)
        
    def testIncrement0Success(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.Resolve(0.49)
        self.assertEqual(x.Increment(),0)
        
    def testIncrement1Failure(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.Resolve(0.51)
        self.assertEqual(x.Increment(),-1)
        
    def testIncrement2Failure(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.Resolve(0.75)
        self.assertEqual(x.Increment(),-2)
        
    def testIncrement1FailureBlameEmpty(self):
        x = TOEMargument('I buy a ticket', 'I win the lottery')
        x.Resolve(0.51)
        self.assertEqual(x.Blame(),[])
        
    def testIncrement1FailureBlame(self):
        x = TOEMargument('Attack by Fire')
        x.AddCon('under fire')
        x.Resolve(0.51)
        self.assertEqual(x.Blame(),['under fire'])

    def testIncrement1FailureBlameWithFailedPro(self):
        y = TOEMargument('Apply Smoke')
        y.Resolve(0.51)
        
        x = TOEMargument('Attack by Fire')
        x.AddPro(y)
        x.AddCon('under fire')
        x.Resolve(0.26)
        self.assertNotEqual(x.Blame(),['under fire'])        

    def testIncrement1SuccessBlameWithFailedPro(self):
        y = TOEMargument('Apply Smoke')
        y.Resolve(0.51)
        
        x = TOEMargument('Attack by Fire')
        x.AddPro(y)
        x.AddCon('under fire')
        x.Resolve(0.24)
        self.assertEqual(x.Blame(),[])         
        
if __name__ == '__main__':
    # suite
    testsuite = []

    # basic tests on sandbox instance
    testsuite.append(unittest.makeSuite(TOEMTesting))
    
    # collate all and run
    allsuite = unittest.TestSuite(testsuite)
    unittest.TextTestRunner(verbosity=2).run(allsuite)
        
        