# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 11:09:53 2020

@author: mfirat and sruiter
Topic of the following publication: 
  Firat, M., De Meyere, J., Martagan, T., Genga, L.,
  “Optimizing the workload of production units in a make-to-order manufacturing system”, 
  2021, Journal of Computers and Operations Research
"""



import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import gurobipy as grb
import math
import time
from datetime import datetime
# from Objects.ProductionObjects import Product,Workcenter,Machine
from Objects.PlanningObjects import AMEOrder,AMETask
from OutputWriter import WriteMachineCapacityUse
from ProductionScheduling import CreateTask


def ConstrucMILPModel(AllOrders,Products,WorkCenters,CustomerTolerance, tau_value, timeGranularity):
    "In this function the MILP model is constructed"
    "The numbers of the constraints are identified with Constraint (X). The 'cname' constraint name is based on an older version of the numbering"
    primal = grb.Model("AME_WHAT")
    primal.modelSense = grb.GRB.MINIMIZE
    independentorders = 0
    Orders = dict()
    Orders2 = dict()
    Orders3 = dict()
    
    RejectedOrderList = [] # droped orders based on unrealistic deadline
    
    for OrderID, myOrder in AllOrders.items():
        myOrder.FindLatestStartTime(tau_value, timeGranularity)
        
    counter = 0
    for OrderID, myOrder in AllOrders.items():
        if myOrder.getLatestStartDay() > tau_value:
            independentorders+=1
            # RejectedOrderList.append(OrderID)
            continue      
      
        if myOrder.Deadline > tau_value:
            if myOrder.getLatestStartDay() < 0:
                RejectedOrderList.append(OrderID)
                continue
        else:
            if myOrder.getLatestStartDay() + min(CustomerTolerance,tau_value-myOrder.Deadline) < 0:
                RejectedOrderList.append(OrderID)
                continue
        counter
                
        Orders[OrderID] = myOrder
               
        if myOrder.getLatestStartDay() <= tau_value+5:
            if myOrder.getLatestStartDay() + CustomerTolerance >= 0:
                Orders2[OrderID] = myOrder
        if myOrder.getLatestStartDay() <= tau_value+10:
            if myOrder.getLatestStartDay() + CustomerTolerance >= 0:
                Orders3[OrderID] = myOrder
   
    print('   >> No. feasible orders: ', len(Orders))
    #print('filtered Orders', tau_value+5,'Lengh: ', len(Orders2))
    #print('filtered Orders', tau_value+10, 'Lengh: ', len(Orders3))

    print('   >> Orders with consideration interval later than tau:',independentorders)
    print('   >> Orders with negative latest start and deadline later than tau:',len(RejectedOrderList))
    #print(RejectedOrderList)
 

    rejectcoeff = 10**6
    
    print('>>> Constructing WHAT model..')
 
    # time horizon in days
   
    dummy_var = primal.addVar(vtype=grb.GRB.CONTINUOUS, ub = 0, name="dummy")
    
           
    # machine set capacities..
    machinesubsetID = 0
    for name,workcnt in WorkCenters.items():
        for myMachSubset in workcnt.MachineSubSetList:
            totalcap = 0
            for day in range(tau_value): 
                totalcap += sum([machine.OnTimeGivenDay(day, timeGranularity) for machine in myMachSubset.Machines])    
                subcapcons = primal.addConstr(dummy_var <= totalcap,'MSubID'+ str(machinesubsetID) +'_d'+str(day))

                myMachSubset.MachSubsetCons.append(subcapcons)
                myMachSubset.CapacityUseVars.append([])
            
            machinesubsetID += 1

    # decision variables
    for order in Orders.values():
        rend = min(order.Deadline+CustomerTolerance, tau_value-1)
        rstart = min(order.Deadline+max(-order.getLatestStartDay(), 0), tau_value-1)


        # shifts are in days      
        for shifttime in range(rstart,rend+1):
            shiftname = 'tht_'+str(order.OrderID)+'_'+str(shifttime)
            thetavar = primal.addVar(obj = max(0,shifttime-order.Deadline), vtype=grb.GRB.BINARY, name= shiftname)
            order.ShiftVars.append(thetavar) #theta_o_t
                
             
        varname = 'rj_'+str(order.OrderID) 
        order.RejectVar = primal.addVar(obj = rejectcoeff, vtype=grb.GRB.BINARY, ub=1, name= varname)
        cname = 'Act_'+str(order.OrderID)
        #\sum_{t} \theta_{o,t} + r_o >= 1
        order.Constraints.append(primal.addConstr(sum(order.ShiftVars) + order.RejectVar >= 1,cname))
        
    for product in Products.values():
        
        for day in range(tau_value):
                
            # create variables: I_i_t, K_i_t , and Phi_{i,t}
            
            targetvar = primal.addVar(vtype=grb.GRB.CONTINUOUS,name = 'I_'+str(product.PN)+'_'+str(day))    
            prodvar = primal.addVar(obj = 1,vtype=grb.GRB.CONTINUOUS, name= 'K_'+str(product.PN)+'_'+str(day)  )            
            setupvar = primal.addVar(vtype=grb.GRB.CONTINUOUS, name= 'phi_'+str(product.PN)+'_'+str(day) ) # Phi_{i,t}
         
            product.TargetVars.append(targetvar)
            product.ProductionVars.append(prodvar)
            product.SetupVars.append(setupvar)
            
            # Capacity use constraints
            # \sum_{i}(s_{i}Phi_{i,t}+p_{i}K_{i,t} <= t U_{r}, below K_{i,t} and phi_{i,t} are added
            
            for myoperation in product.Operations:
                
                for subset in myoperation.OperationType.IncludingMachineSubsets:
                    subset.CapacityUseVars[day].append([myoperation.ProcessTime,prodvar])
                    subset.CapacityUseVars[day].append([myoperation.SetupTime,setupvar])
                    primal.chgCoeff(subset.MachSubsetCons[day],prodvar,myoperation.ProcessTime)
                    primal.chgCoeff(subset.MachSubsetCons[day],setupvar,myoperation.SetupTime)


            # Batch_i*h{i,t} >= K_{i,t}, // here time is in days, but unit of workload in constraint is minute.
            stname = 'Setup'+str(product.PN)+"_"+str(day)
            product.SetupCons.append(primal.addConstr(prodvar <= product.AvgBatch*setupvar, stname))
            
            cname = 'Tgt_Prod_'+str(product.PN)+"_"+str(day)
            primal.addConstr(targetvar <= product.StockLevel + prodvar, cname)
            
            # Here we initialize production target level constraints for each product
            cname = 'Consvr'+str(product.PN)+"_"+str(day)
            
            if day > 0:
                # I_i_t - I_i_t-1 = 0  
                # later add contributions of orders to the targets as \alpha_{i,o}*q_o*\theta_{o,t'}
                constraint = primal.addConstr(product.TargetVars[-1] - product.TargetVars[-2] == 0 ,cname)
                product.TargetStockCons.append(constraint)
                                 
            else:
                constraint = primal.addConstr(product.TargetVars[-1]  == 0, cname)
                product.TargetStockCons.append(constraint)
                

    for order in Orders.values():
        rend = min(order.Deadline+CustomerTolerance, tau_value-1)
        rstart = min(order.Deadline+max(-order.getLatestStartDay(), 0), tau_value-1)
        
        
        quantity = int(order.Quantity*(1+order.Product.ScrapRate))
        if order.Deadline > tau_value:
            quantity = int(((tau_value-order.getLatestStartDay())/(order.Deadline-order.getLatestStartDay()))*(order.Quantity*(1+order.Product.ScrapRate)))
       
        
        # print('OrderID: ', order.OrderID, 'rstart:', rstart, 'rend', rend, 'lStart', order.getLatestStartDay(), order.Deadline)
        for day in range(rstart,rend+1):# (rstart,rend+1) creates conflict devide by zero
            
            UpdateStockLevelCons(day,order.ShiftVars[day-rstart],quantity,primal,order.Product,timeGranularity)
            
    primal.update()
    
    #primal.write('LPFiles/LastversionWHAT.lp')

    return [primal,tau_value,Orders,Products]
##############################################################################################    
def UpdateStockLevelCons(refday,theta,quantity,primal,product, timeGranularity):
    # print('refday: ', refday)
    
     # I_{i_t} = I_{i_t-1} + \alpha_{i,0}*q_{o,t}*\theta_{o,t}, here    
     
    primal.chgCoeff(product.TargetStockCons[int(refday)],theta,-quantity)
    CumulativeDays = 0
    for operation in product.Operations:
        currentshift = operation.ProcessTime*quantity+ operation.SetupTime*(quantity/product.AvgBatch)
        MachineOnTime = ((operation.OperationType.AlternativeMachines[0].UpTimePerDay*60)//timeGranularity)*timeGranularity
        CumulativeDays += currentshift/MachineOnTime
        

    for myProd, Multiplier in product.Predecessors:
        predquantity = Multiplier*quantity*(1+myProd.ScrapRate)
        UpdateStockLevelCons(refday-CumulativeDays,theta,predquantity,primal,myProd,timeGranularity)

    return

###########################################################################################################


#############################################################################################################
def SolveWhatModel(primal,H2M,W2D,timelimit,tau_value,Orders,Products,CustomerTolerance,WorkCenters,timeGranularity):
    "Solves the model."
    
    # write the ILP model in an lp file  
    #primal.write('LPFiles/AME_WHAT.lp')
    start_time = time.time()
    primal.Params.outputFlag = 0
    primal.Params.timeLimit = timelimit
    primal.optimize() 
    acceptedorders = []  
    consideredorders = 0
    
    OptSolved = False
    SolnFound = True

    
    if primal.status == 2: 
        print('   >> WHAT model is solved optimally in ',round((time.time()-start_time),2),'secs., Objective = ',round(primal.objVal,3))
       # print('Running time:',round((time.time()-start_time),2),'secs.,',round((time.time()-start_time)/60,4),'minutes. Status:', primal.status)
 
        OptSolved = True

    else:
        print('   >> WHAT model is not solved optimally, status: ',primal.status,' in ',round((time.time()-start_time),2),'secs., Solutions ',primal.SolCount)
     #   print('Optimality gap', primal.MIPGGap)
        if primal.SolCount > 0:
      
            primal.Params.solutionNumber = 0
            print('   >> Objective = ',primal.objVal)  

        else:
            SolnFound = False
            if primal.status == 3:
                print('WHAT model is infeasible!!')
            else:
                print('No solution could be found of WHAT model in within time limit!!')
                
            
    
    # Turn on if you want to print what sol!!!!!!!!!!!!!!
    # WriteWhatSolution(Orders,Products)
    if SolnFound:
        
        WriteMachineCapacityUse(WorkCenters,tau_value,timeGranularity,OptSolved)
      
        countAccepted = 0
            # production (possibly shifted) deadlines of (non-rejected) orders are read from solution
        for order in Orders.values(): 
                
            consideredorders+=1
            if OptSolved:
                order.Rejected = order.RejectVar.x > 0.5
            else:
                order.Rejected = order.RejectVar.xn > 0.5
                
            order.SQuantity = 0
                
            if not order.Rejected:   
                    
                acceptedorders.append(order)
                rend = min(order.Deadline+CustomerTolerance, tau_value-1)
                rstart = min(order.Deadline+max(-order.getLatestStartDay(), 0), tau_value-1)
                    
                quantity = int(order.Quantity*(1+order.Product.ScrapRate))
                if order.Deadline > tau_value:
                    quantity = int(((tau_value-order.getLatestStartDay())/(order.Deadline-order.getLatestStartDay()))*(order.Quantity*(1+order.Product.ScrapRate)))
           
             
                order.SQuantity = quantity
                    
                for day in range(rstart,rend+1):  
                    if OptSolved:
                        if order.ShiftVars[day-rstart].x > 0.5:  
                            order.setSDeadLine(day+1)
                            break
                    else:
                        if order.ShiftVars[day-rstart].xn > 0.5:  
                            order.setSDeadLine(day+1)
                            break
                        
                countAccepted += 1
        print('   >> Accepted Orders: ',countAccepted,', Rejected Orders: ', len(Orders)-countAccepted)
            
        PrintOrderAcceptance(Orders,CustomerTolerance,tau_value) 
            
        for product in Products.values():
            for day in range(tau_value):
                if OptSolved:
                    product.TargetLevels.append(product.ProductionVars[day].x)
                else:
                    product.TargetLevels.append(product.ProductionVars[day].xn)
        PrintProductionTargets(Products,tau_value,OptSolved)
                  
    
    return acceptedorders

###########################################################################################
def WriteWhatSolution(Orders,Products):
    

    x = datetime.now() 
    infostr = x.strftime("%Y")+"_"+x.strftime("%m")+"_"+x.strftime("%d")
   
    write_file = 'DataSets/WhatSol_Orders_'+infostr+'.csv'
    
    with open(write_file, "w") as output:
        
        row = 'orderid'+','+'PN'+','+'WorkCenter'+','+'Customer'+','+'considerdate'+','+'deadline'+','+'targetdelivery'+','+'targetquantity'+','+'quantity'+','+'accepted'+"\n"    
        output.write(row)
        
        for order in Orders.values(): 
            
            row = str(order.OrderID)+','+str(order.Product.PN)+','+str(order.Product.WorkCenter.Name)+','+str(order.OrderID)+','+str(order.getLatestStartDay())+','+str(order.Deadline)+','+str(order.SDeadline)+','+str(order.SQuantity)+','+str(order.Quantity)+','+str(not order.Rejected)     
            row += "\n"
            output.write(row)
            
            
    write_file = 'DataSets/WhatSol_ProdTargets_'+infostr+'.csv'
    
    with open(write_file, "w") as output:
        
        row = 'ProductPN'+','+'Workcenter'
        
        for product in Products.values():
            for day in range(len(product.TargetLevels)):
                row+=','+'Day'+str(day)
            break    
            
        
        row+="\n"    
        output.write(row)
        
        for product in Products.values(): 
            row = str(product.PN)+','+product.WorkCenter.Name
            for day in range(0,len(product.TargetLevels)): 
                row += ','+str(product.TargetLevels[day])
            row += "\n"
            output.write(row)
########################################################################################           

def PrintOrderAcceptance(Orders,CustomerTolerance,tau_value):

    print('   _____________________________________________________')
    print('   >> WHAT Model results: Order Acceptance/Rejections...')
    
    for order in Orders.values(): 
     
        if not order.Rejected:   
            print('     > Accepted: Order',order.OrderID,'PN:',order.Product.PN,', ls:',order.getLatestStartDay(),', Target:',order.Deadline,'->',order.SDeadline,', Q:',order.Quantity,'->',round(order.SQuantity,2))
        else:
            print('     > Rejected: Order',order.OrderID,'PN:',order.Product.PN,', ls:',order.getLatestStartDay(),', d:',order.Deadline,',Quantity:',order.Quantity)
    return 
  
def PrintProductionTargets(Products,tau_value,optimal):
    
   print('   _____________________________________________________')
   print('   >> WHAT Model results: Production Targets..')

   for product in Products.values():
       total = 0
       prodreqstr = product.PN+': '
       for day in range(tau_value): 
           
           if optimal: 
               productval = product.ProductionVars[day].x
           else:
               productval = product.ProductionVars[day].xn
           prodreqstr+=','+str(round(productval,0))
           total+=productval
       if total > 0:
           print('     >'+prodreqstr) 
###################################################################################################          
