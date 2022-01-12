# -*- coding: utf-8 -*-
"""
Created on Wed Dec 30 13:29:17 2020

@author: mfirat, sruiter
"""


from ProdScheduling.BPSearch import DoBPSearch
from ProdScheduling.BenchmarkMILP import InitializeBenchMachineTimes,InitializeBenchMarkMILP,SolveBenchmarkMILP
from ProdScheduling.PricingMILP import InitializeMachineTimes
from OutputWriter import WriteJobs,WriteMachines, storeSchedules, storeNodeProperties
from Objects.PlanningObjects import AMETask,AMEJob
import pandas as pd
from datetime import datetime
import math

    
################################################################################
'''Scheduling phase of production control'''
################################################################################


def ScheduleProduction(WorkCenters,Orders, acceptedorders, tau_value, timeGranularity,horizonExtension):
    
    
    print('   >> Post-processing procedure: of matching productions targets and accepted order to create tasks at work centers..')
    
    '''
       For each accepted order we walk (recursively) backwards on its production path.
       For a product (in a workcenter), we check the production targets and assign needed amount to the order, that is creasting a task for that order.
       When we encounter a production target value zero, then we stop by seeing that the needed amount is met by stock. 
       Precedence relations among tasks are set in the procedure. 
       Scheduling instance is created when these tasks are converted into jobs. 
    ''' 


    
    acceptedorders.sort(key = lambda x: -(10**6)*x.SDeadline-x.SQuantity-x.OrderID) 
    for order in acceptedorders:     
        UpdatedDeadline = min(order.SDeadline*1440, (order.SDeadline- 1 + (order.Product.Operations[-1].OperationType.AlternativeMachines[0].UpTimePerDay/24))*1440)
        CreateTask(order, UpdatedDeadline, order.SQuantity, order.Product, None, timeGranularity)

    
    # obtain the scheduling problems for each workcenter
    # Workload optimization model did not have jobs only products and orders: ConvertJobs creates the corresponding jobs of orders
    
    print('   >> Tasks are converted into jobs..')
    AMEJobs, AMESelectedOrders = ConvertJobs(WorkCenters, timeGranularity, tau_value, horizonExtension)
    
    
    
    for name,workcnt in WorkCenters.items():
        print('     > Work center ',name,' has ',len(workcnt.Tasks),' tasks that converted to',len(workcnt.Jobs),' jobs')
    ############################## Store job and machine properties in csv ##############################
    WriteJobs(WorkCenters)
    WriteMachines(WorkCenters, timeGranularity)
    ############################## Start Branch-and-price ##############################
    
    
    
    InitializeMachineTimes(WorkCenters, [i for i in range(0,(tau_value+horizonExtension)*1440, timeGranularity)], timeGranularity)
    
    InitializeBenchMachineTimes(WorkCenters, [i for i in range(0,(tau_value+horizonExtension)*1440, timeGranularity)], timeGranularity)
    
    
    BenchmarkMILP = InitializeBenchMarkMILP(AMESelectedOrders, tau_value, horizonExtension, timeGranularity)
    
    schedules, objective_value = SolveBenchmarkMILP(AMESelectedOrders,2400,tau_value,timeGranularity,BenchmarkMILP)
    
    AMEOrders, AMEJobs,incumbentSol, Nodes, comptime = DoBPSearch(WorkCenters,AMESelectedOrders, AMEJobs, tau_value, timeGranularity,horizonExtension)
    
   
    
    ############################################## Store properties ############################################################
    storeNodeProperties(Nodes, tau_value, timeGranularity)
    storeSchedules(incumbentSol, tau_value, timeGranularity)

    
    return AMEOrders, AMEJobs, incumbentSol, Nodes


