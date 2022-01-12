# -*- coding: utf-8 -*-
"""
Created on Sat Jan 23 11:11:03 2021

@author: mfirat
"""

import gurobipy as grb
import time


##########################################################################################################

def InitializePrimal(Orders, WorkCenters, timeUnits, timeGranularity):
    
    # build primal
    primal = grb.Model("AME_Prod_Scheduling")
    primal.modelSense = grb.GRB.MINIMIZE
    primal.Params.outputFlag = 0

    bigM1 = 10**9
    bigM2 = 10**6
    # bigM3 = 10**4
    
    dummy_var = primal.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
    
    # allcomp = 0
    
    for name,myworkcnt in WorkCenters.items():
        for mymachine in myworkcnt.Machines:
            for timePoint in timeUnits:
                cname = 'Cons_m_'+ str(mymachine.Name)+ '_t'+str(timePoint)
                
                artificialMachVar = primal.addVar(vtype=grb.GRB.CONTINUOUS,lb = 0, ub = 0, name="arMach_"+mymachine.Name+'_t'+str(timePoint))
                mymachine.MasterArtMachVar[timePoint] = artificialMachVar
                mymachine.MasterLPCons.append(primal.addConstr(dummy_var <= 1 + artificialMachVar,cname))
                
                mymachine.DualWeights.append(0)
                
    for OrderID, myOrder in Orders.items(): 
        cname = 'Cons_o_'+str(OrderID)               
        artificial_var = primal.addVar(vtype=grb.GRB.CONTINUOUS,obj = bigM1 ,lb = 0, ub = 1, name="avar_"+str(OrderID))
        myOrder.MasterLPCons = primal.addConstr(artificial_var == 1 ,cname)
        myOrder.MasterArtVar = artificial_var
                        
     
    primal.update() 

   
   
    return primal

###############################################################################################      
def SolveMaster(primal,nodeid,cgiter,WorkCenters, Orders):  
    
    # primal.write('LPFiles/AME_HOW_'+str(nodeid)+'_'+str(cgiter)+'.lp')
    primal.Params.outputFlag = 0
    primal.optimize()
    
    
    selectedschedules = {}
    
    selectedschedulesstr=  ''
    
    #print('***************  Master LP solution (N'+str(nodeid)+'_'+str(cgiter)+') *******************')
    
    #print('----> Primal solution: obj=',round(primal.objVal,2),' <----')
    
    artvarstr =  '-->> Artificial vars:'
    artvarcounter = 0
    artvarSUM = 0
    schedulescounter = 0

    
    # IntegerSolution = True
    for OrderID, myOrder in Orders.items(): 
        # print()
        if round(myOrder.MasterArtVar.x,2) != 0:
            artvarstr+= 'O_'+str(OrderID)+': '+str(round(myOrder.MasterArtVar.x,2))+', '
            artvarcounter += 1
            artvarSUM += myOrder.MasterArtVar.x

        myOrder.MasterLPDual = myOrder.MasterLPCons.pi
        SchIndex = 0
        SolutionSum = 0
        for Schedule in myOrder.Schedules:
            if Schedule.MPLambdaVar.ub >= 1-10**-4:
                schedulescounter += 1
            xval = Schedule.MPLambdaVar.x 
            if xval >= 10**-4:
                selectedschedules[Schedule]=xval
                
                
                SolutionSum += xval
                 
                # if not (int(xval) == int(xval-10**-4)+1 or int(xval)+1 == int(xval+10**-4)):
                #     IntegerSolution = False
                if SolutionSum >= 1 - 10**-4:
                    break
            SchIndex+=1
    selectedschedules = {k: v for k, v in sorted(selectedschedules.items(), key=lambda item: -item[1])}
    integerCounter = 0
    for schedule in selectedschedules:
        check = ''
        if schedule.Branched:
            check = '*'
            # if schedule.MPLambdaVar.x <= 1-10**-4:
            #     print('Error: '+ str(list(schedule.MPSchedule.values())[0][0][0].Order.OrderID)+'_'+ str(schedule.id) + 'not integer')
        selectedschedulesstr+=' '+str(list(schedule.MPSchedule.values())[0][0][0].Order.OrderID)+'_'+ str(schedule.id)+' x='+str(round(schedule.MPLambdaVar.x ,3))+check+','
        if schedule.MPLambdaVar.x >= 1-10**-4:
            integerCounter += 1

    #print('Selected Schedules: ', len(selectedschedules), 'Integer: ', integerCounter)
        
    for name,myworkcnt in WorkCenters.items():
        
        for myMachine in myworkcnt.Machines:
        
            TotalSlack = 0
            Times = 0
            myMachine.DualWeights.clear()
            for MPcons_ in myMachine.MasterLPCons:  
                TotalSlack+=MPcons_.Slack
                Times+=1
                myMachine.DualWeights.append(abs(MPcons_.pi))
            myMachine.setCapUse(1-(TotalSlack/Times))
            #print('Machine',myMachine.Name,' CapUse: ',myMachine.getCapUse())
            # print(myMachine.Name, myMachine.DualWeights)
   
  
    #print(artvarstr)
    # print('>>> Selected schedules: ')
    # print(selectedschedulesstr)
    
    IntegerSolution = (integerCounter == len(Orders))
    
    integer = 0
    if IntegerSolution:
        print('Primal solution is integer!')
        integer = 1

    
    #print('***************  Master LP solution (N'+str(nodeid)+'_'+str(cgiter)+') *******************')    
    
    # print('schedulescounter', schedulescounter,'!!!!!!!!!!!!!')
    MasterProperties = [artvarcounter,artvarSUM, selectedschedules, schedulescounter]
    return primal,primal.objVal, IntegerSolution, MasterProperties,integerCounter
