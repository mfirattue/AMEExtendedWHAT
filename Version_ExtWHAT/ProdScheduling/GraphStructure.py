# -*- coding: utf-8 -*-
"""
Created on Sun Sep 13 21:37:05 2020
1BK50-2020 LP Assignment Library


"""

import pandas as pd
import time
from collections import deque
import numpy as np
from Objects.GraphObjects import SPArcs




    
#%%
print('Storing Arcs')
def InitializeGraphStructure(myOrder, tau_value, horizonExtension, timeGranularity):
    # AMEArcs.weight = weight

    timeHorizon = tau_value + horizonExtension
    starttime = time.time()
    LinearNodes = int(timeHorizon*1440/timeGranularity)
    # print('LinearNodes', LinearNodes)
    # for OrderID, myOrder in Orders.items():
        # if OrderID %2:
    size = 0.0000000001
    # else: size = - 0.0000000001
    myJob = myOrder.StartJobs[0]
    SkipArcs = []
    Arcs = dict()
    ExecuteArcs = []
    # for i in range(len(myOrder.Jobs)): # not a while loop in the case of an order with one job
    while len(myJob.Successors) == 1:
        for timeNode in range(LinearNodes):
            
            # Check if the node starts during offtime. If so, the node is not created
            # SelectedMachine = 
            day = (timeNode*timeGranularity)//1440
            machineOffThisDay = (myJob.AlternativeMachines[0].UpTimePerDay*60//timeGranularity)*timeGranularity #Offtime[SelectedMachine][day]
            if timeNode*timeGranularity >= day*1440+machineOffThisDay:
                continue
            
            
            if timeNode*timeGranularity >= myJob.StartLB and (timeNode + 1)*timeGranularity <= myJob.StartUB:
                SkipArcs.append(((myJob, timeNode*timeGranularity),(myJob,(timeNode + 1)*timeGranularity), size))
                
            if timeNode*timeGranularity >= myJob.StartLB and timeNode*timeGranularity <= myJob.StartUB:
                mySucJob = myJob.Successors[0]
                myArc = SPArcs(timeNode*timeGranularity, myJob, timeGranularity)
                # if myArc.endNode <= mySucJob.StartUB/timeGranularity: # Deze controleren!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                ExecuteArcs.append(((myJob, timeNode*timeGranularity),(mySucJob,myArc.endNode*timeGranularity), myArc))
                Arcs[(myJob, timeNode*timeGranularity)] = myArc

                
        myJob = myJob.Successors[0]
    
            
    FinishArcs = []
    FinishedNode = []
    for timeNode in range(LinearNodes):
        if timeNode*timeGranularity >= myJob.StartLB and (timeNode + 1)*timeGranularity <= myJob.StartUB:
            SkipArcs.append(((myJob, timeNode*timeGranularity),(myJob,(timeNode + 1)*timeGranularity), size))
        if timeNode*timeGranularity >= myJob.StartLB and timeNode*timeGranularity <= myJob.StartUB:
            myArc = SPArcs(timeNode*timeGranularity, myJob, timeGranularity)
            ExecuteArcs.append(((myJob, timeNode*timeGranularity),('end',myArc.endNode*timeGranularity), myArc))
            # ExecuteArcs.append(((myJob, timeNode),('end',myArc.endNode), myArc))
            FinishedNode.append((('end',myArc.endNode*timeGranularity),myArc))
            Arcs[(myJob, timeNode*timeGranularity)] = myArc

            
            
    for node_ , myArc in FinishedNode:
        FinishArcs.append((node_, 'sink', max( myArc.CompTime - myOrder.SDeadline*1440, 0)))
    myOrder.Arcs = Arcs

    myOrder.ExecuteArcs = ExecuteArcs
    staticArcs = SkipArcs + FinishArcs
    myOrder.staticArcs = staticArcs
    
    testArcs = staticArcs.copy()
    for stN, endN, myArc in ExecuteArcs:
        testArcs.append((stN, endN, myArc.CallWeight()))
        
    endDict = {}
    for stN, endN, weight_ in testArcs:
        if endN not in endDict:
            endDict[endN] = {}
            endDict[endN][stN] = weight_
        else: endDict[endN][stN] = weight_
    
    
    myOrder.endDict = endDict
    
    IntegerDict = {}
    idx = 0
    for from_, to, weight in testArcs:
        if from_ not in IntegerDict:
            IntegerDict[from_] = idx
            idx += 1
    for from_, to, weight in testArcs:
        if to != 'sink':
            if to not in IntegerDict:
                IntegerDict[to] = idx
                idx += 1
    IntegerDict['sink'] = idx
    revDict = {v: k for k, v in IntegerDict.items()}

    myOrder.IntegerDict = IntegerDict
    myOrder.revDict = revDict

    myOrder.sourceNode = IntegerDict['sink']
    myOrder.sinkNode = 0
    S = 0
    V = IntegerDict['sink']
    
        
    # print('Creating arcs finished in', time.time()-starttime)
    return


# #%%
# #%%
# print('StartCalculating SP')
# # from typing import Dict, List, Optional, Tuple
# a = time.time()
# for i in range(1):
#     for OrderID, myOrder in Orders.items():
#         # print('OrderID', OrderID)
#         Column =[]
#         graph = myOrder.getGraph()
#         # print(time.time()-a)
#         # print(graph)
#         Dict, new_solution, SolutionList, d = myOrder.shortestPathFaster(graph)
#         # print(SolutionList)




#     for SelectedArc in SolutionList:
#         ArcProperties = [SelectedArc]
#         # print(Arcs[SelectedArc].SPMachine)
#         ArcProperties.append(myOrder.Arcs[SelectedArc].SPMachine)
#         Column.append(ArcProperties)
    
#     myOrder.Schedules.append(Column)
# # print((time.time()-a)/1)
    
    
# #%%
# tijd_1 = time.time()
# iterations = 1
# for i in range(iterations):
#     for MachineName, myMachine in Machines.items():
#         myMachine.DualWeight = np.array(np.random.uniform(0,5,40000))
#         # if MachineName == 'PRD_LaserMarking_2':
#         #     myMachine.DualWeight = np.concatenate((np.array(np.random.uniform(800000,900000,12000)),np.array(np.random.uniform(0,5,40000))))
#         # if MachineName == 'PRD_LaserMarking_1':
#         #     myMachine.DualWeight = np.concatenate((np.array(np.random.uniform(800000,900000,12000)),np.array(np.random.uniform(0,5,40000))))
        
#     a = time.time()
#     for OrderID, myOrder in Orders.items():
#         Column =[]
#         tijd = time.time()
            
#         graph = myOrder.getGraph()

#         Dict, new_solution, SolutionList, d = myOrder.shortestPathFaster(graph)
    
#         for SelectedArc in SolutionList:
#             ArcProperties = [SelectedArc]
#             ArcProperties.append(myOrder.Arcs[SelectedArc].SPMachine)
#             Column.append(ArcProperties)


#         myOrder.Schedules.append(Column)

# print((time.time()-tijd_1)/iterations)


            

# def PricingUpdateMILPObjective(myOrder, timeGranularity): #SolvePricingMILP

#     dummy_var = myOrder.PricingMILP.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
#     # objExp = 2 * dummy_var
#     objExp = myOrder.PricingMILPTardVar
#     for myJob in myOrder.Jobs:
#         for myArc in myJob.PricingMILPArcs:
#             objExp = objExp + myArc.CallWeight(timeGranularity) * myArc.PricingMILPVar
        
#     myOrder.PricingMILP.setObjective(objExp)
#     return



#     # myOrder.PricingMILP.update()
#     # myOrder.PricingMILP.Params.outputFlag = 0
#     # myOrder.PricingMILP.optimize()
    
    
    
    
    
            
    