def CreateTask(order,refday, amount,product,successor, timeGranularity):
    
    remquantity = math.ceil(min(product.TargetLevels[int(refday//1440)],amount)) # the amount of product attached to order o
    fwddays = int(refday//1440)
    while fwddays < len(product.TargetLevels):
        product.TargetLevels[fwddays]-= remquantity
        fwddays+=1
          
    bwdquantity = remquantity
    bwddays = int((refday//1440)-1)
    
    while bwddays >= 0:
         bwdquantity = min(bwdquantity,product.TargetLevels[bwddays])
         product.TargetLevels[bwddays]-= bwdquantity
         
         if bwdquantity == 0:
             break
         bwddays-=1
  
    if remquantity > 0:
        UpdatedDeadline = min(refday, ((refday//1440) + (product.Operations[-1].OperationType.AlternativeMachines[0].UpTimePerDay/24))*1440)
        
        currtask = AMETask(len(product.WorkCenter.Tasks)+1,product,remquantity,UpdatedDeadline,order.OrderID, order)
        if successor is not None:
           currtask.Successors.append(successor)
           successor.Predecessors.append(currtask)
        else:
            currtask.setFinal()
        
        product.WorkCenter.Tasks.append(currtask)

        StartTime = refday
        CurrentTime = refday
        for idx in range(len(product.Operations)-1,-1,-1):
            day = CurrentTime//1440

            operation = product.Operations[idx]
            if operation.ProcessTime != 0:
                ProcessTime = ((((operation.ProcessTime * remquantity)  + operation.SetupTime)//timeGranularity)+1)*timeGranularity
            else: ProcessTime = 0
            
            RemainingProcTime = ProcessTime

            AlternativeMachines = operation.OperationType.AlternativeMachines
            
            
            while RemainingProcTime > 0:
                dayUse = min(CurrentTime - round(day*1440), RemainingProcTime)
                RemainingProcTime -= dayUse
                StartTime = CurrentTime-dayUse

                day -= 1
                
                CurrentTime = day*1440 + AlternativeMachines[0].UpTimePerDay * 60

            CurrentTime = StartTime
      
        for pred in product.Predecessors:
            CreateTask(order,CurrentTime, pred[1]*remquantity,pred[0],currtask, timeGranularity)
     
    return

######################################################################################################################################


############################## Production scheduling ##############################

def ConvertJobs(WorkCenters, timeGranularity, tau_value, horizonExtension):
      
    '''
      This function converts tasks into jobs at workcenters.
      Once the jobs are created, they are passed to Scheduling module.    
    ''' 
    
    
    AMEJobs = dict()
    AMESelectedOrders = dict()
    jobid = 0
    TaskID = 0
    # convert task to set of jobs and update deadlines of corresponding job
    
    
    
    
    for name, workcnt in WorkCenters.items():
        for task in workcnt.Tasks:
            mycurrent_deadline = task.Deadline
            prefjob = None
            Quantity = math.ceil(task.Quantity * (1 + task.Product.ScrapRate))
            UpdatedDeadline = min(task.Deadline, (task.Deadline- 1 + (task.Product.Operations[-1].OperationType.AlternativeMachines[0].UpTimePerDay/24))*1440)
            day = UpdatedDeadline//1440
            CurrentTime = UpdatedDeadline
            
            # go backward through operations of task
            for idx in range(len(task.Product.Operations)-1,-1,-1):
                operation = task.Product.Operations[idx]
                
                if operation.ProcessTime != 0:
                    ProcessTime = ((((operation.ProcessTime * Quantity)  + operation.SetupTime)//timeGranularity)+1)*timeGranularity
                else: ProcessTime = 0
                
                AlternativeMachines = operation.OperationType.AlternativeMachines
                
                     
                myJob = AMEJob(jobid, TaskID, task, task.OrderID, task.myOrder, task.Deadline, task.Product, workcnt, AlternativeMachines, ProcessTime, Quantity)
                RemainingProcTime = ProcessTime
                myJob.SetDeadlineMinutes(CurrentTime)
                
                # update current time for next previous operation
                while RemainingProcTime > 0:
                    dayUse = min(CurrentTime - round(day*1440), RemainingProcTime)
                    RemainingProcTime -= dayUse
                    StartTime = CurrentTime - dayUse
                    day -= 1
                    CurrentTime = day*1440+myJob.AlternativeMachines[0].UpTimePerDay*60
                    
                CurrentTime = StartTime
                
                
                
                
                if prefjob != None:
                    myJob.Successors.append(prefjob)
                    prefjob.Predecessors.append(myJob)
                    
                
                if myJob.Deadline < 0:
                    print('******Task',task.ID,'for prod.',task.Product.PN,', d',task.Deadline,'successor tasks',[succ.ID for succ in task.Successors])
                workcnt.Jobs.append(myJob)
                task.Jobs.append(myJob)
                # WorkCenters.AllJobs.append(myJob)
                AMEJobs[myJob.JobID] = myJob
                jobid += 1
                prefjob = myJob
                
            task.ID = TaskID
            TaskID += 1


    # update predecessor and successor for fist job in task
    for name,workcnt in WorkCenters.items():
        for task in workcnt.Tasks:
            if len(task.Successors) == 0:
                RecursiveProductionPass(task)
    
    for JobID, myJob in AMEJobs.items():
        myJob.setRollingPredsToSchedule()
        if len(myJob.Successors) == 0:
            myJob.Order.FinalJob = myJob
            myJob.IsFinal = True
            
            
            myJob.RecursiveRemCompUpdate(myJob, 0, 0)
        if len(myJob.Predecessors) == 0:
            myJob.IsStart = True
            myJob.Order.StartJobs.append(myJob)
            
        if len(myJob.Predecessors) > 1:
            myJob.Order.SequentialOrder = False
        
        myJob.Order.Jobs.append(myJob)

            
######################################### Include sequential Orders ##########################################    
    # OrderCounter = 0
    # for JobID, myJob in AMEJobs.items():
    #     if myJob.IsFinal:
    #         # AMESelectedOrders[myJob.Order.OrderID] = myJob.Order
    #         OrderCounter += 1
    #         if myJob.Order.SequentialOrder:
    #             AMESelectedOrders[myJob.Order.OrderID] = myJob.Order
                
    # print('\n')
    # print('Number of Orders: ', OrderCounter)
    # print('Number of Sequential Orders: ', len(AMESelectedOrders))
    # print('\n')
    # print('Number Of Jobs: ', len(AMEJobs))
    # AMEJobsCopy = AMEJobs.copy()
    # for JobID, myJob in AMEJobsCopy.items():
    #     if not myJob.Order.SequentialOrder:
    #         del AMEJobs[JobID]
    # print('Total Number Of Sequential Jobs: ', len(AMEJobs))
    
    
    ########################################################################################################
    ######################################### Include All Orders ##########################################    
    OrderCounter = 0
    for JobID, myJob in AMEJobs.items():
        if myJob.IsFinal:
            AMESelectedOrders[myJob.Order.OrderID] = myJob.Order
            OrderCounter += 1

    print('   >> Number of Orders with jobs: ', OrderCounter)
    
    
    ########################################################################################################
    # create properties for greedy intial solution model 
    maxRollingWeight = 0
    for JobID, myJob in AMEJobs.items():
        RollingWeight = myJob.Order.Deadline*1440 + myJob.RemainingProcTime + myJob.succsToSchedule*1000
        maxRollingWeight = max(maxRollingWeight, RollingWeight)
        
    for JobID, myJob in AMEJobs.items():
        myJob.RollingWeight = (myJob.Order.Deadline*1440 + myJob.RemainingProcTime + myJob.succsToSchedule*10)/maxRollingWeight
     
        
    # set Lower and upperbound for Arcs
    for OrderID, myOrder in AMESelectedOrders.items():
        for myStartJob in myOrder.StartJobs:
            # lowerbound for job
            RecursiveForward(myStartJob, 0, timeGranularity)
    
        # MaxCompTime = round((timeHorizon//1440 -1 +myOrder.FinalJob.MachineOptions[0].OffTimes[timeHorizon//1440])*1440)
        MaxCompTime = round((tau_value+horizonExtension-1)*1440 +((myOrder.FinalJob.AlternativeMachines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity)
        # Upperbound for arc
        RecursiveBackward(myOrder.FinalJob,MaxCompTime,0,timeGranularity)

    return AMEJobs, AMESelectedOrders


##################################################################

def RecursiveProductionPass(task):
    noPredJob = None
    for job in task.Jobs:
        if len(job.Predecessors) == 0:
            noPredJob = job
            break

            
    for predtask in task.Predecessors:
        for job in predtask.Jobs:
            if len(job.Successors) == 0:
                job.Successors.append(noPredJob)
                noPredJob.Predecessors.append(job)
                break
        
        RecursiveProductionPass(predtask)



###################################################################

def RecursiveForward(myJob, LowerBound, timeGranularity):
    
    day = int(LowerBound//1440)
    machines = myJob.AlternativeMachines

    UpTimeMin = ((machines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity
    CurrentTime = LowerBound
    if LowerBound >= day*1440+ UpTimeMin:
        CurrentTime = (day+1)*1440
        day += 1

    
    
    myJob.setStartLB(CurrentTime)
    RemainingProcTime = myJob.ProcessingTime
    CompTime = CurrentTime
    
    while RemainingProcTime > 0:
        dayUse = min(round(day*1440+UpTimeMin,0) - CurrentTime, RemainingProcTime)
        
        CompTime = CurrentTime + RemainingProcTime
        
        RemainingProcTime -= dayUse

        day += 1
        CurrentTime = day*1440
        if CompTime >= (day-1)*1440+UpTimeMin:

                
            CompTime = max(CompTime, CurrentTime)
        
    for mySucJob in myJob.Successors:
        RecursiveForward(mySucJob, CompTime, timeGranularity)
        
        
#############################################################################################################
        
def RecursiveBackward(myJob, UpperBound,count,timeGranularity):
    day = int(UpperBound//1440)
    
    machines = myJob.AlternativeMachines
    
    machinedayontime = ((machines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity
    
    CurrentTime = min(UpperBound,day*1440+machinedayontime)
    RemainingProcTime = myJob.ProcessingTime
    StartTime = CurrentTime
    
    while RemainingProcTime > 10**-4:
        dayUse = min(CurrentTime - round(day*1440), RemainingProcTime)
        StartTime = int(CurrentTime - RemainingProcTime)
        RemainingProcTime -= dayUse
        day -= 1
        CurrentTime = day*1440+machinedayontime
        
    myJob.setStartUB(StartTime)
  
    #print(count,'->Job ',myJob.JobID,', Upperbound',UpperBound,', startUB',myJob.StartUB,', process time',myJob.ProcessingTime,', machine day on time',machines[0].UpTimePerDay*60)
    

    for mySucJob in myJob.Predecessors:
        RecursiveBackward(mySucJob, StartTime,count+1,timeGranularity)




                          