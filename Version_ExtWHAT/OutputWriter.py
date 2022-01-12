# -*- coding: utf-8 -*-
"""
Created on Mon May 24 17:52:37 2021

@author: VAIO
"""
import pandas as pd
from datetime import datetime

def WriteHowSolution_1(Workcenters):

    write_file = 'DataSets/How_Solution_1.csv'
    
    df_job = pd.read_csv('DataSets/JOBName.csv', usecols=['JobOld','JobID'])
    # df_task = pd.read_csv('DataSets/JOBName.csv', usecols=['TaskOld','TaskID'])
    # df_order = pd.read_csv('DataSets/JOBName.csv', usecols=['OrderOld','OrderID'])
    
    df_job = df_job.set_index('JobOld')['JobID'].to_dict()
    # df_task.set_index('TaskOld')['TaskID'].to_dict()
    # df_order.set_index('OrderOld')['OrderID'].to_dict()

    

    with open(write_file, "w") as output:

            
        rowlist = ['JobID',
                   'Machine',
                   'StartTime',

            
                   
            ]

        row = ",".join(rowlist)
 
        row +='\n'  #'SLot'+','+'PN'+','+'Quantity'+','+'Start'+','+'Processingtime'+','+'End'+','+'PredecessorTaskID'+','+'MaxPredecessorTaskTime'+','+'MaxPredecessorTime'+','+"\n"    
        output.write(row)
        
        
        
        jobdict = {}
            
        for name,workcnt in Workcenters.items(): 
            for machine in workcnt.Machines:

                for daysch in machine.getDaySchedules():
                    
                    for job, jobcompletion in daysch.getSequence():
                        try: 
                            jobdict[str(name)+'_'+str(job.getID())] == -1
                        except:
                            jobdict.update({str(name)+'_'+str(job.getID()):1})
                            
                            rowlist = [df_job[str(name)+'_'+str(job.getID())],
                                       machine.Name,
                                       job.getGreedyStart()
                                ]
            
                            row = ",".join([str(element) for element in rowlist])
                 
                
                            row += "\n"
                            output.write(row)

    return

def WriteHowSolution_2(Workcenters):

    write_file = 'DataSets/How_Solution_extra_1.csv'
    
    df = pd.read_csv('DataSets/JOBName.csv', usecols=['JobOld','JobID','TaskID','OrderID','Deadline'])
    # df_task = pd.read_csv('DataSets/JOBName.csv', usecols=['TaskOld','TaskID'])
    # df_order = pd.read_csv('DataSets/JOBName.csv', usecols=['OrderOld','OrderID'])
    
    df_jobID = df.set_index('JobOld')['JobID'].copy().to_dict()
    df_taskID = df.set_index('JobOld')['TaskID'].copy().to_dict()
    df_OrderID = df.set_index('JobOld')['OrderID'].copy().to_dict()
    df_Deadline = df.set_index('JobOld')['Deadline'].copy().to_dict()


    

    with open(write_file, "w") as output:

            
        rowlist = ['JobID',
                    'TaskID',
                    'OrderID',
                    'Deadline',
                    'Machine',
                    'StartTime',
                    'CompletionTime'

                   
                   
            ]

        row = ",".join(rowlist)
 
        row +='\n'  #'SLot'+','+'PN'+','+'Quantity'+','+'Start'+','+'Processingtime'+','+'End'+','+'PredecessorTaskID'+','+'MaxPredecessorTaskTime'+','+'MaxPredecessorTime'+','+"\n"    
        output.write(row)
        
        
        
        jobdict = {}
            
        for name,workcnt in Workcenters.items(): 
            for machine in workcnt.getMachines():

                for daysch in machine.getDaySchedules():
                    
                    for job, jobcompletion in daysch.getSequence():
                        try: 
                            jobdict[str(name)+'_'+str(job.getID())] == -1
                        except:
                            jobdict.update({str(name)+'_'+str(job.getID()):1})
                            
                            rowlist = [df_jobID[str(name)+'_'+str(job.getID())],
                                        df_taskID[str(name)+'_'+str(job.getID())],
                                        df_OrderID[str(name)+'_'+str(job.getID())],
                                        df_Deadline[str(name)+'_'+str(job.getID())],
                                        str(name)+'_'+str(machine.getName())+'_'+str(machine.getID()),
                                        job.getGreedyStart(),
                                        job.getGreedyCompletion()
                                ]
            
                            row = ",".join([str(element) for element in rowlist])
                 
                
                            row += "\n"
                            output.write(row)

    return

#########################################################################################################

#########################################################################################################

