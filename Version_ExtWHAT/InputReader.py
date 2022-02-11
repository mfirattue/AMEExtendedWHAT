# -*- coding: utf-8 -*-
"""
Created on Mon May 24 17:56:54 2021

@author: VAIO
"""
import pandas as pd
import random

from Objects.ProductionObjects import AMEWorkcenter,AMEMachine,AMEProduct, AMERawMaterial, AMEOperation, AMEOperationType, Equipment,Worker
from Objects.PlanningObjects import AMEOrder
from PreProcessing import UpdateMachineSubsets,PrintMachineGroup,UpdateOprMachines,FindIncludingMachineSubSets

import ast
from datetime import datetime
import collections

compare = lambda x, y: collections.Counter(x) == collections.Counter(y)

         
             
#####################################################################################################################

def InitializeAMEProductionSystem(ResourceFile,RouteFile,timeGranularity):
    
    '''
        Def: Operation Type: Identified by a set of characteristic alternative machines. 
        Def: Operation: Belong to one operation type. 
        Def: Machine subset: A set of machines that are resource for an operation type. 
        
        Note: 
        > Operations of same operation type may have different processing times.
        > A machine may be involved in different subsets. 
        
    '''
    #ResourceFile: AMEResources_date.csv
    #RouteFile : AMEWorkcenterOperationRoutes_date.csv
    
    data_Resources = pd.read_csv(ResourceFile,sep =',')
  
    WorkCenterDict = {} # key: Workcenter name, value: workcenter object.
    
    OperationTypes = dict() # key operationtypename,  value: list of machines 
    
    
       
    
    for index in range(0, len(data_Resources)):
        
     
        WorkCnt = data_Resources.loc[index]['WorkCenter']
        
        
        if WorkCnt not in WorkCenterDict:  
            WorkCenterDict[WorkCnt] = AMEWorkcenter(WorkCnt)
            
        myWorkCnt = WorkCenterDict[WorkCnt]
        
        myName = data_Resources.loc[index]['Resource']
        myOprs = data_Resources.loc[index]['OperationTypes'].split('-')
        myUtil = data_Resources.loc[index]['Utilization'] 
        myAvailability = data_Resources.loc[index]['Availability'].split('-')       
        myOnTimePerDay = data_Resources.loc[index]['OnTimePerDay']      
        resourcetype = data_Resources.loc[index]['Resource_Type']
       
        # myopr is a list and we have to iterate this list to fill operations of mahine or equipment. 
        
        if resourcetype == 'machine':                
            mymachine = AMEMachine(myWorkCnt,myName,myOprs,myUtil,myAvailability,myOnTimePerDay)
            
            UpdateOprMachines(myOprs,OperationTypes,mymachine)
            myWorkCnt.Machines.append(mymachine)
         
            
        if resourcetype == 'worker':

            myworker = Worker(myWorkCnt,myName,myOprs,myAvailability)

            myWorkCnt.Workers.append(myworker)
            
            if WorkCnt == 'SA':
                if len(myWorkCnt.Workers) %4 == 0 and len(myWorkCnt.Workers) > 0:            
                    mymachine = AMEMachine(myWorkCnt,'SA_'+str(int(len(myWorkCnt.Workers)/2)),myOprs,myUtil,myAvailability,2*myOnTimePerDay) 
                    
                    UpdateOprMachines(myOprs,OperationTypes,mymachine)
                    myWorkCnt.Machines.append(mymachine) 
   
                    
            elif WorkCnt == 'CLEAN':            
                mymachine = AMEMachine(myWorkCnt,myName,myOprs, myUtil,myAvailability,myOnTimePerDay) 
                
                UpdateOprMachines(myOprs,OperationTypes,mymachine)
                myWorkCnt.Machines.append(mymachine)
                
            
        if resourcetype == 'equipment':

            myequipment = Equipment(myWorkCnt,myName, myOprs, myAvailability)    
            myWorkCnt.Equipments.append(myequipment)
    
    # Construct Operation Type objects  
    # OperationTypes: Dictionary, key: OperationType string, value: [Operation type object, alternative machines...]  
    
    for OperationName, MachineList in OperationTypes.items():
        myOprType = AMEOperationType(OperationName)
        MachineList.insert(0,myOprType)
        
        myOprType.AlternativeMachines = MachineList[1:]
        myOprType.AlternativeMachines.sort(key = lambda x:x.Name)
        
        for machine in myOprType.AlternativeMachines:
            machine.OperationTypes.append(myOprType)
            

      
    '''
        Def: Operation (or process) route:
        The set of (sequential) operation types to perform at a work center. 
         
        Note: 
        Products have Route ID to identify their operation type in production paths.
        
        Example:
        At workcetner PRD there is a process route with ID 9 is "Laser Marking,SMD,ICT,Depanelize"
        
        myWorkCnt.ProcessRoutes[9] = [[0,Laser Marking],[1,SMD],[2,ICT],[3,Depenalize]]       
        (myWorkCnt.Name = PRD) 
        
    ''' 
        
    data_Routes = pd.read_csv(RouteFile) 

    #RouteFile : AMEWorkcenterOperationRoutes_date.csv      

    # Read Operation routes and find the corresponding operation types

    for index in range(0, len(data_Routes)):
        
        
        WorkCnt = data_Routes.loc[index]["WorkCenter"]
        myWorkCnt = WorkCenterDict[WorkCnt]
         
        RouteID = data_Routes.loc[index]["RouteID"]
         
         
        if RouteID not in myWorkCnt.ProcessRoutes:  
            myWorkCnt.ProcessRoutes[RouteID] = []
            
        myRouteOrder = data_Routes.loc[index]["RouteSeqOrder"]
        
        myOprType = OperationTypes[data_Routes.loc[index]["OperationType"]][0]
        
      
        myWorkCnt.ProcessRoutes[RouteID].append([myRouteOrder,myOprType])
        
        for routeID, route in myWorkCnt.ProcessRoutes.items():
            if len(route) > 1:
                route.sort(key = lambda x:x[0]) 
   
                
   # For each workcenter, machine subsets are constructed..

    OperationTypeObjects = []
    for WorkCName, myWorkCnt in WorkCenterDict.items():
      
        for routeID, route in myWorkCnt.ProcessRoutes.items():
            for SequenceID, myOprType in route:
              
                UpdateMachineSubsets(myOprType)
                if myOprType not in OperationTypeObjects:
                    OperationTypeObjects.append(myOprType)
        print('   >> WorkCenter', myWorkCnt.Name, ' has ',len(myWorkCnt.MachineGroups),' Machine Groups of sizes: ',[len(machgr) for machgr in myWorkCnt.MachineGroups ])
   
   
  
    
    for myOprType in OperationTypeObjects:
        FindIncludingMachineSubSets(myOprType)
  
    
    return WorkCenterDict 
