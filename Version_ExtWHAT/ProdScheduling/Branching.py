# -*- coding: utf-8 -*-
"""


@author: mfirat
"""

from Objects.BPObjects import Node
from Objects.PlanningObjects import JobMachineAssignment
from ProdScheduling.PricingMILP import InitializeArcPricingMILP,InitializeExclusion, ActivateExclusion, DeactivateExclusion
from ProdScheduling.MasterLP import SolveMaster


def Branch(masterlp,WorkCenters, Orders,parent,lastid, selectedschedules):
   
    ChildNodes = CheckBranchingType(masterlp,WorkCenters, Orders,parent,lastid, selectedschedules)
    # branching rule is selected here.      


    return ChildNodes, lastid + len(ChildNodes)


  
def CheckBranchingType(masterlp,WorkCenters, Orders,parent,lastid, selectedschedules):
    
    selectedschedules = dict(sorted(selectedschedules.items(), key=lambda item: -item[1]))
    
  
    leftchild = Node(lastid+1,parent, True)
    rightchild = Node(lastid+2,parent, False)
    
    ScheduleBranchThreshold = 0.0
    
  
    
    for schedule in selectedschedules:
        

        if schedule.Branched:
            continue
  
      
        cancelledcolumns = SimulateScheduleBranching(schedule.Order,schedule,leftchild)

        masterlp,mastersolval,selectedschedules, IntegerSolution, MasterProperties,integerCounter = SolveMaster(masterlp,leftchild.getID(),0,WorkCenters, Orders)

        selectstr = str(schedule.MPLambdaVar.x)
        
        for myschedule in cancelledcolumns:
            selectstr+=str(myschedule.MPLambdaVar.x)
        
  
        print('LBranch: O',schedule.Order.OrderID,',Sch',schedule.id,', cans',len(cancelledcolumns),' z_RMP=',mastersolval,', IntSchedules',integerCounter,', Pos.ArtVars',MasterProperties[1],',str',selectstr)
        
        # backtrack the changes:
        for myschedule in cancelledcolumns: 
            myschedule.MPLambdaVar.ub = 1
            
            
        cancelledcolumns = SimulateScheduleBranching(schedule.Order,schedule,rightchild)

        masterlp,mastersolval,selectedschedules, IntegerSolution, MasterProperties,integerCounter = SolveMaster(masterlp,rightchild.getID(),0,WorkCenters, Orders)
    
    
        print('RBranch: O',schedule.Order.OrderID,',Sch',schedule.id,', cans',len(cancelledcolumns),' z_RMP=',mastersolval,', IntSchedules',integerCounter,', Pos.ArtVars',MasterProperties[1])
     
    
          
        # backtrack the changes:
        for myschedule in cancelledcolumns: 
            myschedule.MPLambdaVar.ub = 1
             
             
    

    
    for schedule in selectedschedules:
        

        if schedule.Branched:
            continue
        
        ProceedScheduleBranching(leftchild,rightchild,schedule.Order,schedule)
          
        break
    
   
    

    return [leftchild,rightchild]

#################################################################################

def ProceedScheduleBranching(leftchild,rightchild,myOrder,schedule):
    
    leftchild.setScheduleBranched()
    rightchild.setScheduleBranched()
    
    for mySchedule in myOrder.Schedules:    
        if mySchedule.MPLambdaVar.ub == 0:
            continue     
        if schedule != mySchedule:
            leftchild.cancelledcolumns.append(mySchedule)
            
   
    rightchild.cancelledcolumns.append(schedule)
    
   
    # here we specify the precise information of branching        
    leftchild.branchedcolumns.append(schedule)      
    
  
    return 

##################################################################################
def SimulateScheduleBranching(myOrder,schedule,node):
    
    cancelledcolumns = []
    
    if node.Left: 
        for mySchedule in myOrder.Schedules:    
            if mySchedule.MPLambdaVar.ub == 0:
                continue     
            if schedule != mySchedule:
               mySchedule.MPLambdaVar.ub = 0
               cancelledcolumns.append(mySchedule)              
              
    else:
        schedule.MPLambdaVar.ub == 0
        cancelledcolumns.append(schedule)
      
  
    return cancelledcolumns