def WriteJobs(Workcenters):

    write_file = 'DataSets/Instance_Jobs.csv'

    with open(write_file, "w") as output:

            
        rowlist = ['JobID',
                   'TaskID',
                   'OrderID',
                   'JobDeadline',
                   'OrderDeadline',
                   'PN',
                   'Quantity', 
                   'Workcenter',
                   
                    # 'PredecessorTasks',
                    # 'SuccessorTasks',
                   'PredecessorJobs',
                   'SuccessorJobs',
                   
                   'MachineOptions',
                   'Processingtime',
                   'RemainingProcTime',
                   'SuccsToSchedule',
                   'PredsToComp']
                   
                           


        row = ",".join(rowlist)
 
        row +='\n'
        output.write(row)

        for name,workcnt in Workcenters.items():   
            for job in workcnt.Jobs:
                # print('Deadlines: ',job.JobID, job.Deadline, job.Task.Deadline, job.Order.Deadline, job.Order.SDeadline)
                machinelist = []
                # processtime = job.getAlternatives().items()[0][1]
                # for machine, processingtime in job.Alternatives.items():
                #     machinelist.append(str(machine.Name))
                #     # processtimelist.append(processingtime)
                processtime = round(job.ProcessingTime,1)
                machinelist = "-".join(str(x.Name) for x in job.AlternativeMachines)
                # processtimelist = "-".join(str(round(x,1)) for x in processtimelist)
                
                predecessortasklist = []
                for predtask in job.Task.Predecessors:
                    predecessortasklist.append(str(predtask.Product.WorkCenter.Name)+'_'+str(predtask.ID))
                predecessortasklist = "-".join(str(x) for x in predecessortasklist)
                
                successortasklist = []
                for succtask in job.Task.Successors:
                    successortasklist.append(str(succtask.Product.WorkCenter.Name)+'_'+str(succtask.ID))
                successortasklist = "-".join(str(x) for x in successortasklist)
                    
                predecessorjoblist = []
                for predjob in job.Predecessors:
                    predecessorjoblist.append(predjob.JobID)
                predecessorjoblist = "-".join(str(x) for x in predecessorjoblist)
                
                successorjoblist = []
                for predjob in job.Successors:
                    successorjoblist.append(predjob.JobID)
                successorjoblist = "-".join(str(x) for x in successorjoblist)

                    
                rowlist = [job.JobID,
                            job.Task.ID,
                            job.Task.OrderID,
                            job.Deadline,
                            job.Order.SDeadline,
                           
                            job.Task.Product.PN,
                            job.Quantity,
                            workcnt.Name,
                           
                            # predecessortasklist,
                            # successortasklist,
                            
                            predecessorjoblist,
                            successorjoblist,
                           
                            machinelist,
                            processtime,
                            job.RemainingProcTime,
                            job.succsToSchedule,
                            len(job.Predecessors)]

        
                        
    
                row = ",".join([str(element) for element in rowlist])
     
    
                row += "\n"
                output.write(row)

    return

def WriteMachines(Workcenters,TimeGranularity): 

    write_file = 'DataSets/Instance_Machines.csv'

    with open(write_file, "w") as output:

            
        rowlist = ['machine',
                   'OffTimePerDay']
                   
                           


        row = ",".join(rowlist)
 
        row +='\n'  #'SLot'+','+'PN'+','+'Quantity'+','+'Start'+','+'Processingtime'+','+'End'+','+'PredecessorTaskID'+','+'MaxPredecessorTaskTime'+','+'MaxPredecessorTime'+','+"\n"    
        output.write(row)




        for name,workcnt in Workcenters.items():   
            for machine in workcnt.Machines:
                rowlist = [str(machine.Name),
                           "-".join(str(x) for x in [machine.OnTimeGivenDay(day, TimeGranularity) for day in range(50)])
                           ]
                # print(str(name)+'_'+str(machine.getName())+'_'+str(machine.getID()))
                        

                row = ",".join([str(element) for element in rowlist])
     
    
                row += "\n"
                output.write(row)

    return





def storeSchedules(incumbentSol, tau_value, timeGranularity):
    
    
    SelectedSchedules = []
    for schedule, value in incumbentSol.schedules.items():
        SelectedSchedules.append(schedule)
    
    
    data = []
    for schedule in SelectedSchedules:
        for machine, Tuples in schedule.MPSchedule.items():
            for job, ranges in Tuples:
                startTask = 0
                if len(job.Predecessors) == 0:
                    startTask = 1
                for PredJob in job.Predecessors:
                    if PredJob.Task != job.Task:
                        startTask = 1
                        break
                endTask = 0
                if len(job.Successors) == 0:
                    endTask = 1
                for SucJob in job.Successors:
                    if SucJob.Task != job.Task:
                        endTask = 1
                data.append([job.JobID, job.OrderID,  job.Order.SDeadline, machine.Name, machine.WorkCenter.Name, '- '.join(map(str,[machine.Name for machine in job.AlternativeMachines])), ranges.start, ranges.stop, job.ProcessingTime, job.StartLB, job.StartUB,job.Deadline, schedule.tardiness, startTask, endTask, job.IsStart, job.IsFinal])
    df = pd.DataFrame(data, columns=['JobID', 'OrderID', 'OrderDeadline', 'Selected Machine', 'WorkCenter', 'Alternative Machines', 'StartTime', 'CompTime', 'ProcessingTime', 'LatestStartTime', 'LatestCompTime','JobDeadline', 'Tardiness', 'StartTask', 'EndTask','StartJob', 'FinalJob'])
    
    
    df.to_csv('DataSets/OutputBP/Schedule instance T'+str(tau_value)+'_G'+str(timeGranularity)+'.csv', index=False)
    
    return

