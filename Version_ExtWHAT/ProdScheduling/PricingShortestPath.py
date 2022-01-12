# -*- coding: utf-8 -*-
"""


@author: mfirat
"""
# from Objects.PlanningObjects import Schedule
import gurobipy as grb
from Objects.PlanningObjects import AMEOrderSchedule
import math
import time





###################################################################################################
def print_distance(d, V):
    print("Vertex","\t","Distance from source")
 
    for i in range(1, V + 1):
        print(i,"\t",d[i])

def SolveExactPricingSP(myOrder,timelimit,TimeHorizon,iterno, timeGranularity):
    Column =[]
    graph = myOrder.getGraph()
    
    # print('OrderID', OrderID)

    # print(time.time()-a)
    # print(graph)
    Dict, new_solution, SolutionList, d, V = myOrder.shortestPathFaster(graph)
    myOrderSchedule = None
    # if d[V] -  myOrder.MasterLPDual + 10**-6 > 0:
        # print_distance(d, V)
        # print(SolutionList)
        # print(SolutionList)
        # print('sink idx: ', V)
    Schedule = {}
    for SelectedArc in SolutionList:
        ArcProperties = [SelectedArc]
        # print(Arcs[SelectedArc].SPMachine)
        ArcProperties.append(myOrder.Arcs[SelectedArc].SPMachine)
        Column.append(ArcProperties)
        myJob, StartTime = SelectedArc
        if myJob.IsFinal:
            JobCompletion = myJob.Order.Arcs[SelectedArc].CompTime
        
        if myOrder.Arcs[SelectedArc].SPMachine in Schedule:
            Schedule[myOrder.Arcs[SelectedArc].SPMachine].append((myJob, range(StartTime,myOrder.Arcs[SelectedArc].CompTime, timeGranularity)))
        else:
            # print(1, myOrder.Arcs[SelectedArc])
            # print(2, myOrder.Arcs[SelectedArc].CompTime)
            Schedule[myOrder.Arcs[SelectedArc].SPMachine] = [(myJob, range(StartTime,myOrder.Arcs[SelectedArc].CompTime, timeGranularity))]
        # print(Schedule)
            
        # print(Column)
        
        # myOrder.Schedules.append(Column)
        # Orderschedule = None
        # redcost = None
        # print('Order masterartvar = ' , - myOrder.MasterLPDual)
        # print('Order red cost = ' , - myOrder.MasterLPDual.x)
    tardiness = max( JobCompletion - myOrder.SDeadline*1440,0)
    myOrderSchedule = AMEOrderSchedule(Schedule, JobCompletion, tardiness)
    if not myOrderSchedule.checkFeasibility():
        myOrderSchedule.PrintSchedule()
    # if d[V] -  myOrder.MasterLPDual < 0:
        # myOrder.Schedules.append(myOrderSchedule)
    return myOrderSchedule, max(d[V],0) -  myOrder.MasterLPDual + 10**-6#Orderschedule, redcost