#############################################################################################

def InitializeAMEProducts(WorkCenterDict,ResourceFile, StockFile, Date):    
    
    #ResourceFile : AMEProductInformation_date.csv   
  
    data_Products = pd.read_csv(ResourceFile)

     
    #StocklevelFile : AMEStockLevels_date.csv
    data_StockLevels = pd.read_csv(StockFile)
    data_StockLevels['Date'] = data_StockLevels['Date'].astype('datetime64[ns]')
    data_StockLevels['StockLevel'] = data_StockLevels['StockLevel'].astype(int)
    data_StockLevels.set_index('PN')
    ProductDict = {}
    RawMaterialDict = {}
    # AlternativeDict = {}
    
    
    
    StockFile = 'DataSets/AMEStockLevels_20210301.csv'
    data_StockLevels = pd.read_csv(StockFile)
    data_StockLevels['Date'] = data_StockLevels['Date'].astype('datetime64[ns]')
    data_StockLevels['StockLevel'] = data_StockLevels['StockLevel'].astype(int)
    data_StockLevels = data_StockLevels[['PN','StockLevel']]
    
    StockLevelDict = data_StockLevels.set_index('PN')['StockLevel'].to_dict()
    counter_wel = 0
    counter_niet = 0
    
    # Reading and defining products starts
    
    for index in range(0, len(data_Products)):     
        PN = data_Products.loc[index]['PN']
        ProdGroup = data_Products.loc[index]['ProductGroup']
        WorkCnt = data_Products.loc[index]['WorkCenter']
        ProcessRouteID = data_Products.loc[index]['OperationRouteID']
        
        batchinfo = data_Products.loc[index]['BatchInfo'].split('-')
        batchinfo = [int(float(num)) for num in batchinfo]
        
        ScrapRate = data_Products.loc[index]['ScrapRate']
        
        if PN in StockLevelDict.keys():
            counter_wel += 1
            StockLevel = StockLevelDict[PN]
        else:
            counter_niet += 1
            StockLevel = 0
            
  
        if WorkCnt not in WorkCenterDict:
            print('ERROR: Product',PN,'has undefined workcenter <',WorkCnt,'> reading passed..')
            continue
        
        myworkcnt = WorkCenterDict[WorkCnt]
             
        if ProcessRouteID not in myworkcnt.ProcessRoutes:
            print('ERROR: Product',PN,'has undefined processroute <',ProcessRouteID,'> reading passed..')
            continue
        
        myroute = myworkcnt.ProcessRoutes[ProcessRouteID]   

        myprod = AMEProduct(PN,myworkcnt,ProdGroup,myroute,batchinfo[0],batchinfo[2],batchinfo[1], ScrapRate,StockLevel) 


         
   
        # raw = ast.literal_eval(data_Products.loc[index]['RawMaterial'])  
        # myprod.getRawMaterials().append(raw)                   
            
        
        # processing times of operations in the workcenter. 
        # Note that we assume that an operation has the same processing time in alternative machines.
        procs = ast.literal_eval(data_Products.loc[index]['ProcessingTimes'])
        setups = ast.literal_eval(data_Products.loc[index]['SetupTimes'])
        
        
        # We do not use scrap rate, to check!
        #scrap_rate = data_Products.loc[index]['ScrapRate'] 
        
         
        if len(myroute)!= len(procs):
             print('ERROR: Product',PN,'has inconsistent execution info, reading passed..')
            

        # create operations of a product and insert into its list..
        for oprid in range(len(myroute)):
            
            myopr = myroute[oprid]
            myoperation = AMEOperation(myprod,myopr[1].Name,myopr[1])
 
            # initialize executioninfo of the operation
            found = False

            for machine in myworkcnt.Machines:
                if myopr[1] in machine.OperationTypes:
                    found = True
                    if type(setups) == list:
                        setuptime = setups[oprid]
                    else: setuptime = setups
                    myoperation.setExecutionInfo(machine, procs[oprid], setuptime)
            if not found:
                print('ERROR: Product',PN,'has undefined machine for operation <',myopr[1],'>')
                       
            myprod.Operations.append(myoperation)                         
        
        if PN in ProductDict:
            print('ERROR: Product',PN,'is already defined before!')
            continue
         
        ProductDict[PN]=myprod
        
    # A second pass for setting predecessors of products
    for index in range(0, len(data_Products)):
        PN = data_Products.loc[index]['PN']
        preds = ast.literal_eval(data_Products.loc[index]['Predecessors'])
      
        for pred in preds:      
            if pred[0] in ProductDict:
                ProductDict[PN].Predecessors.append((ProductDict[pred[0]],int(pred[1])))                    
            else:
                print('ERROR: Pred ',pred[0],' pf prod ',ProductDict[PN].PN,' does -not- exist in the list')
                


   
    
    for product in ProductDict.values():
        RawPN = product.PN+"_rw"
        if len(product.Predecessors) == 0:
            if RawPN in RawMaterialDict:
                product.RawMaterials.append(RawMaterialDict[RawPN])
                RawMaterialDict[RawPN].RequiringProducts.append((product, 1)) #random is multiplier, random.randint(1,10)
            else:
                rawmaterial = AMERawMaterial(RawPN, product.WorkCenter, 1) #random is multiplier # random.randint(1,10)
                
                # here we define only for three days the raw material levels
                day1level = product.StockLevel
                rawmaterial.StockLevels.append(int(day1level))
                day2level = (1+0.1*random.random())*day1level
                rawmaterial.StockLevels.append(int(day2level))
                day3level = (1+0.1*random.random())*day2level
                rawmaterial.StockLevels.append(int(day3level))
                
                RawMaterialDict[RawPN] = rawmaterial
                product.RawMaterials.append(rawmaterial)
                rawmaterial.RequiringProducts.append((product, 1))
        
    # for RawPN in RawMaterialDict:
    #     AlternativeRawPN = RawPN+"_alt"
    #     if AlternativeRawPN in AlternativeDict:
    #         product.Alternative.append(AlternativeDict[AlternativeRawPN])
            
        
        #relatie naar successor + design, afhankelijk                           
                                
                
    print('   >> No. Products: ',len(ProductDict))
    print('   >> No. Raw Materials : ',len(RawMaterialDict))
    # print(RawMaterialDict)
          
    print('   >> Products with stock information', counter_wel)
    return ProductDict, RawMaterialDict
                     
        
        
