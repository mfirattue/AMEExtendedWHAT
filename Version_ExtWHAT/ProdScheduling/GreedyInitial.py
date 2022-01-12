# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 02:28:25 2021

@author: mfirat
"""
# from sortedcontainers import SortedList
# from Objects.PlanningObjects import DaySchedule,Schedule,Task,Job
from Objects.PlanningObjects import AMEOrderSchedule
import time
import collections
import gurobipy as grb
import sys

def updateSchedulableJobs(JobsToInclude, schedulableJobs):
    for myJob in JobsToInclude:
        if myJob.RollingPredsToSchedule == 0:
            schedulableJobs.append(myJob)

    return JobsToInclude, schedulableJobs




def GreedyParametricHeuristic(Workcenters,AMEJobs, tau_value, horizonExtension, timeGranularity):
    NumberOfBestSelectedSolutions = 10
    startTime = time.time() 
    parameterList = []
    
    ##################################### Turn this part off if parameters are known #########################
    for alpha in [0.001, 0.01, 0.05, 0.1]:
        for beta in [0.01, 0.25, 0.5, 0.75, 0.99]:
            for gamma in [0.01, 0.25, 0.5, 0.75, 0.99]: 
                som = alpha+beta+gamma
                parameterList.append([alpha/som,  beta/som,gamma/som])

    
    MinimumTardiness = 9999999999    
    decreaseInTardiness = []  
    TardinessDict = dict()    
    startTime = time.time()
    ########################## Find best parameter combinations ##########################################
    for alpha, beta, gamma in parameterList:
        # Execute greedy scheduling approach for parameter set
        totalTardiness = GreedyParametricHeuristic1Iter(Workcenters,AMEJobs, tau_value, horizonExtension, timeGranularity, alpha, beta, gamma, StoreSchedule = False)
        TardinessDict[(alpha,  beta,gamma)] = totalTardiness
        decreaseInTardiness.append(MinimumTardiness)
    
    # sort list of tardinesses to get best solutions
    sorted_dict = [(key, value) for (key, value) in sorted(TardinessDict.items(), key=lambda x: x[1])]
    print('All parameters checked in: ', time.time() - startTime, 'Sec')
    ##############################################################################################################


    idx = 0
    for parameters, objective in sorted_dict[0:NumberOfBestSelectedSolutions]:
        alpha, beta, gamma = parameters
        #  Execute greedy scheduling approach for parameter set, but this time store schedules for first node
        totalTardiness = GreedyParametricHeuristic1Iter(Workcenters,AMEJobs, tau_value, horizonExtension, timeGranularity, alpha, beta, gamma, StoreSchedule = True)
        print('parameters alpha', round(alpha,3), 'beta ', round(beta,3), 'gamma ', round(gamma,3), 'Tardiness:   ',totalTardiness)
        if idx == 0:
            BestFoundSolutionValue = totalTardiness
        idx += 1

    return BestFoundSolutionValue
    
def GreedyParametricHeuristic1Iter(Workcenters,AMEJobs, tau_value, horizonExtension, timeGranularity, alpha, beta, gamma, StoreSchedule = False):
    OrderSchedules = dict()
    maxRollingWeight = 0   
    for JobID, myJob in AMEJobs.items():
        RollingWeight = alpha*myJob.Order.SDeadline*1440 + beta*myJob.RemainingProcTime + gamma*myJob.succsToSchedule*1000
        maxRollingWeight = max(maxRollingWeight, RollingWeight)
        
    for JobID, myJob in AMEJobs.items():
        myJob.RollingWeight = (alpha*myJob.Order.SDeadline*1440 + beta*myJob.RemainingProcTime + gamma*myJob.succsToSchedule*1000)/maxRollingWeight
    
    ########################################## reset all variables #####################################
    schedulableJobs = dict()
    for JobID, myJob in AMEJobs.items():
        myJob.resetRollingScheduled()
        myJob.RollingSchedulable = False
        myJob.RollingMaxPredComp = 0
        
    for name,workcnt in Workcenters.items():
        for machine in workcnt.Machines:
            machine.RolingLatestComp = 0
            machine.AssignLPCons = None

    
    for JobID, myJob in AMEJobs.items():
        myJob.setRollingPredsToSchedule()
        if myJob.RollingPredsToSchedule == 0:
            schedulableJobs[JobID] =myJob
            myJob.RollingSchedulable = True
            
    ########################################## Solve Model #####################################
    
    iteration  = 0 
    while len(schedulableJobs) > 0:
        schedulableJobs, OrderSchedules = ConstructAndSolveAssignLP(iteration, Workcenters, schedulableJobs,timeGranularity, OrderSchedules)
        iteration += 1
    totalTardyness = 0
    
    CheckIfAllJobsScheduled = True
    for JobID, myJob in AMEJobs.items():
        if myJob.RollingScheduled == False:
            CheckIfAllJobsScheduled = False
            print('Job: ', myJob.JobID, ' Not scheduled')
            
        if myJob.IsFinal:
            totalTardyness += max(myJob.RollingCompletion - myJob.Order.SDeadline*1440,0)

    
    if StoreSchedule:
        if CheckIfAllJobsScheduled:
            for JobID, myJob in AMEJobs.items():
                if myJob.IsFinal:
                    tardiness = max( myJob.RollingCompletion - myJob.Order.SDeadline*1440,0)
                    
                    SelectedArcs = []
                    for machine, tuples in OrderSchedules[myJob.Order].items():
                        for myJob, ranges in tuples:
                            try:    
                                SelectedArcs.append(myJob.PricingMILPArcDict[(machine, ranges.start)])
                            except:
                                print('\n\n\n Error: HORIZON EXTENSION IS TOO SMALL !!!!!\n\n\n\n')
                                sys.stop()
                    
                    
                    myOrderSchedule = AMEOrderSchedule(OrderSchedules[myJob.Order], tardiness, SelectedArcs)
                    if not myOrderSchedule.checkFeasibility():
                        myOrderSchedule.PrintSchedule()
                        
                    DuplicateSchedule = False   
                    for schedule in myJob.Order.Schedules:
                        if schedule.tardiness == myOrderSchedule.tardiness:
                            DuplicateSchedule = (schedule.MPSchedule == myOrderSchedule.MPSchedule)
                            if DuplicateSchedule:
                                break
            
                    if not DuplicateSchedule:  
                        myJob.Order.setOrderSchedule(myOrderSchedule)
                    
        else: 
            print('Not all jobs are scheduled, therefore infeasible start solution')
            return

    return totalTardyness
        
def ConstructAndSolveAssignLP(iteration, Workcenters, schedulableJobs, timeGranularity, OrderSchedules):
    for JobID, myJob in schedulableJobs.items():
        myJob.RollingLPVars = []
        myJob.RollingLPCons = []
    for name,workcnt in Workcenters.items():   
        for machine in workcnt.Machines:
            machine.RollingLPVars = dict() #keyJobID, valueVar
            machine.RollingLPCons = []
    
    start_time = time.time()
    
    LPModel = grb.Model("AME_Initial")
    LPModel.modelSense = grb.GRB.MAXIMIZE
    for JobID, myJob in schedulableJobs.items():
        for machine in myJob.AlternativeMachines:
            jobstart = max(machine.RolingLatestComp, myJob.RollingMaxPredComp)
            x_jm = LPModel.addVar(obj = myJob.RollingWeight*10000000000 - jobstart, vtype=grb.GRB.BINARY, name='x_j'+str(myJob.JobID)+'_m'+machine.Name) 
            machine.RollingLPVars[myJob] = x_jm
            myJob.RollingLPVars.append(x_jm)
        myJob.RollingLPCons.append(LPModel.addConstr(sum(myJob.RollingLPVars) <= 1, name='Con1j'+str(myJob.JobID)))
        
    for name,workcnt in Workcenters.items():   
        for machine in workcnt.Machines:
            machine.RollingLPCons.append(LPModel.addConstr(sum(machine.RollingLPVars.values()) <= 1, name='Con2m'+machine.Name))
            
            
    LPModel.update()
    # LPModel.write('LPFiles/InitialSol.lp')
    
    LPModel.Params.outputFlag = 0
    LPModel.Params.timeLimit = 60
    LPModel.optimize()
    NrJobsScheduled = 0 
    for name,workcnt in Workcenters.items():
        for machine in workcnt.Machines:
            for myJob, Rolvar in machine.RollingLPVars.items():
                if Rolvar.x > 0.5:
                    NrJobsScheduled += 1
                    myJob.setRollingScheduled()
                    myJob.RollingStartTime = max(myJob.RollingMaxPredComp, machine.RolingLatestComp)
                    
                    
                    
                    day = myJob.RollingStartTime//1440
                    
                    UpTimeMin = ((myJob.AlternativeMachines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity

                    
                    if myJob.RollingStartTime >= day*1440+ UpTimeMin:
                        myJob.RollingStartTime = (day+1)*1440


                    
                    
                    NewCompletion = myJob.getCompTime(myJob.RollingStartTime, timeGranularity)
                    myJob.RollingCompletion = NewCompletion
                    machine.RolingLatestComp = NewCompletion
                    
                    del schedulableJobs[myJob.JobID]
                    for sucJob in myJob.Successors:
                        sucJob.RollingPredsToSchedule -= 1
                        sucJob.setRollingMaxPredComp(NewCompletion)
                        if sucJob.RollingPredsToSchedule == 0:
                            schedulableJobs[sucJob.JobID] = sucJob
                    
                    
                    # add job to OrderSchedules
                    if myJob.Order in OrderSchedules:
                        if machine in OrderSchedules[myJob.Order]:
                            OrderSchedules[myJob.Order][machine].append((myJob, range(myJob.RollingStartTime, myJob.RollingCompletion, timeGranularity)))
                        else:
                            OrderSchedules[myJob.Order][machine] =[(myJob, range(myJob.RollingStartTime, myJob.RollingCompletion, timeGranularity))]
                    else:
                        OrderSchedules[myJob.Order] = {machine:[(myJob, range(myJob.RollingStartTime, myJob.RollingCompletion, timeGranularity))]}
                        
                    continue
    # print('    Jobs scheduled: ', NrJobsScheduled)

    return schedulableJobs, OrderSchedules
#####################################################################################################
def ConstructGreedyModel(Workcenters,schedulablejobs,tasksinModel,latestdeadline,wcschedules,iterno, timeGranularity):

    return schedulablejobs