###############################################################################################

def AddScheduleToMaster(primal,Order,schedule,timeGranularity):
    # bigM2 = 10**6
    
    machineCapCons = []
    # tardiness = 0
    for myMachine, tuples in schedule.MPSchedule.items():
        for job, timePoints in tuples:
            for timePoint in timePoints:
                machineCapCons.append(myMachine.MasterLPCons[int(timePoint/timeGranularity)])
                
    # print(tardiness, '_', index, '     ', Order.OrderID)
    schedule.MPLambdaVar = primal.addVar(obj = schedule.tardiness, vtype=grb.GRB.CONTINUOUS, name='y_o'+str(Order.OrderID)+'_s'+str(schedule.id))
    primal.chgCoeff(Order.MasterLPCons,schedule.MPLambdaVar,1.0)
    
    for machCapCons in machineCapCons:
        primal.chgCoeff(machCapCons,schedule.MPLambdaVar,1.0)

    primal.update() 
    return 

def SolveILPMaster(primal,nodeid,cgiter,WorkCenters, Orders):

    # primal.write('LPFiles/AME_HOW_'+str(nodeid)+'_'+str(cgiter)+'.lp')
    primal.Params.outputFlag = 0
    primal.optimize()
    
    
    selectedschedules = []
    
    selectedschedulesstr=  ''
    
    print('***************  Master -ILP- solution (N'+str(nodeid)+') *******************')
    
    print('----> Primal solution: obj=',round(primal.objVal,2),' <----')
    
    artvarstr =  '-->> Artificial vars:'
    for OrderID, myOrder in Orders.items(): 
        # print()
        artvarstr+= 'O_'+str(OrderID)+': '+str(round(myOrder.MasterArtVar.x,2))+', '
        SchIndex = 0

        for Schedule in myOrder.CurrentBPSchedules:
            # print(Schedule.MPLambdaVar)
            xval = Schedule.MPLambdaVar.x 
            if xval >= 10**-6:
                selectedschedules.append(Schedule)
                selectedschedulesstr+=' '+str(myOrder.OrderID)+'_'+ str(SchIndex)+' x='+str(round(xval,2))+','
                        
            SchIndex+=1


                     
    print(artvarstr)
    print('>>> Selected schedules: ')
    print(selectedschedulesstr)
                     
    # if writeTextSol:
    #     primal.write('LPFiles/'+'(N'+str(nodeid)+'_'+str(cgiter)+')_Pricing.lp')
    
    print('***************  Master -ILP- solution (N'+str(nodeid)+') *******************')              

    return primal,primal.objVal,selectedschedules
             
             
             

             
