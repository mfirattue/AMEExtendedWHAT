# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 10:44:56 2021

@author: mfirat
"""


import gurobipy as grb
import time
from Objects.GraphObjects import MILPArc,BenchMILPArc
from Objects.PlanningObjects import AMEOrderSchedule

def InitializeBenchMachineTimes(WorkCenters, timeUnits, timeGranularity):
    
    for name,myworkcnt in WorkCenters.items():
        for mymachine in myworkcnt.Machines:
            
            
            for timePoint in timeUnits:
                mymachine.BenchmarkMILPArcs.append([])
                
    return


def InitializeBenchMarkMILP(Orders, tau_value, horizonExtension, timeGranularity):
    
    BenchmarkMILP= grb.Model('Benchmark_MILP')
    
    MachineList = []
    
    for OrderID, myOrder in Orders.items():
        
        myOrder.BenchmarkMILPTardVar = BenchmarkMILP.addVar(vtype=grb.GRB.CONTINUOUS,name = 'tau_o'+str(myOrder.OrderID)) 
        myOrder.BenchmarkMILPTardCons = BenchmarkMILP.addConstr(-myOrder.SDeadline*1440 <= myOrder.BenchmarkMILPTardVar, name='TardCons_o'+str(myOrder.OrderID))
   
    
    
        for myJob in myOrder.Jobs:
            
            for mySucJob in myJob.Successors:
                dummy_var = BenchmarkMILP.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
                myJob.BenchmarkMILPPrecCons.append(BenchmarkMILP.addConstr(dummy_var  <= 0,'predCons_j'+str(myJob.JobID)+'_sucj'+str(mySucJob.JobID)))
            
            for myMachine in myJob.AlternativeMachines:
                
                if myMachine not in MachineList:
                    MachineList.append(myMachine)
                    for idx, arcList in enumerate(myMachine.BenchmarkMILPArcs):
                        arcList.clear()
                   
    
                for timePoint in range(0,(tau_value+horizonExtension)*1440, timeGranularity):
                    day = timePoint//1440
                    if timePoint < myJob.StartLB :
                        continue
                    if timePoint > myJob.StartUB:
                        break
                    if myMachine.Availability[day] == 0:
                        continue
                    if timePoint >= (day *1440) + myMachine.UpTimePerDay * 60:
                        continue
                    myArc = BenchMILPArc(timePoint, myJob, myMachine, timeGranularity,BenchmarkMILP)
                    for Time in range(myArc.StartTime, myArc.CompTime, timeGranularity):
                        # print(Time, myArc.StartTime, myArc.CompTime, timeGranularity)
                        TimePoint = int(Time//timeGranularity)
                        try:
                            myMachine.BenchmarkMILPArcs[TimePoint].append(myArc.BenchmarkMILPVar)
                        except:
                            print('Job',myJob.JobID,', Range final',(tau_value+horizonExtension-1)*1440,'timepoint',timePoint,'st_ubtime',myJob.StartUB,'myJob.ProcessingTime',myJob.ProcessingTime,'completion time',myArc.CompTime,'machineuptime',myMachine.UpTimePerDay * 60)
                            print('dit is niet goed. file: GraphStructure', len(myMachine.PricingMILPArcs), TimePoint, Time, timeGranularity)
                            None
                    if myJob.IsFinal:
                        BenchmarkMILP.chgCoeff(myOrder.BenchmarkMILPTardCons,myArc.BenchmarkMILPVar,- myArc.CompTime)
            
            BenchmarkMILP.addConstr(grb.quicksum(myJob.BenchmarkMILPArcVars)  == 1,'OneArc_j'+str(myJob.JobID))
       
        for myJob in myOrder.Jobs:
            for myArc in myJob.BenchmarkMILPArcs:
                for myPrecons in myJob.BenchmarkMILPPrecCons:
                    BenchmarkMILP.chgCoeff(myPrecons,myArc.BenchmarkMILPVar,myArc.CompTime)
                for myPredJob in myJob.Predecessors:
                    for myPrecons2 in myPredJob.BenchmarkMILPPrecCons:
                        BenchmarkMILP.chgCoeff(myPrecons2,myArc.BenchmarkMILPVar,-myArc.StartTime)


    for myMachine in MachineList:
        for idx, arcList in enumerate(myMachine.BenchmarkMILPArcs):
            BenchmarkMILP.addConstr(grb.quicksum([arcList[idx] for idx in range(len(arcList))])  <= 1,'OneArc_M'+myMachine.Name+'_t'+str(idx*timeGranularity))            
    
    
    return BenchmarkMILP
####################################################################################################################
def SolveBenchmarkMILP(Orders,comptime, tau_value,timeGranularity,BenchmarkMILP):
    
    dummy_var = BenchmarkMILP.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
    objExp = dummy_var
    
    OrderSchedules = []
    MachineSchedules = dict()
    
    for OrderID, myOrder in Orders.items():
        objExp = objExp + myOrder.BenchmarkMILPTardVar
        
        
    start_time = time.time()       
    BenchmarkMILP.setObjective(objExp)        
    BenchmarkMILP.update()
    BenchmarkMILP.Params.outputFlag = 0
    BenchmarkMILP.Params.timeLimit = comptime
    BenchmarkMILP.optimize()
   
    if BenchmarkMILP.status == 2: 
        print('   >>>> Benchmark MILP model of tau=',tau_value,' is solved optimally in ',round((time.time()-start_time),2),'secs., Objective = ',round(BenchmarkMILP.objVal,3))
   

    else:
        print('   >>>> Benchmark model is not solved optimally, status: ',BenchmarkMILP.status,' in ',round((time.time()-start_time),2),'secs., Solutions ',BenchmarkMILP.SolCount)
        if BenchmarkMILP.SolCount > 0:
      
            BenchmarkMILP.Params.solutionNumber = 0
            print('   >> Objective = ',BenchmarkMILP.objVal)  

        else:
            if BenchmarkMILP.status == 3:
                print('Benchmark model is infeasible!!')
            else:
                print('No solution could be found of Benchmark model in within time limit!!')
       
    for OrderID, myOrder in Orders.items():    
        order_str = ''
        SelectedArcs = []
        OrderSchedule = {}
        
        jobidx = 0
        for myJob in myOrder.Jobs:
            for myArc in myJob.BenchmarkMILPArcs:
                if myArc.BenchmarkMILPVar.x > 0.5:
                    
                    SelectedArcs.append(myArc)
                    if myArc.Machine in OrderSchedule:
                        OrderSchedule[myArc.Machine].append((myArc.Job, range(myArc.StartTime, myArc.CompTime, timeGranularity)))
                    else:
                        OrderSchedule[myArc.Machine] = [(myArc.Job, range(myArc.StartTime, myArc.CompTime, timeGranularity))]
                        
                    if jobidx == 0:    
                        order_str+= 'j'+str(myJob.JobID)+'['+str(myArc.CompTime)+':'+str(myOrder.SDeadline*1440)+'] '
                    else:
                        order_str+= ',j'+str(myJob.JobID)+'['+str(myArc.CompTime)+':'+str(myOrder.SDeadline*1440)+'] '
                    if myJob.IsFinal:
                        JobCompletion = myArc.CompTime
            jobidx+=1
                       
                        # print(myOrder.SDeadline)
        tardiness = max( JobCompletion - myOrder.SDeadline*1440,0)
        myOrderSchedule = AMEOrderSchedule(OrderSchedule, tardiness, SelectedArcs)
        
        dictionary = {} 
        for machine, Tuples in myOrderSchedule.MPSchedule.items():
            if machine not in MachineSchedules:
                MachineSchedules[machine]=  []
           
            for myJob, ranges in Tuples:
                dictionary[myJob] = ranges
                MachineSchedules[machine].append([myJob,ranges])

       
        for myJob, times in dictionary.items():
            if len(myJob.Successors) != 0:
                if dictionary[myJob.Successors[0]].start < dictionary[myJob].stop:
                     print('Order: ', myJob.Order.OrderID, 'Precedence viol job:  ', myJob.Successors[0].JobID, 'Started before job: ', myJob.JobID, ' Compl')          
        OrderSchedules.append(myOrderSchedule)
        order_str = 'Order'+str(myOrder.OrderID)+'['+str(round(tardiness,0))+']'+'\n' +order_str
        print(order_str)
   
    
    
    for machine,schedule in MachineSchedules.items():
        #print('Machine: ',machine.Name,' schedule: ')
        schedule_str=' '
        schedule.sort(key = lambda x:x[1].start)
             
        for jobexec in schedule:
            #print(',J',jobexec[0].JobID,'[',jobexec[1].start,',',jobexec[1].stop,']')
            schedule_str+=',J'+str(jobexec[0].JobID)+'['+str(jobexec[1].start)+','+str(jobexec[1].stop)+']'
        print('>> Machine: ',machine.Name,' schedule: ')
        print(schedule_str)
    
      
    
    
    return OrderSchedules,BenchmarkMILP.objVal




#####################################################################################################################

