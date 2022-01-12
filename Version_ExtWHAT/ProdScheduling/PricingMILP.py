# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 10:44:56 2021

@author: mfirat
"""


import gurobipy as grb
from Objects.GraphObjects import MILPArc
from Objects.PlanningObjects import AMEOrderSchedule


def InitializeMachineTimes(WorkCenters, timeUnits, timeGranularity):
    
    for name,myworkcnt in WorkCenters.items():
        for mymachine in myworkcnt.Machines:
            
            for timePoint in timeUnits:
                mymachine.PricingMILPArcs.append([])
                
    return

def InitializeArcPricingMILP(myOrder, tau_value, horizonExtension, timeGranularity):
    

    
    myOrder.setPricingMILP(grb.Model('o_'+str(myOrder.OrderID)+'_Pricing_MILP'))
    
    # myOrder.PricingMILPTardCons = myOrder.PricingMILP.addConstr(-myOrder.SDeadline*1440 <= myOrder.PricingMILPTardVar, name='TardCons_o'+str(myOrder.OrderID))

    myOrder.PricingMILPTardCons = myOrder.PricingMILP.addConstr(-myOrder.SDeadline*1440 <= myOrder.PricingMILPTardVar, name='TardCons_o'+str(myOrder.OrderID))
       
    # timeHorizon = tau_value + horizonExtension
    # starttime = time.time()
    # LinearNodes = int((tau_value + horizonExtension)*1440/timeGranularity)
    # print('LenearNodes' ,LinearNodes)
    MachineList = []
    
    for myJob in myOrder.Jobs:
        for mySucJob in myJob.Successors:
            dummy_var = myOrder.PricingMILP.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
            myJob.PricingMILPPrecCons.append(myOrder.PricingMILP.addConstr(dummy_var  <= 0,'predCons_j'+str(myJob.JobID)+'_sucj'+str(mySucJob.JobID)))
            
        for myMachine in myJob.AlternativeMachines:
            myJob.getPricingMILPArcDict()[myMachine] = [] # MF (26-10-21) initializing the arclist of this specific machine
            if myMachine not in MachineList:
                MachineList.append(myMachine)
                for idx, arcList in enumerate(myMachine.PricingMILPArcs):
                    arcList.clear()
                # myMachine.PricingMILPArcs = []
            # for timePoint in range()
            # for timePoint in range(LinearNodes):

            for timePoint in range(0,(tau_value+horizonExtension)*1440, timeGranularity):
                day = timePoint//1440
                if timePoint < myJob.StartLB or timePoint > myJob.StartUB:
                    continue
                if myMachine.Availability[day] == 0:
                    continue
                if timePoint >= (day *1440) + myMachine.UpTimePerDay * 60:
                    continue
                myArc = MILPArc(timePoint, myJob, myMachine, timeGranularity, myOrder.PricingMILP)
                for Time in range(myArc.StartTime, myArc.CompTime, timeGranularity):
                    # print(Time, myArc.StartTime, myArc.CompTime, timeGranularity)
                    TimePoint = int(Time//timeGranularity)
                    try:
                        myMachine.PricingMILPArcs[TimePoint].append(myArc.PricingMILPVar)
                    except:
                        # print('dit is niet goed. file: GraphStructure', len(myMachine.PricingMILPArcs), TimePoint, Time, timeGranularity)
                        None
                if myJob.IsFinal:
                    myOrder.PricingMILP.chgCoeff(myOrder.PricingMILPTardCons,myArc.PricingMILPVar,- myArc.CompTime)
        
        myOrder.PricingMILP.addConstr(grb.quicksum(myJob.PricingMILPArcVars)  == 1,'OneArc_j'+str(myJob.JobID))
       
    for myJob in myOrder.Jobs:
        for myArc in myJob.PricingMILPArcs:
            for myPrecons in myJob.PricingMILPPrecCons:
                myOrder.PricingMILP.chgCoeff(myPrecons,myArc.PricingMILPVar,myArc.CompTime)
            for myPredJob in myJob.Predecessors:
                for myPrecons2 in myPredJob.PricingMILPPrecCons:
                    myOrder.PricingMILP.chgCoeff(myPrecons2,myArc.PricingMILPVar,-myArc.StartTime)

    for myMachine in MachineList:
        for idx, arcList in enumerate(myMachine.PricingMILPArcs):
            if len(arcList) == 0:
                continue
            myOrder.PricingMILP.addConstr(grb.quicksum([arcList[idx] for idx in range(len(arcList))])  <= 1,'OneArc_M'+myMachine.Name+'_t'+str(idx*timeGranularity))            
    
    
####################################################################################################################
def SolveExactPricingMILP(myOrder,timelimit,TimeHorizon,iterno, timeGranularity):
    # dummy_var = myOrder.PricingMILP.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
    # objExp = 2 * dummy_var
    objExp = myOrder.PricingMILPTardVar
    for myJob in myOrder.Jobs:
        for myArc in myJob.PricingMILPArcs:
            objExp = objExp + myArc.CallWeight(timeGranularity) * myArc.PricingMILPVar
        
    myOrder.PricingMILP.setObjective(objExp)
    
    
    myOrder.PricingMILP.update()
    myOrder.PricingMILP.Params.outputFlag = 0
    myOrder.PricingMILP.optimize()
    # myOrder.PricingMILP.write('LPFiles/AME_MILP_.lp')
    # stop
    
    SelectedArcs = []
    OrderSchedule = {}
    for myJob in myOrder.Jobs:
        for myArc in myJob.PricingMILPArcs:
            if myArc.PricingMILPVar.x > 0.5:
                SelectedArcs.append(myArc)
                if myArc.Machine in OrderSchedule:
                    OrderSchedule[myArc.Machine].append((myArc.Job, range(myArc.StartTime, myArc.CompTime, timeGranularity)))
                else:
                    OrderSchedule[myArc.Machine] = [(myArc.Job, range(myArc.StartTime, myArc.CompTime, timeGranularity))]
                if myJob.IsFinal:
                    JobCompletion = myArc.CompTime
                    # print(myOrder.SDeadline)
    tardiness = max( JobCompletion - myOrder.SDeadline*1440,0)
    myOrderSchedule = AMEOrderSchedule(OrderSchedule, tardiness, SelectedArcs)
    # myOrderSchedule.PrintSchedule()
    # print(myOrderSchedule.tardiness)
    myOrderSchedule.checkFeasibility()
    # print('OrderDeadline: ', myOrder.SDeadline*1440, 'ScheduleDeadline: ', JobCompletion, 'Tardiness ',tardiness , 'obj: ', myOrder.PricingMILP.objVal, 'tardyvar: ', myOrder.PricingMILPTardVar.x)
    
    reducedcost = myOrder.PricingMILP.objVal -  myOrder.MasterLPDual + 10**-6
    
    
    return myOrderSchedule, reducedcost #Orderschedule, redcost




#####################################################################################################################

def InitializeExclusion(OrderSchedule, myOrder):
    OrderSchedule.PricingRedundancyVar = myOrder.PricingMILP.addVar(lb=1, ub=1, vtype=grb.GRB.CONTINUOUS, name='redVar_o'+str(myOrder.OrderID))
    OrderSchedule.PricingMILPExclCons =  myOrder.PricingMILP.addConstr(grb.quicksum([arc.PricingMILPVar for arc in OrderSchedule.PricingMILPArcs])  <= len(myOrder.Jobs) - OrderSchedule.PricingRedundancyVar, name= 'SchExclCons_N'+str(myOrder.OrderID))
    OrderSchedule.MPLambdaVar.ub = 0
    
    return
    
    
def ActivateExclusion(OrderSchedule, myOrder):
    myOrder.PricingMILP.chgCoeff(OrderSchedule.PricingMILPExclCons,OrderSchedule.PricingRedundancyVar,1)  
    OrderSchedule.MPLambdaVar.ub = 0
    
    return
    
def DeactivateExclusion(OrderSchedule, myOrder):
    myOrder.PricingMILP.chgCoeff(OrderSchedule.PricingMILPExclCons,OrderSchedule.PricingRedundancyVar,-1)  
    OrderSchedule.MPLambdaVar.ub = 1
    
    return
    
#######################################################################################################################
def InitializeLNodePricingCons(JobMachAssign):
    
    for job,machine in JobMachAssign.getAssignDict().items():
        LNodeVar = JobMachAssign.order.PricingMILP.addVar(lb=1, ub=1, vtype=grb.GRB.CONTINUOUS, name='LNodeVar_o'+str(JobMachAssign.order.OrderID)+'_j'+str(job.JobID)+'_m_'+machine.Name)
        JobMachAssign.getLNodeVarDict()[job] = LNodeVar
        
        PricingFixingCons = JobMachAssign.order.PricingMILP.addConstr(grb.quicksum([arc.PricingMILPVar for arc in job.getPricingMILPArcDict()[machine]])  >=LNodeVar, name= 'AssignCons_o'+str(JobMachAssign.order.OrderID)+'_j'+str(job.JobID)+'_m_'+machine.Name)
        JobMachAssign.getLNodeConsDict()[job] = PricingFixingCons
        
    return   
        
###################################################################################################################
def InitializeRNodePricingCons(JobMachAssign):

    RNodeRedundancyVar = JobMachAssign.order.PricingMILP.addVar(lb=1, ub=1, vtype=grb.GRB.CONTINUOUS, name='RNodeVar_o'+str(JobMachAssign.order.OrderID))
    JobMachAssign.setRNodeRedundancyVar(RNodeRedundancyVar)
    
    ArcSumExpr = RNodeRedundancyVar
    
    for job,machine in JobMachAssign.getAssignDict().items():
        ArcSumExpr+=grb.quicksum([arc.PricingMILPVar for arc in job.getPricingMILPArcDict()[machine]])
    
    PricingExclusionCons = JobMachAssign.order.PricingMILP.addConstr(ArcSumExpr <= len(JobMachAssign.getAssignDict().keys()) , name= 'AssignRNodeCons_o'+str(JobMachAssign.order.OrderID))
    JobMachAssign.setRNodeCons(PricingExclusionCons)
        
    return   
###################################################################################################################
def ActivateLNodePricingCons(JobMachAssign):
    
    for job,machine in JobMachAssign.getAssignDict().items():
        JobMachAssign.order.PricingMILP.chgCoeff(JobMachAssign.getLNodeConsDict()[job],JobMachAssign.getLNodeVarDict()[job] ,1)  
    
    return
    
def DeactivateLNodePricingCons(JobMachAssign):
    
    for job,machine in JobMachAssign.getAssignDict().items():
        JobMachAssign.order.PricingMILP.chgCoeff(JobMachAssign.getLNodeConsDict()[job],JobMachAssign.getLNodeVarDict()[job] ,-1)  
    return
###################################################################################################################
def ActivateRNodePricingCons(JobMachAssign):
  
    JobMachAssign.order.PricingMILP.chgCoeff(JobMachAssign.getRNodeCons(), JobMachAssign.getRNodeRedundancyVar(),1)  
    
    return
    
def DeactivateRNodePricingCons(JobMachAssign):
    
    JobMachAssign.order.PricingMILP.chgCoeff(JobMachAssign.getRNodeCons(), JobMachAssign.getRNodeRedundancyVar(),-1)  
     
    return  