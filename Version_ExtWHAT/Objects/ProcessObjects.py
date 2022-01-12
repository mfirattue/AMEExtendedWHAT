# -*- coding: utf-8 -*-
"""


@author: mfirat
"""

class QualityCheck:
    
     # Initializer / Instance Attributes
    def __init__(self,myMach):
        self.myMachine = myMach
        self.QCheckCriteria = []
        self.QCheckResults = []
        self.TimeGranularity = 0
        
        
    def getMachine(self):
        return self.myMachine
    
    def getQCheckPoints(self):
        return self.QCheckPoints 
    
    def getQCheckResults(self):
        return self.QCheckResults
    
    def setTimeGranularity(self,timegr):
        self.TimeGranularity = timegr
        
    def getTimeGranularity(self):
        return self.TimeGranularity    