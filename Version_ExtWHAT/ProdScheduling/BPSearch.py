# -*- coding: utf-8 -*-
"""

@author: mfirat
"""



import time
from Objects.BPObjects import Solution, NodeProperties, Node
from ProdScheduling.Branching import Branch
from ProdScheduling.NodeSelection import OrderNodes
from ProdScheduling.ColumnGeneration import ColumnGen
from ProdScheduling.MasterLP import InitializePrimal,AddScheduleToMaster
from ProdScheduling.GreedyInitial import GreedyParametricHeuristic
from ProdScheduling.PricingMILP import InitializeArcPricingMILP,InitializeExclusion, ActivateExclusion, DeactivateExclusion
from ProdScheduling.PricingMILP import InitializeLNodePricingCons,InitializeRNodePricingCons,ActivateLNodePricingCons,ActivateRNodePricingCons
from ProdScheduling.PricingMILP import DeactivateLNodePricingCons,DeactivateRNodePricingCons



def DoBPSearch(WorkCenters,AMEOrders,AMEJobs, tau_value, timeGranularity, horizonExtension):
    
   
    print('+++++++++++++++++++++++ BP Search is initialized +++++++++++++++++++++++')
    # initialization 
    Nodes = []
    nodeid = 0
    Queue = []
    
    incumbentSol = None
    bestlbval = -1
    gapthreshold = 0.70
    TimeHorizon = 300 #days
    timelimit = 600 #secs.
    
    
    start_time = time.time() 
    
    
    levelexplorations  = [0 for i in range(10000)] 
    levellbvalues = [-1 for i in range(10000)] 
    
    initialheuristic = True   

    # timeUnits = (tau_value*1440)//timeGranularity
    timeUnits = [i for i in range(0,(tau_value+horizonExtension)*1440, timeGranularity)]
    
    
    Rootnode = Node(nodeid,None, True)
    
    #################### Initialize primal and arcs for B&P ############################
    print('Master model is initialized..')
    masterlp = InitializePrimal(AMEOrders, WorkCenters, timeUnits, timeGranularity)
    
  
    
    print('Construct Graph structure')
    for OrderID, myOrder in AMEOrders.items():
        InitializeArcPricingMILP(myOrder, tau_value, horizonExtension, timeGranularity)

    ########################## Greedy solution approach ##############################
    if initialheuristic: 
        print('Start Greedy Parametric Horizon Model, initial solution')
        BestFoundSolutionValue = GreedyParametricHeuristic(WorkCenters, AMEJobs,tau_value, horizonExtension, timeGranularity)
        selectedschedules = []
        for orderID, order in AMEOrders.items():
            for idx, schedule in enumerate(order.Schedules):
                AddScheduleToMaster(masterlp, order, schedule, timeGranularity)
                if idx == 0:
                    selectedschedules.append(schedule)
    
        incumbentSol = Solution(BestFoundSolutionValue,Rootnode, selectedschedules)
    
    
    
    # print('Construct MILP Arcs')
    # InitializeArcPricingMILP(Orders, AMEJobs, tau_value, horizonExtension, timeGranularity)
    
    #######################################################################################################
    
    
    # attention: Time units may not coincide with new CG, granularity etc.
    # The heuristic needs to be adapted, once the granularity setting is done.
    
    
    myNodeProperties = NodeProperties(Rootnode)
    Rootnode.setNodeProperties(myNodeProperties)
    
   
    
    Nodes.append(Rootnode)
            
    
    
    masterlp.update()


    Queue.append(Rootnode)

    maxdepth = 5000 # 0 means only exploration of root node
    
    print('+++++++++++++++++++++++ BP Search starts +++++++++++++++++++++++')
    previousnode = None
    idx = 0
    while len(Queue) > 0:
        #print('Length of Queue: ', len(Queue))
        currentnode = Queue[0]
        if previousnode != None:
            ActivateNode(previousnode, currentnode)
        
        #print('Current node',currentnode.getID(),' to explore..')
        nodeintsol, masterlp, selectedschedules, CGPropertiesList = ExploreNode(currentnode,masterlp,WorkCenters,AMEOrders,timelimit,TimeHorizon, timeGranularity) #Tue part
        if nodeintsol != None:
            if incumbentSol != None:
                if incumbentSol.getObjValue() > nodeintsol.getObjValue():
                    incumbentSol = nodeintsol
                    UpdateQueue(Queue,incumbentSol.getObjValue())
            else:
                 incumbentSol = nodeintsol
                 UpdateQueue(Queue,incumbentSol.getObjValue())

        if incumbentSol == None:
             childs, nodeid = Branch(masterlp,WorkCenters,AMEOrders,currentnode,nodeid, selectedschedules)
             if len(childs) > 0:
                   #print('Current node is creating child Node')
                   leftchild, rightchild = childs
                   myLeftNodeProperties = NodeProperties(leftchild)
                   myRightNodeProperties = NodeProperties(rightchild)
                   
                   leftchild.setNodeProperties(myLeftNodeProperties)
                   rightchild.setNodeProperties(myRightNodeProperties)

                   Nodes.append(leftchild)
                   Nodes.append(rightchild)
                   
                   Queue.insert(0, rightchild)
                   Queue.insert(0, leftchild)
        else:
            if currentnode.getLBValue() < incumbentSol.getObjValue() - 10**-4: # else node pruning
            
                
               if currentnode.getTreeDepth() < maxdepth: # else max depth reached
                   childs, nodeid = Branch(masterlp,WorkCenters,AMEOrders,currentnode,nodeid, selectedschedules)
                   if len(childs) > 0:
                       #print('Current node is creating child Node')
                       leftchild, rightchild = childs
                       myLeftNodeProperties = NodeProperties(leftchild)
                       myRightNodeProperties = NodeProperties(rightchild)
                       
                       leftchild.setNodeProperties(myLeftNodeProperties)
                       rightchild.setNodeProperties(myRightNodeProperties)
    
                       Nodes.append(leftchild)
                       Nodes.append(rightchild)
                       
                       Queue.insert(0, rightchild)
                       Queue.insert(0, leftchild)
            
        Queue.remove(currentnode)
        previousnode = currentnode
        # OrderNodes(Queue) #OzU part
        
        levelexplorations[currentnode.treedepth]+=1
          
            
        
       
        
        if levellbvalues[currentnode.treedepth] == -1:
            levellbvalues[currentnode.treedepth] = masterlp.ObjVal
            #print('--->Level lb value is set to Master ObjVal : ', masterlp.objVal)
        else:
            levellbvalues[currentnode.treedepth] = min(levellbvalues[currentnode.treedepth],masterlp.ObjVal)
        
        if levelexplorations[currentnode.treedepth] == 2**(currentnode.treedepth):  
            bestlbval = levellbvalues[currentnode.treedepth]
            print('LB vales update at level ',currentnode.treedepth,':', bestlbval)
        # optimality gap based termination
        
        
        currentnode.NodeProperties.UpdateExplored(idx, currentnode, CGPropertiesList)
        if incumbentSol != None:
            if (incumbentSol.getObjValue() - max(bestlbval, timeGranularity))/ max(bestlbval, timeGranularity) < gapthreshold:
                if bestlbval !=0:
                    print('Termination: Optimality gap is small enough',round((incumbentSol.getObjValue() - bestlbval)/ bestlbval ,2))
                else:
                    print('bestlbvar equal to zero so break')
                break
        # if incumbentSol.getObjValue() < 500:
        #     print('Termination: Optimality gap is small',round(incumbentSol.getObjValue()  ,2))
        #     break
        idx += 1
     
    
    
    return AMEOrders, AMEJobs, incumbentSol, Nodes, (time.time()-start_time)