#################################################################################
def ProceedJobMachineBranching(leftchild,rightchild,selectedschedules,myschedule):
    
       
    #print('>>> Job-Machine Branching...')
   
       
    
    jobmatchdict = dict()
    
    assigndict = dict()
    
    assigns = []
    
    for schedule in selectedschedules:
            
        if schedule.Branched:
            continue
        
        if schedule.Order not in assigndict:
            assigndict[schedule.Order] = dict()
            
            for job in schedule.Order.Jobs:
                if len(job.AlternativeMachines) == 1 or job.MachineBranched:
                    continue     
                assigndict[schedule.Order][job] = dict()
                
                for machine in job.AlternativeMachines:
                    assigndict[schedule.Order][job][machine] = 0
        
        for machine, Tuples in schedule.MPSchedule.items():     
            for myJob, ranges in Tuples:
                if len(myJob.AlternativeMachines) == 1 or myJob.MachineBranched:
                    continue
                assigndict[schedule.Order][myJob][machine] += schedule.MPLambdaVar.x
        
 
                 
    for order,jobassings in assigndict.items():
      
        for job,machines in jobassings.items():
            
            for machine,val in machines.items():
            
                
                assigns.append([job,machine,val])
                 
    assigns.sort(key=lambda x: -x[-1])    
    
    orderdict = dict()
    for assign in assigns:
        if assign[2] < 0.75:
            break
        if assign[0].Order not in orderdict:
            orderdict[assign[0].Order] = 0
        orderdict[assign[0].Order] +=1
        #print('Job',assign[0].JobID,' of order ',assign[0].Order.OrderID,' assigned to machine ',assign[1].Name, 'assignvalue ',assign[2])
    
    SelectedOrder = None
    HighestValue = 0
    for order,count in orderdict.items():
        if count > HighestValue:
            HighestValue = count
            SelectedOrder = order

    if SelectedOrder == None:
        return None

    jobmachassign = JobMachineAssignment(SelectedOrder) 
    
    for assign in assigns:
        if assign[2] < 0.75:
            break 
        if assign[0].Order == SelectedOrder:
            jobmachassign.getAssignDict()[assign[0]] = assign[1]
            #print('>>>> Job',assign[0].JobID,' of order ',assign[0].Order.OrderID,' assigned to machine ',assign[1].Name, 'assignvalue ',assign[2])
    
          
    leftchild.branchedjobmachs.append(jobmachassign)  
    rightchild.branchedjobmachs.append(jobmachassign)       
      
    
    
    #print('>> Branching.. Order ',SelectedOrder.OrderID)
            
    
    #print('Order',SelectedOrder.OrderID,'has ',len(SelectedOrder.Schedules), 'schedules')
       
    for mySchedule in SelectedOrder.Schedules:
            
        allassigned = True
        #print('Schedule',mySchedule.id,' solution value', mySchedule.MPLambdaVar.x)
        
        for machine,execs in mySchedule.MPSchedule.items():
             for myJob, ranges in execs:   
                 if len(myJob.AlternativeMachines) == 1 or myJob not in jobmachassign.getAssignDict():
                    continue
                 if jobmachassign.getAssignDict()[myJob] != machine: 
                     #print('  xxx  > Job',myJob.JobID,' executed in machine',machine.Name, 'but assigned to',jobmachassign.getAssignDict()[myJob].Name )
                     allassigned = False
                     break
                 
             if not allassigned:
                 break
             
      
        if not allassigned:
            # job is not executed in the assigned machine in this schedule, so forbid it.
            leftchild.cancelledcolumns.append(mySchedule)
        else:
            rightchild.cancelledcolumns.append(mySchedule)
            
                
    # print('>> Leftchild ',leftchild.getID(),' node has ',len(leftchild.cancelledcolumns),' cancelled schedules..')
    # print('>> Rightchild  ',rightchild.getID(),' node has ',len(rightchild.cancelledcolumns),' cancelled schedules..')
                  
                     
               
    return jobmachassign


#################################################################################
def ProceedJobTimeBranching(BPnode,myOrder,jobmachtuples):
    
    print('>>> Job-Time Branching...')
    
    # This branching considers execution of jobs and finding time slots that are surely selected by master model.
   
    
    
   
  
    return