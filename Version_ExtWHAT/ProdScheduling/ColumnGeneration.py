# -*- coding: utf-8 -*-
"""

@author: mfirat
"""

import gurobipy as grb
import math
import time
# from Objects.PlanningObjects import Schedule
from Objects.BPObjects import Solution, CGProperties
from ProdScheduling.MasterLP import SolveMaster,AddScheduleToMaster#,ConvertSolveMaster
from ProdScheduling.PricingMILP import SolveExactPricingMILP
from ProdScheduling.PricingShortestPath import SolveExactPricingSP


########################  Scheduling framework of workcenters ####################################  



def ColumnGen(node,masterlp,WorkCenters,Orders,timelimit,TimeHorizon, timeGranularity):
    CGPropertiesList = []
    epsilon = 10**-6
    cgiter = 1
    maxiters = 2500
    
    minredcost = -1
        
     # Here Column Generation starts, it continues until any schedule with negative redcost is found.
     # The convergence of column generation is when pricing search cannot reach a negative schedule anymore
        
    integersol = None
    ExactAlgRun = False
    
    integerCounter = 0
    
     
   
    while minredcost < -epsilon:
         
        
        # master is solved, dual values are set
        starttimemaster = time.time()
        masterlp,mastersolval, IntegerSolution, MasterProperties,integerCounter = SolveMaster(masterlp,node.getID(),cgiter,WorkCenters, Orders)
        MasterCompTime = time.time() - starttimemaster
        starttimepricing = time.time()
    
        ColumnsNegRedCostCounter = 0
        NegRedCostColumns = []
        if IntegerSolution:
            if integersol is not None:
                if integersol.getObjValue()-10**-4 >= mastersolval:
                    integersol = Solution(mastersolval,node, selectedschedules)

                    
            else:
                integersol = Solution(mastersolval,node, selectedschedules)
                print('--->Node ',node.getID(),': IntegerSolution with obj value',integersol.getObjValue(),' is created!')
     
                
        if node.parent != None: 
            if mastersolval <= node.parent.getLBValue() + 10**-4:
                #print('---> Current RMP solution value ',mastersolval,' the parent lower bound ',node.parent.getLBValue(),' => terminating CG..')
                node.setLBValue(node.parent.getLBValue())
               # myCGProperty = CGProperties(cgiter, MasterCompTime, time.time() - starttimepricing, True, mastersolval, MasterProperties, ColumnsNegRedCostCounter)
               # CGPropertiesList.append(myCGProperty)
               
                return integersol, masterlp, selectedschedules, CGPropertiesList,cgiter,integerCounter  
                
            
        minredcost = - epsilon
        
        # -----  P R I C I N G   -----
        ExactAlgRun = True
        if ExactAlgRun:
            ExactCheck = 1
        else: ExactCheck = 0
        for OrderID, myOrder in Orders.items(): 
            if myOrder.Branched:
                continue
       
            if not ExactAlgRun: 
                orderschedule,redcost = SolveHeuristicPricing(myOrder,timelimit,TimeHorizon,cgiter)
            else: 
                orderschedule,redcost = SolveExactPricingMILP(myOrder,timelimit,TimeHorizon,cgiter,timeGranularity)
                
                minredcost = min(minredcost, redcost)
           
            if orderschedule != None:
                if redcost < -10**-6-5:
                    ColumnsNegRedCostCounter += 1
                    NegRedCostColumns.append(redcost)
                    #print('Sch(O'+str(OrderID)+'), rd=',round(redcost,2))
                        
                # if redcost < - epsilon: 
                if redcost < -10**-6-5:
                    myOrder.Schedules.append(orderschedule)
                    node.generatedcolumns.append(orderschedule)
                    
                    AddScheduleToMaster(masterlp,myOrder,orderschedule, timeGranularity)
        # -----  P R I C I N G   -----
             
        if minredcost >= - epsilon:
            if ExactAlgRun == False:
                ExactAlgRun = True
                minredcost = -2* epsilon
            
        PricingCompTime = time.time() - starttimepricing
        
            # iteration, mastercomptime, pricingcomptime, pricingcomptype, mastersolval
        myCGProperty = CGProperties(cgiter, MasterCompTime, PricingCompTime, ExactCheck, mastersolval, MasterProperties, NegRedCostColumns)
        CGPropertiesList.append(myCGProperty)
        cgiter +=1
        #print('Time now: ', time.time())
        if  cgiter >= maxiters:
            node.earlybranch = True
            break
        else:
            node.setLBValue(mastersolval)
    
        if -5< minredcost and minredcost < 0:
            minredcost = 0.1

        
    return integersol, masterlp, selectedschedules, CGPropertiesList,cgiter,integerCounter

#############################################################################################################################################
#############################################################################################################
def SolveHeuristicPricing(Order,timelimit,TimeHorizon,cgiter):
    myschedule = None

    return myschedule


    

