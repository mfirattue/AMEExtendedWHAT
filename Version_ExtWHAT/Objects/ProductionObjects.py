# -*- coding: utf-8 -*-
"""
Created on Wed Dec 30

@author: mfirat
"""

import pandas as pd
import time
import math
from Objects.ProcessObjects import QualityCheck
import random




class AMEWorkcenter:
    # Initializer / Instance Attributes
    def __init__(self,myname):
        self.Name = myname
        self.Machines = []
        self.Workers = []
        self.Equipments = []
        self.ProcessRoutes = dict() # key: RouteID, value = [[order,operation]]
        
        
        self.Tasks = []
        self.TasksToSchedule = []
        self.Jobs = []
        self.Schedules= dict()
        
        self.MachineGroups =[]
        self.MachSubsetCons = []
        # self.MachineSubsetCons = []
        # self.CapacityUseVars = []
        
        # self.MachineGroups = []
        
        self.MachineSubSetList = []


    def getName(self):
        return self.Name


class ProductGroup:

     # Initializer / Instance Attributes
    def __init__(self,myID):

        self.products = []

    def getProducts(self):
        return self.products

class Worker:
     # Initializer / Instance Attributes
    def __init__(self,myWorkCnt,myname,myOpr,myAvailability):
        self.WorkCenter = myWorkCnt
        self.Name = myname
        self.Operations = myOpr
        self.fte = 1.0
        self.EffectiveHours = 8
        self.Availability = myAvailability

    def getEffectiveHours(self):
        return self.EffectiveHours
    def getName(self):
       return self.Name
    def getWorkCenter(self):
       return self.WorkCenter

    def setFTE(self,myfte):
       self.fte = myfte
    def getFTE(self):
       return self.fte

    def getAvailability(self):
        return self.Availability


class Equipment:
     # Initializer / Instance Attributes
    def __init__(self,myWorkCnt,myName, myOpr, myAvailability):
        self.WorkCenter = myWorkCnt
        self.Name = myName
        self.Operations = myOpr
        self.Availability = myAvailability

    def getOperations(self):
       return self.Operation
    def getWorkCenter(self):
       return self.WorkCenter
    def getName(self):
       return self.Name
    def getAvailability(self):
        return self.Availability


