# -*- coding: utf-8 -*-
"""
Created on Wed Dec 30 2020

@author: mfirat
Disclaimer:
This implementation is developed under AME-TUE/OU collaborations. 

The contributing students: 
    - Julie de Meyere (TUE, MSE graduate, Nov. 2020)
    - Suzanne Voorn (TUE, OML graduate, Apr. 2021)
    - Sven Ruiter (TUE, OML graduate, Oct. 2021)

"""

import pandas as pd
import time



from WorkloadAlg import ConstrucMILPModel,SolveWhatModel,WriteWhatSolution
from InputReader import InitializeAMEProductionSystem,InitializeAMEProducts,InitializeAMEOrders

from datetime import datetime

######## DO NOT CHANGE ANY CODE IN BETWEEN THESE LINES ########

def RunProductionControl(instance, Date):
  
    tau_Value = instance[0]
    horizonExtension = instance[1]
    timeGranularity = instance[2]
    
    print('******************  [AME AUTOMATED PLANNING]  ******************')
    TimeConvention = [5, 60] # [days of week, minutes of hour]
    #import file
    prodsysfile = 'DataSets/AMEResources_'+str(Date)+'.csv'
    procroutefile = 'DataSets/AMEWorkcenterOperationRoutes_'+str(Date)+'.csv'
    AMEStockFile = 'DataSets/AMEStockLevels_'+str(Date)+'.csv'
    AMEProductFile = 'DataSets/AMEProductInformation_'+str(Date)+'.csv'
    AMEOrderFile = 'DataSets/AMEOrderInformation_'+str(Date)+'.csv'

    print('<----------------- INITIALIZATION PHASE  ----------------->')
  
    print('>>> Initializing Production system..')
    AMEWorkCenters = InitializeAMEProductionSystem(prodsysfile,procroutefile,timeGranularity)
    print('-------------------------------------------------------------')
    print('>>> Initializing Products..')
    AMEProducts = InitializeAMEProducts(AMEWorkCenters,AMEProductFile,AMEStockFile,Date)
    print('-------------------------------------------------------------')
    print('>>> Initializing Orders..')
    AMEOrders = InitializeAMEOrders(AMEProducts,AMEOrderFile)


    WorkloadFindingStart = time.time()
    TimeLimit = 60 # set a maximum time limit for running the model
    CustomerTolerance = 10 #Customer Order Delay Tolerance in days
    
    ########################################## workload optimization  ##################################################
    print()
    print('<----------------- PLANNING PHASE 1: Workload Optimization ----------------->')
    
    print('>>Time Limit:',TimeLimit,' sec., Tau =',tau_Value,' days., Customer Tolerance:',CustomerTolerance,' days')
    primal,timelength_day,OrdersInModel,AMEProducts = ConstrucMILPModel(AMEOrders,AMEProducts,AMEWorkCenters,CustomerTolerance, tau_Value, timeGranularity)
    print('   >> Model construction in ',round((time.time()-WorkloadFindingStart),2),'secs.')
     
    Acceptedorders = SolveWhatModel(primal,TimeConvention[1],TimeConvention[0],TimeLimit,tau_Value,OrdersInModel,AMEProducts,CustomerTolerance,AMEWorkCenters,timeGranularity)
  

    ########################################## production scheduling ##################################################
    start_time = time.time()
    
    
    
    return AMEOrders

######## DO NOT CHANGE ANY CODE IN BETWEEN THESE LINES ########

############################## Parameters ############################################
# for date see input file names
Date = 20210301 #nietveranderen
TimeHorizon = 5
HorizonExtension = 3 # In case of a to small horizon extension the greedy scheduling model will fail
TimeGranularity = 120 # Multiple of TimeGranularity should be a equal to 1440


############################## start run #################################################
starttime = time.time()
instance = [TimeHorizon,HorizonExtension,TimeGranularity]
AMEOrders = RunProductionControl(instance, Date)
print('>>> Total computation time: ', round(time.time() - starttime,3),' secs.')


#%%