###########################################################################################################################################
def ExploreNode(node,masterlp,WorkCenters,Orders,timelimit,TimeHorizon,timeGranularity):
                  
            
        integersol, masterlp, selectedschedules, CGPropertiesList,cgiters,integerCounter = ColumnGen(node,masterlp,WorkCenters,Orders,timelimit,TimeHorizon, timeGranularity)


        print('---->Node ',node.getID(),' exploration: ',cgiters,' CG iters, integers: ',integerCounter,', obj.val= ',round(masterlp.objVal,2),'  <----')      
          
        return integersol, masterlp, selectedschedules, CGPropertiesList

##############################################################################################################################################
 
def UpdateQueue(Queue,bestubval): 
    newQueue = [item for item in Queue if item.getLBValue() < bestubval]
    return newQueue
######################################################################################################
def BacktrackBranching(Node):
    
    if Node.IsScheduleBranched():
        for schedule in Node.branchedcolumns:
            schedule.resetBranched()
            schedule.Order.resetBranched()
            DeactivateExclusion(schedule,schedule.Order)
    else:
        if Node.IsAssignBranched(): 
            if Node.Left:
                for jobmachassign in Node.branchedjobmachs:
                    DeactivateLNodePricingCons(jobmachassign)
                    jobmachassign.order.resetAssignBranched()
                    
                    for job,machine in jobmachassign.getAssignDict().items():
                        job.MachineBranched = False
            else:
                for jobmachassign in Node.branchedjobmachs:
                    DeactivateRNodePricingCons(jobmachassign)
                   

        
    for schedule in Node.cancelledcolumns:
        schedule.MPLambdaVar.ub = 1
        
    # Making the generated columns off because these schedules will no longer exist
    for schedule in Node.generatedcolumns:
        schedule.MPLambdaVar.ub = 0
        
    return
