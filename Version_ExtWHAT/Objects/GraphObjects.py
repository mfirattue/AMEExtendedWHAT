# -*- coding: utf-8 -*-
"""
Created on Sat Mar  6 06:54:55 2021

@author: mfirat
"""
import gurobipy as grb
import time
import numpy as np
import collections, itertools
        
        
class SPArcs:
    ArcList = []
    weight = {}
    
     # Initializer / Instance Attributes
    def __init__(self,starttime,myJob, timeGranularity):
        self.timeDelta = timeGranularity
        self.ArcList.append(self)
        self.myJob = myJob
        self.processingtime = myJob.ProcessingTime
        self.StartTime = starttime
        self.SPMachine = None

        day = starttime//1440

        RemainingProcTime = self.processingtime
        CurrentTime = self.StartTime
        self.CompTime = CurrentTime
        while RemainingProcTime > 0:
            dayUse = min(round((day*1440+self.myJob.AlternativeMachines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity - CurrentTime, RemainingProcTime)
            self.CompTime = CurrentTime + RemainingProcTime
            RemainingProcTime -= dayUse
            day += 1
            CurrentTime = day*1440
            
        self.endNode = int(((self.CompTime-0.01)//timeGranularity)+1)
        


    def CallWeight(self):
        minList = []
        for myMachine in self.myJob.AlternativeMachines:  # myJob.MachineOptions:
            minList.append(np.sum(myMachine.DualWeights[np.int(self.StartTime//self.timeDelta):np.int(self.endNode)]))
        minW= np.min(np.array(minList))
        self.SPMachine = self.myJob.AlternativeMachines[minList.index(minW)]
        return np.round(minW,3)
        
        

class MILPArc:
    
     # Initializer / Instance Attributes
    def __init__(self,starttime, myJob, myMachine, timeGranularity, PricingMILP):

        self.Job = myJob
        self.Machine = myMachine
        self.StartTime = starttime
        self.DualWeight = 0
        self.ConflictingArcs = []
        self.PricingMILPVar = PricingMILP.addVar(vtype=grb.GRB.BINARY, name="X_j"+str(myJob.JobID)+'_m'+myMachine.Name+'_t'+str(starttime))
        
        
        myJob.getPricingMILPArcDict()[myMachine].append(self)
        myJob.PricingMILPArcVars.append(self.PricingMILPVar)
        myJob.PricingMILPArcs.append(self)
        myJob.PricingMILPArcDict[(myMachine,starttime)] = self



        
        day = starttime//1440

        RemainingProcTime = myJob.ProcessingTime
        CurrentTime = self.StartTime
        self.CompTime = CurrentTime
        while RemainingProcTime > 0:
            dayUse = min(round((day*1440+self.Job.AlternativeMachines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity - CurrentTime, RemainingProcTime)
            self.CompTime = CurrentTime + RemainingProcTime
            RemainingProcTime -= dayUse
            day += 1
            CurrentTime = day*1440
            
    def CallWeight(self, timeGranularity):
            self.DualWeight = np.sum(self.Machine.DualWeights[np.int(self.StartTime//timeGranularity):np.int(self.CompTime//timeGranularity)])
            return self.DualWeight
        
        
 
        
class BenchMILPArc:
    
     # Initializer / Instance Attributes
    def __init__(self,starttime, myJob, myMachine, timeGranularity, BenchmarkMILP):

        self.Job = myJob
        self.Machine = myMachine
        self.StartTime = starttime
        self.DualWeight = 0
        self.ConflictingArcs = []
        self.BenchmarkMILPVar = BenchmarkMILP.addVar(vtype=grb.GRB.BINARY, name="X_j"+str(myJob.JobID)+'_m'+myMachine.Name+'_t'+str(starttime))
        
        
        
        myJob.BenchmarkMILPArcVars.append(self.BenchmarkMILPVar)
        myJob.BenchmarkMILPArcs.append(self)
     

        
        day = starttime//1440

        RemainingProcTime = myJob.ProcessingTime
        
        CurrentTime = self.StartTime
        
        self.CompTime = CurrentTime
        
        while RemainingProcTime > 0:
            daymachinelatest = (day*1440+self.Job.AlternativeMachines[0].UpTimePerDay*60)
            dayUse = min(round((daymachinelatest//timeGranularity)+10**-4)*timeGranularity - CurrentTime, RemainingProcTime)
            self.CompTime = CurrentTime + RemainingProcTime
            RemainingProcTime -= dayUse
            day += 1
            CurrentTime = day*1440
        
        
        day = starttime//1440
            
    
      

    

    
    
    

        
        