def storeNodeProperties(Nodes, tau_value, timeGranularity):
    NodeData = []
    for nodeIter in Nodes:
        node = nodeIter.NodeProperties
        NodeData.append((node.idx, node.id, node.depth, node.Explored, node.Pruned, node.Fathomed, node.Objective, node.TotalSchedules, node.IntegerSchedules,node.SchedulesPerOrder, node.SchedulesOptimalPerOrder, node.Integer, node.CGIterations, node.MasterCompTime, node.PricingCompTime))
    dframe = pd.DataFrame(NodeData, columns=['idx', 'id', 'depth', 'Explored', 'Pruned', 'Fathomed', 'Objective', 'TotalSchedules', 'IntegerSchedules', 'SchedulesPerOrder', 'SchedulesOptimalPerOrder', 'Integer', 'CGIterations', 'MasterCompTime', 'PricingCompTime'])
    dframe.to_csv('DataSets/OutputBP/M_NodeProperties_'+str(tau_value)+'_'+str(timeGranularity)+'_'+datetime.now().strftime("%Y-%m-%d %H_%M")+'.csv', encoding='utf-8', index=False)
    
    CGData = []
    for nodeIndex, node in enumerate(Nodes):
        for CGIter in node.NodeProperties.CGProperties:
            CGData.append((node.NodeProperties.idx, node.NodeProperties.id, node.NodeProperties.depth, CGIter.Iteration, CGIter.MasterCompTime, CGIter.PricingCompTime,  CGIter.MasterSolVal, CGIter.Integer, CGIter.ArtVars, CGIter.artvarSUM, CGIter.SelectedColumns,CGIter.TotalColumns, CGIter.IntegerColumns, CGIter.SchedulesPerOrder, CGIter.SchedulesSelectedPerOrder, CGIter.ColumnsNegRedCost, CGIter.ColumnsChecked))
        dframe = pd.DataFrame(CGData, columns=['idx', 'id', 'depth', 'Iteration', 'MasterCompTime', 'PricingCompTime', 'MasterSolVal', 'Integer', 'ArtVars', 'artvarSUM', 'SelectedColumns', 'TotalColumns', 'IntegerColumns', 'SchedulesPerOrder', 'SchedulesSelectedPerOrder', 'ColumnsNegRedCost', 'ColumnsChecked'])
    dframe.to_csv('DataSets/OutputBP/M_NodeCGProperties_'+str(tau_value)+'_'+str(timeGranularity)+'.csv', encoding='utf-8', index=False)
    return
    
    
    
    
    
########################################################################################           
def WriteMachineCapacityUse(WorkCenters,tau_value,timeGranularity,optimal):
    
    
    
     write_file = 'DataSets/What_MachineCapUse.csv'
     
     print('   _____________________________________________________')
     print('   >> WHAT Model results: Resource capacity use values: ' )
  
     with open(write_file, "w") as output:
        
         row = 'WorkCnt'+','+'MachGroup'+','+'Day'+','+'Use'+','+'Capacity'+"\n"    
         output.write(row)
         print(output.write(row))
        
                
        
         for name,workcnt in WorkCenters.items():
             subsetid = 0
             for myMachSubset in workcnt.MachineSubSetList:
                 totalcap = 0
                 
                    
           
                 subsetstr = ''
                 
                 
                 for mach in myMachSubset.Machines:  
                     subsetstr+='-'+mach.Name
                 print('    -> Workcenter ',workcnt.Name,', Machine group',subsetstr,':' )
                    
                 for day in range(tau_value):      
                     totalcap += sum([machine.OnTimeGivenDay(day, timeGranularity) for machine in myMachSubset.Machines])    
                     if optimal:
                         totaluse = sum( usepair[0]*usepair[1].x  for usepair in myMachSubset.CapacityUseVars[day])
                     else: 
                         totaluse = sum( usepair[0]*usepair[1].xn  for usepair in myMachSubset.CapacityUseVars[day])
                     row = str(workcnt.Name)+','+str(subsetstr)+','+str(day+1)+','+str(round(totaluse,2))+','+str(round(totalcap,2))     
                     row += "\n"
                     output.write(row)
                     print('     > Day',(day+1),': ',round(totaluse,2),'<= ',round(totalcap,2))
                    
               
                 subsetid+=1 
                     
                     


     return      

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    