############################################################################################################## 
def ActivateBranching(node): # this is activation of branching for previously explored nodes                  
   
 
    for nodeSchedule in node.generatedcolumns:
        nodeSchedule.MPLambdaVar.ub = 1
        
       
    for schedule in node.cancelledcolumns: 
        schedule.MPLambdaVar.ub = 0
        
        
    
    # Forbid cancelled schedules in the PricingMILP of the order 
         
    if not node.explored: 
        for schedule in node.cancelledcolumns:
            InitializeExclusion(schedule, schedule.Order) 
    else: 
        for schedule in node.cancelledcolumns:
            ActivateExclusion(schedule, schedule.Order)


    # Set branched schedules
    for schedule in node.branchedcolumns:
        schedule.setBranched()
        schedule.Order.setBranched()
            
  
        
    return
    
##############################################################################################################
def ActivateNode(LastExplored,ToExplore):
    #print('LastExplored Node', LastExplored.id, '-> ToExplore Node' , ToExplore.id)

    # print('from Node d'+str(LastExplored.treedepth)+ 'n'+str(LastExplored.id)+ 'to node d'+str(ToExplore.treedepth)+ 'n'+str(ToExplore.id))
    PassedNodes = []
    LastParent = LastExplored
    ToParent = ToExplore.parent
    
    
    
    # Equate depth of lastExplored
    while LastParent.treedepth > ToParent.treedepth:
        BacktrackBranching(LastParent)     
        #print('Depth', LastParent.treedepth, 'backtracked branching at node ', LastParent.id, 'to parent node: ', ToParent.id)
        LastParent = LastParent.parent
        
    # Equate depth of ToExplore
    while LastParent.treedepth < ToParent.treedepth:
        PassedNodes.insert(0, ToParent)
        #print('Depth', ToParent.treedepth, 'inserting node ', ToParent.id, 'into passed node ', LastParent.id)
        ToParent = ToParent.parent
        
    # Continue backtracking together until common node is reached
    
    while LastParent != ToParent:
        BacktrackBranching(LastParent)  
        #print('Depth', LastParent.treedepth, 'backtracked branching at node ', LastParent.id, 'to parent node: ', ToParent.id)
        LastParent = LastParent.parent
            
        PassedNodes.insert(0,ToParent)
        #print('Depth', ToParent.treedepth, 'inserting node ', ToParent.id, 'into passed node ', LastParent.id)
        ToParent = ToParent.parent
    
    # Common parent is reached, now start activating branching
    for node in PassedNodes:
        ActivateBranching(node)
    
    # Go to node to explore
    ActivateBranching(ToExplore)    
        
      
    return
    
#########################################################################################################################################
def printQueue(Queue):
    string = ''
    for node in Queue:
        string += '-Node_d'+str(node.treedepth) + '_N' + str(node.id) 