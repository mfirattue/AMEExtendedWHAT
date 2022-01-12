# -*- coding: utf-8 -*-
"""
Created on Sat Mar  6 06:54:55 2021

@author: mfirat, sruiter
"""
import math
import numpy as np
from collections import deque
import gurobipy as grb

# from Objects.ProductionObjects import Product,Workcenter,Machine




    

class AMEOrder:
    ProductOrderDict = {}
    #                   myID,myQuantity,myProd,myStart,myDeadline,myType,myCustID):
    def __init__(self,myID,myQuantity,myProd,mySplit,mySPeriod,myRev,myDeadline,myType,myCust):
        self.OrderID = myID
        self.Quantity = myQuantity     
        self.Deadline = myDeadline
        self.Type = myType
        self.Product = myProd
        self.SplitDelivery = mySplit
        self.SplitPeriod = mySPeriod
        self.Revenue = myRev
        self.CustomerPriority = myCust
        self.LatestStart = self.Deadline * 1440
        
        self.ShiftVars = []
        self.RejectVar = None
        self.Constraints = []
        self.Rejected = False
        self.SQuantity = 0
        self.SDeadline = 0
        self.FinalJob = None
        self.SequentialOrder = True
        self.StartJobs = []
        self.Jobs = []
        
        
        
        # self.MasterLPVars = [] # <OrderSchedule>:var
        self.MasterLPCons = None
        self.MasterArtVar = None
        self.MasterLPDual = 0
        
        self.PricingMILP = None
        self.PricingMILPTardVar = None
        self.PricingMILPTardCons = None
        
        
        self.BenchmarkMILPTardVar = None
        self.BenchmarkMILPTardCons = None
        

        
        self.Schedules = [] # list of orderschedule objects
        self.JobMachAssign = None # list of job-machine pairs branched so far in the search tree.
        self.Branched = False
        self.AssignBranched = False
        # self.MPSchedules = []
        
    def getJobMachAssign(self):
        return self.JobMachAssign
    
    def setJobMachAssign(self,assign):
        self.JobMachAssign = assign
    
        
    def setBranched(self):
        self.Branched = True
    
    def resetBranched(self):
        self.Branched = False
     
    def setAssignBranched(self):
        self.AssignBranched = True
    
    def resetAssignBranched(self):
        self.AssignBranched = False
        
   
        
    def setSQuantity(self, quantity):
        self.Squantity = quantity
        
    def setSDeadLine(self, deadline):
        self.SDeadline = deadline        
        
        
    def getLatestStartDay(self):
        return int(self.LatestStart//1440)
        
    def setLatestStartTime(self, NewStartOption):
        self.LatestStart = min(self.LatestStart, NewStartOption)
        
    def RecursiveTimeUpdate(self, myProduct,lastestcompletion,Quantity,timeGranularity):
        # print('Start: ')

        # if self.LatestStart <= 0:
        #     return
        Quantity = math.ceil(Quantity *(1+myProduct.ScrapRate))
        CurrentTime = lastestcompletion
    
        for idx in range(len(myProduct.Operations)-1,-1,-1):
            Operation_ = myProduct.Operations[idx]
            day = (CurrentTime-0.001)//1440
            Machine = Operation_.OperationType.AlternativeMachines[0]
            # RemainingProcTime = Quantity*processtime + setuptime
            
            RemainingProcTime = (((Quantity*Operation_.ProcessTime + Operation_.SetupTime-0.0001)//timeGranularity)+1)*timeGranularity

            StartTime = CurrentTime

            while RemainingProcTime > 0:
                dayUse = min(CurrentTime - round(day*1440), RemainingProcTime)
                StartTime = int(CurrentTime - RemainingProcTime)
                RemainingProcTime -= dayUse

                day -= 1

                CurrentTime = (day*1440+Machine.OnTimeGivenDay(day, timeGranularity))

                
        self.setLatestStartTime(StartTime)
        # if self.OrderID == 47:
        #     print('      PN', myProduct.PN, 'Quantity', Quantity, 'StockLevel: ', myProduct.StockLevel)
        
        
        if myProduct.PN in AMEOrder.ProductOrderDict:
            AMEOrder.ProductOrderDict[myProduct.PN].append(self.OrderID)
        else:
            AMEOrder.ProductOrderDict[myProduct.PN] = [self.OrderID]
        
    
        for myPredProduct, Multiplier in myProduct.Predecessors:
            self.RecursiveTimeUpdate(myPredProduct, StartTime, Multiplier * Quantity, timeGranularity)
        return 
     
    def FindLatestStartTime(self, tau_value, timeGranularity): #over products
        # print('\n')
        # print('OrderID', self.OrderID)
        day = self.Deadline
        LastMinuteTime = self.Product.Operations[-1].FindLatestTime(day*1440, timeGranularity)
        # print('LastMinuteTime', LastMinuteTime)
        self.RecursiveTimeUpdate(self.Product,LastMinuteTime, self.Quantity, timeGranularity)
        return
        
    def setOrderSchedule(self, OrderSchedule):
        self.Schedules.append(OrderSchedule)

    def UpdateorderArcs(self, new_dict):
        self.MILPArcs.update(new_dict)
        
    
    def addEdge(self, frm, to, weight, graph):
        graph[frm].append([to, weight])

    def getGraph(self):
        graph = [[] for _ in range(100000)]
        AllArcs = self.staticArcs.copy()
        for stN, endN, myArc in self.ExecuteArcs:
            weight = myArc.CallWeight()
            AllArcs.append((stN, endN, weight))
            self.endDict[endN][stN] = weight

        for start, to, weight in AllArcs:
            # print(start, to, weight)
            self.addEdge(self.IntegerDict[start], self.IntegerDict[to], weight, graph)
        return graph

    
    
    def shortestPathFaster(self, graph):
        # graph = self.getGraph()

        S = 0
        V = self.IntegerDict['sink']
        
        # Create array d to store shortest distance
        d = [10**9]*(V + 1)
        # Boolean array to check if vertex
        # is present in queue or not
        inQueue = [False]*(V + 1)
        d[S] = 0
        q = deque()
        q.append(S)
        inQueue[S] = True
        
        while (len(q) > 0):
            # Take the front vertex from Queue
            u = q.popleft()
            inQueue[u] = False
            # Relaxing all the adjacent edges of
            # vertex taken from the Queue
            for i in range(len(graph[u])):
                v = graph[u][i][0]
                weight = graph[u][i][1]
                if (d[v] > d[u] + weight):
                    d[v] = d[u] + weight
     
                    # Check if vertex v is in Queue or not
                    # if not then append it into the Queue
                    if (inQueue[v] == False):
                        q.append(v)
                        inQueue[v] = True
        

        Dict = {}

        for i in range(1, V + 1):
            Dict[self.revDict[i]] = d[i]
        # print(d)
        
        Dict[(self.StartJobs[0],0)] = 0
        SolutionList = []
        new_solution = []
        index = 'sink'
        value = 0
        while index != (self.StartJobs[0],0):
            # print(index)
            for idx, weight in self.endDict[index].items():
                # print('index', index,'_  ', idx, weight)
                if Dict[idx] + weight == Dict[index]:
                    new_solution.append((value, Dict[idx], idx, weight , Dict[index]))
                    # print('step: ',value, 'start: ', idx, 'Dist: ', np.round(Dict[idx],3), ' + ', weight , ' = ', np.round(Dict[index],3), 'goes to: ', index)
                    new_index = idx
            value += 1
            index = new_index
        
        for idx in range(len(new_solution)-1):
            if new_solution[idx][2][0] != new_solution[idx+1][2][0]:
                SolutionList.append(new_solution[idx+1][2])
                # print((new_solution[idx+1][2][0].JobID, new_solution[idx+1][2][1], new_solution[idx+1][2][0].Order.Arcs[(new_solution[idx+1][2][0],new_solution[idx+1][2][1])].CompTime))
            # else:  
            #     try:
            #         print('     ',(new_solution[idx+1][2][0].JobID, new_solution[idx+1][2][1]))
            #     except:
            #         print('     ',(new_solution[idx+1][2][0], new_solution[idx+1][2][1]))
        
        
        return Dict, new_solution, SolutionList, d, V  
    
    def setPricingMILP(self, PricingMILP):
        self.PricingMILP = PricingMILP
        self.PricingMILPTardVar = PricingMILP.addVar(vtype=grb.GRB.CONTINUOUS, name="tard_O"+str(self.OrderID)) 
        self.PricingMILP.modelSense = grb.GRB.MINIMIZE
        

    
def MakeBackwardShift(self, tau_value, timeGranularity): #over products
    # print('\n')
    # print('OrderID', self.OrderID)
    day = self.Deadline
    LastMinuteTime = self.Product.Operations[-1].FindLatestTime(day*1440, timeGranularity)
    # print('LastMinuteTime', LastMinuteTime)
    self.RecursiveTimeUpdate(self.Product,LastMinuteTime, self.Quantity, timeGranularity)
        
def RecursiveTimeUpdate(self, myProduct,lastestcompletion,Quantity,timeGranularity):
    # print('Start: ')

    # if self.LatestStart <= 0:
    #     return
    Quantity = math.ceil(Quantity *(1+myProduct.ScrapRate))
    CurrentTime = lastestcompletion

    for idx in range(len(myProduct.Operations)-1,-1,-1):
        Operation_ = myProduct.Operations[idx]
        day = (CurrentTime-0.001)//1440
        Machine = Operation_.OperationType.AlternativeMachines[0]
        # RemainingProcTime = Quantity*processtime + setuptime
        
        RemainingProcTime = (((Quantity*Operation_.ProcessTime + Operation_.SetupTime-0.0001)//timeGranularity)+1)*timeGranularity
        # print('RemainingProcTime: ', RemainingProcTime)
        StartTime = CurrentTime
        # print('StartTime!!!', StartTime)
        counter = 0
        while RemainingProcTime > 0:
            dayUse = min(CurrentTime - round(day*1440), RemainingProcTime)
            StartTime = int(CurrentTime - RemainingProcTime)
            RemainingProcTime -= dayUse
            # print(counter, 'RemainingProcTime: ', RemainingProcTime)
            day -= 1
            # if day <= 0:
            #     self.setLatestStartTime(0)
            #     return
            CurrentTime = (day*1440+Machine.OnTimeGivenDay(day, timeGranularity))
            counter += 1
            
    self.setLatestStartTime(StartTime)
    # if self.OrderID == 47:
    #     print('      PN', myProduct.PN, 'Quantity', Quantity, 'StockLevel: ', myProduct.StockLevel)
    
    
    if myProduct.PN in AMEOrder.ProductOrderDict:
        AMEOrder.ProductOrderDict[myProduct.PN].append(self.OrderID)
    else:
        AMEOrder.ProductOrderDict[myProduct.PN] = [self.OrderID]
    

    for myPredProduct, Multiplier in myProduct.Predecessors:
        self.RecursiveTimeUpdate(myPredProduct, StartTime, Multiplier * Quantity, timeGranularity)
    return

 
class JobMachineAssignment:
    
    def __init__(self,myorder):
        
        self.assigndict = dict() # key is job and value is machine
        self.order = myorder
        self.PricingLNodeConsDict = dict()
        self.PricingLNodeVarDict = dict()
        self.PricingRNodeCons = None
        self.PricingRNodeRedundancyVar = None
        myorder.setJobMachAssign(self)
      
   
        
    def getAssignDict(self):
        return self.assigndict 
        
    def getLNodeConsDict(self):
        return self.PricingLNodeConsDict
    def getLNodeVarDict(self):
        return self.PricingLNodeVarDict
    def getRNodeCons(self):
        return self.PricingRNodeCons
    def setRNodeCons(self,mycons):
        self.PricingRNodeCons = mycons
    def setRNodeRedundancyVar(self,myvar):
        self.PricingRNodeRedundancyVar = myvar
    def getRNodeRedundancyVar(self):
        return self.PricingRNodeRedundancyVar
        
   

class AMEOrderSchedule:
    def __init__(self, Schedule, tardiness, SelectedArcs):
        self.Order = list(Schedule.values())[0][0][0].Order
        self.id = len(self.Order.Schedules)
        self.MPLambdaVar = None
        self.tardiness = tardiness
        self.MPSchedule = Schedule #[dict(),dict(),.....] key=machine, value=[] list of tuple (jobs,[30,60])
        
        self.PricingMILPArcs = SelectedArcs
        self.PricingMILPExclCons = None
        self.PricingRedundancyVar = None
        self.Branched = False
        
        
    def setBranched(self):
        self.Branched = True
    def resetBranched(self):
        self.Branched = False
            
    
    def checkFeasibility(self):
        # alljobs = []
        dictionary = {}
        for machine, Tuples in self.MPSchedule.items():
            for myJob, ranges in Tuples:
                dictionary[myJob] = ranges
        FeasibilityFound = True
        for myJob, times in dictionary.items():
            if len(myJob.Successors) != 0:
                if dictionary[myJob.Successors[0]].start < dictionary[myJob].stop:
                    print('Order: ', myJob.Order.OrderID, 'Precedence viol job:  ', myJob.Successors[0].JobID, 'Started before job: ', myJob.JobID, ' Compl')
                    FeasibilityFound = False
        return FeasibilityFound
        
            
    def PrintSchedule(self):
        for myMachine, Tuples in self.MPSchedule.items():
            print(myMachine.Name)
            for myJob, ranges in Tuples:
                print(myJob.JobID, [i.JobID for i in myJob.Predecessors], ranges)
        return


class AMETask:

    # Initializer / Instance Attributes
    def __init__(self,myid,myProd,myQuantity,myDeadline,OrderID, myOrder):
        self.ID = myid
        self.Product = myProd
        self.Quantity = myQuantity
        self.Deadline = math.ceil(myDeadline)
        
        self.MasterLPDict = dict()
        self.Jobs = []
        self.AllJobs = []
        self.OrderID = OrderID
        self.myOrder = myOrder
        self.Predecessors = []
        self.Successors = []
        
        self.PredstoComplete = []
        self.jobproctime = 0
        self.FinalTask = False
        
        
        # Task-day model
        
        self.DayAssignVars = []
        self.AssignedDay = -1
        self.TardyVar = None
        self.CompVar = None
        
        #greedy heuristic
        self.PrGreedyTardyVar = None
        self.PrGreedyCompVar = None  
        
        # Task-day model
     
    ##########################################################################

    def setFinal(self):
        self.FinalTask = True


        
class AMEJob:
    def __init__(self, JobID, TaskID, myTask, OrderID, myOrder, Deadline, PN, WorkCenter, MachineOptions, ProcessingTime, Quantity):
        self.JobID = JobID
        self.TaskID = TaskID
        self.Task = myTask
        self.OrderID = OrderID
        self.Order = myOrder
        self.Deadline = Deadline
        self.PN = PN
        self.Quantity = Quantity
        self.WorkCenter = WorkCenter
        self.Predecessors = []
        self.Successors = []
        self.AlternativeMachines = MachineOptions
        self.ProcessingTime = int(round(float(ProcessingTime)))
        self.IsFinal = False
        self.IsStart = False
    
        
        self.MachineBranched = False
        self.TimeBranched = False
 
                
        self.StartLB = 0
        self.StartUB = 999999999
        
        self.RollingWeight = None
        self.RollingLPVars = []
        self.RollingLPCons = []
        # self.RollingMaxComp = 0
        self.RollingSchedulable = False
        self.RollingStartTime = None
        self.RollingCompletion = None
        self.RollingScheduled = False
        self.RollingPredsToSchedule = None
        
        self.RollingMaxPredComp = 0
        self.RemainingProcTime = 'NULL'
        self.succsToSchedule = 'NULL'
        
        self.PricingMILPArcs = [] 
        self.PricingMILPPrecCons = []
        self.PricingMILPArcVars = []
        self.PricingMILPArcDict = {} # key is machine and value is the execution arcs with that machine.
        # MF (26-10-21) the above dictionary will get the arcs of a certain machine immediately. 
        
        self.BenchmarkMILPArcs = [] 
        self.BenchmarkMILPPrecCons = []
        self.BenchmarkMILPArcVars = []
         
    def getPricingMILPArcDict(self):
        return self.PricingMILPArcDict 
    
        
        
    def setMachineBranched(self):
        self.MachineBranched = True
    def resetMachineBranched(self):
        self.MachineBranched = False    
        
        
        
    def setTimeBranched(self):
        self.TimeBranched = True
    def resetTimeBranched(self):
        self.TimeBranched = False          
        #self.quantity
        #self.OperationStype
        
    def setStartLB(self, newcandidate):
        self.StartLB = max(newcandidate, self.StartLB)
    def setStartUB(self, newcandidate):
        self.StartUB = min(newcandidate, self.StartUB)
        
    def SetDeadlineMinutes(self, DeadlineInMinutes):
        self.Deadline = DeadlineInMinutes
        
    def getCompTime(self, StartTime, timeGranularity):
        day = StartTime//1440
        
        UpTimeMin = ((self.AlternativeMachines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity
        RemainingProcTime = self.ProcessingTime
        CurrentTime = StartTime
        
        CompTime = CurrentTime
        
        if CurrentTime >= day*1440+ UpTimeMin:
            CurrentTime = (day+1)*1440
            day += 1
        
        
        
        
        while RemainingProcTime > 0:
            dayUse = min(round((day*1440 + UpTimeMin) - CurrentTime), RemainingProcTime)
            CompTime = CurrentTime + RemainingProcTime
            RemainingProcTime -= dayUse
            day += 1
            CurrentTime = day*1440
            if CompTime >= (day-1)*1440 + UpTimeMin:
                CompTime = max(CompTime,CurrentTime)
            
        return CompTime

        

        
    def setRollingPredsToSchedule(self):
        self.RollingPredsToSchedule = len(self.Predecessors)
    def setRollingMaxPredComp(self, PredComp):
        if self.AlternativeMachines[0].Name == 'Phantom':
            self.RollingMaxPredComp = 0
        else:
            self.RollingMaxPredComp = max(self.RollingMaxPredComp,PredComp)
        
        
    def setRollingScheduled(self):
        self.RollingScheduled = True
    
    def resetRollingScheduled(self):
        self.RollingScheduled = False
    
    def SetRollingSchedulable(self):
        self.RollingSchedulable = True


    def RecursiveRemCompUpdate(self, myJob, RemComTime, succsToSchedule):
        myJob.RemainingProcTime = RemComTime + myJob.ProcessingTime
        myJob.succsToSchedule = succsToSchedule
        succsToSchedule += 1
        for predJob in myJob.Predecessors:
            self.RecursiveRemCompUpdate(predJob, myJob.RemainingProcTime, succsToSchedule)
    