###################################################################################################  
def InitializeAMEOrders(Products,Orderfile):
 
    #OrderFile : AMEOrderInformation_date.csv
    
    data_Orders = pd.read_csv(Orderfile)
    uniquePN = []
    OrderDictionary = {}
  
    for index in range(0, len(data_Orders)):
         deadline = data_Orders.loc[index]['Deadline']
 
         PN = data_Orders.loc[index]['FinalProductPN']
         myID = data_Orders.loc[index]['OrderID']
         
         if PN not in Products:
             if PN not in uniquePN:
                 uniquePN.append(PN)
             continue
          
         finalprod = Products[PN]
         
         Quantity= data_Orders.loc[index]['Quantity']
         Type = data_Orders.loc[index]['Type']
         SplitType = data_Orders.loc[index]['SplitDelivery'] == '1'
         SplitPeriod = data_Orders.loc[index]['SplitPeriod']
         Revenue = data_Orders.loc[index]['Revenue']
         CustPrio =  data_Orders.loc[index]['CustomerPriority']

        
        
        
        
         myorder = AMEOrder(myID,Quantity,finalprod,SplitType,SplitPeriod,Revenue,deadline,Type,CustPrio) 
         

         

         OrderDictionary[myID] = myorder
         
    print('   >> No.Orders: ',len(OrderDictionary))
    print('   >> Number of PNs not recognized in Product list: ',len(uniquePN),' ..')
    #print('List of missing PN: ', uniquePN)
    
    
    
    
    
    return OrderDictionary 
 


################################################################################################

