# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 09:12:41 2021

@author: mfirat
"""

import pandas as pd

from Objects.ProductionObjects import AMEMachineSubSet

import ast
from datetime import datetime
import collections

compare = lambda x, y: collections.Counter(x) == collections.Counter(y)


#####################################################################################################
def UpdateMachineSubsets(myOprType):
           
    '''    
       Given an operation type, OpType, with a set of alternative machines, M(opType).
       Find all machines subsets, union of M(opType) \cup M' such that this union is not 
       in the Machines Subsets of the corresponding work center. 
        
    '''
    
    myWorkCnt = myOprType.AlternativeMachines[0].WorkCenter
    # print(myWorkCnt.Name)
    OpMachStr= ''
    for mach in myOprType.AlternativeMachines:
        OpMachStr+='-'+mach.Name
    OverlappingMachineGroup = None
    intersecting = []
    inlist = False
    Included = False
    Overlapping = False
    
    for MachineGroup in myWorkCnt.MachineGroups:
        Overlapping = False
        Included = False
        for subset in MachineGroup:
            if compare(myOprType.AlternativeMachines,subset):
                Included = True
                break       
            if set(subset).intersection(myOprType.AlternativeMachines):
                Overlapping = True
                OverlappingMachineGroup = MachineGroup
                subsetstr = ''
                for mach in subset:
                    subsetstr+='-'+mach.Name
                    
                # print('Intersection: ',subsetstr,' and ',OpMachStr)
                # PrintMachineGroup(MachineGroup)
               
        if Included or Overlapping:
            break
    if Included:
        return
    if not Overlapping:
        myWorkCnt.MachineGroups.append([myOprType.AlternativeMachines])
        mySubset = AMEMachineSubSet(myOprType.AlternativeMachines)
        myWorkCnt.MachineSubSetList.append(mySubset)
          
        return
    
    for subset in OverlappingMachineGroup:
        if len(set(myOprType.AlternativeMachines).intersection(set(subset)))> 0:
            intersecting.append(subset)
        
    # print('Intersecting subsets',len(intersecting))
    
   
    for subset in intersecting: 
        if set(myOprType.AlternativeMachines).issubset(set(subset)) or set(subset).issubset(set(myOprType.AlternativeMachines)):
            continue
        newsubset = list(set(myOprType.AlternativeMachines).union(set(subset)))
        
        newsubset.sort(key = lambda x:x.Name)
                
        inlist = False
        for ssubset in OverlappingMachineGroup:
            
            if compare(newsubset,ssubset):
                inlist = True
                # print('Equal')
                break
                # print('Not Equal')
        if inlist:
            continue

            
        OverlappingMachineGroup.append(newsubset)
        
        mySubset = AMEMachineSubSet(newsubset)
        myWorkCnt.MachineSubSetList.append(mySubset)
        
    OverlappingMachineGroup.append(myOprType.AlternativeMachines)
    
    mySubset = AMEMachineSubSet(myOprType.AlternativeMachines)
    myWorkCnt.MachineSubSetList.append(mySubset)
    
      
    return
############################################################################################

def PrintMachineGroup(MachineGroup):
    
    machinestrgroup = []
    
    for subset in MachineGroup:
          subsetstr = ''
          for mach in subset:
              subsetstr+='-'+mach.Name
          machinestrgroup.append(subsetstr)
         
    print('WorkCenter: ', mach.WorkCenter.Name, 'MachineGr: ',machinestrgroup)
   
    
    return


def UpdateOprMachines(myOprs,oprmachines,mymachine):
    
    for opname in myOprs:
        if opname in oprmachines:
            oprmachines[opname].append(mymachine)
        else:
            oprmachines[opname] = [mymachine]
            
    return


def FindIncludingMachineSubSets(myOprType):
    
    myWorkCnt = myOprType.AlternativeMachines[0].WorkCenter
    for subset in myWorkCnt.MachineSubSetList:
        if set(myOprType.AlternativeMachines).issubset(set(subset.Machines)):
            myOprType.IncludingMachineSubsets.append(subset)
                
    return