class AMEMachine:
     # Initializer / Instance Attributes
    def __init__(self,myWorkCnt,myName,myOprs, myUtil,myAvailability,myUpTime):

        self.WorkCenter = myWorkCnt
        self.Name = myName
        self.Utilization = myUtil
        self.OperationTypes = myOprs
        self.Availability = myAvailability #per day
        self.UpTimePerDay = myUpTime # Hours
        self.CapUse = 0.0
        
        # Roling horizon
        self.RollingLPVars = dict() #keyJobID, valueVar
        self.RollingLPCons = []
        self.RolingLatestComp = 0
        # self.MasterLPVars = dict()
        self.MasterLPCons = []
        self.MasterArtMachVar = {}
        self.DualWeights = []    
        
        self.PricingMILPArcs = []
        self.BenchmarkMILPArcs = []
        
        
        
    def OnTimeGivenDay(self,day, timeGranularity):
        if abs(day) >= len(self.Availability):
            return ((self.UpTimePerDay*60)//timeGranularity)*timeGranularity
        return ((int(self.Availability[int(day)])*self.UpTimePerDay*60)//timeGranularity)*timeGranularity


    
    def setCapUse(self,val):
        self.CapUse = val

    def getCapUse(self):
        return self.CapUse

    def PrintAMEMachine(self):
        print(self.WorkCenter, self.Name, self.Utilization, self.Operations, self.Availability, self.UpTimePerDay)

    


class AMEMachineSubSet: 
    def __init__(self, machinelist):
        self.Machines = machinelist
        self.MachSubsetCons = [] # for each day
        self.CapacityUseVars = []


class AMEOperationType:
    
       # Initializer / Instance Attributes
    # def __init__(self,myProd,myname):
    def __init__(self,myname):
  
        self.Name = myname
        self.Workers = []
        self.ReqWorkers = 0
        self.ReqEquipments = []
        self.AlternativeMachines = []
        self.IncludingMachineSubsets = []
        

class AMEOperation:

       # Initializer / Instance Attributes
    def __init__(self,myProd,myname,myOprType):

        self.Prod = myProd
        self.OperationType = myOprType
        self.Name = myname
        self.Workers = []

        self.ExecutionInfo = dict() #key: machine, value: [processtime,setuptime,scraprate]
        self.BatchInfo = [] # Min,Avg,Max

        # MF: for the extension of WHAT model
        self.ReqWorkers = 0
        self.ReqEquipments = []
        
        self.WCMachSubsets = []
        # print(self.ExecutionInfo.values())
        
        
    def FindLatestTime(self,LastCompletionMinute,timeGranularity):
        dayidx = 0
        day = int((LastCompletionMinute-0.0001)//1440)
        
        currday = day
        OptionFound = False
        while not OptionFound:
            for mach in self.OperationType.AlternativeMachines:
                if abs(currday) >= len(mach.Availability):
                    if currday < 0:
                         return 0
                    else:
                         return LastCompletionMinute
                
                if int(mach.Availability[currday]) == 1:
                    OptionFound = True
                    dayidx = currday
                    break
            currday -= 1
        LatestTime = min(LastCompletionMinute, dayidx*1440+self.OperationType.AlternativeMachines[0].OnTimeGivenDay(dayidx, timeGranularity))
        return LatestTime

    def setExecutionInfo(self,machine,processTime,setuptime):
        self.ExecutionInfo[machine] = [processTime,setuptime]
        self.ProcessTime = list(self.ExecutionInfo.values())[0][0]  
        self.SetupTime = list(self.ExecutionInfo.values())[0][1]


class AMEProduct:
    # Initializer / Instance Attributes
    def __init__(self,myPN,myWokrcnt,myGroup,myProcessRoute,minbatch,maxbatch,avgbatch, myScrapRate, StockLevel):
        self.PN = myPN
        self.WorkCenter = myWokrcnt
        self.Predecessors = [] # list of tuples (product,multiplier) met lists
        self.Operations = []
        self.RawMaterials = [] # list of tuples (rawmaterial (PN), multiplier), 1 of 0 (boolean)
        self.ProductGroup = myGroup
        self.ProcessRoute = myProcessRoute
        self.AvgBatch = avgbatch
        self.MinBatch = minbatch
        self.MaxBatch = maxbatch
        self.StockLevel = StockLevel
        #self.StockLevel = []
        # print('PN: ', self.PN, 'StockLevel', self.StockLevel)
        
        self.ScrapRate = myScrapRate
        

        self.TargetVars = []
        self.ProductionVars = []
        self.SetupVars = []
        self.SetupCons = []
        self.TargetStockCons = []
        
        self.TargetLevels = [] #advice levels
    
# class AMERawMaterial:
#     # Initializer / Instance Attributes
#     def __init__(self, myPN, myWokrcnt, QualitypastRate):
#         self.PN = myPN
#         self.WorkCenter = myWokrcnt
#         self.StockLevels = [] #fixed values
#         self.RequiringProducts = [] #Tuples (PN, multiplier)
        
#         # print('PN: ', self.PN, 'StockLevel', self.StockLevel)
    
#         self.QualitypastRate = QualitypastRate
#         self.TargetVars = [] #for every time step, level decision variable
#         self.TargetStockCons = [] #
#         self.TargetLevels = [] #advice levels
#         self.Slack = [] #slackvalues
#         self.LeadTime = random.randint(1,6)
#         # self.Alternative = myAlternative
        
        
# class AMEAlternative:
#     # Initializer / Instance Attributes
#     def __init__(self, myPN, myWokrcnt):
#         self.PN = myPN
#         self.WorkCenter = myWokrcnt
#         self.StockLevels = random.randint(1,4)
#         self.LeadTime = random.randint(1,6)
#         # self.RequiringProducts = [] #Tuples (PN, multiplier)
        # self.Group = [] #the group/design of the succesor of the raw material 
        
        # print('PN: ', self.PN, 'StockLevel', self.StockLevel)
        