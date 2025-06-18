"use client";

import React, { useMemo } from 'react';
import { Brain, Wrench, Eye, CheckCircle, AlertTriangle, ArrowDown, Clock, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AgentStep, AgentExecution } from '@/types/agent';
import { cn } from '@/lib/utils';

interface ExecutionFlowDiagramProps {
  execution: AgentExecution;
  selectedStepId?: string;
  onStepSelect?: (stepId: string) => void;
  className?: string;
}

export function ExecutionFlowDiagram({ 
  execution, 
  selectedStepId,
  onStepSelect,
  className 
}: ExecutionFlowDiagramProps) {
  const flowData = useMemo(() => {
    const steps = execution.steps;
    const totalDuration = execution.endTime 
      ? execution.endTime.getTime() - execution.startTime.getTime()
      : Date.now() - execution.startTime.getTime();

    return {
      steps,
      totalDuration,
      thoughtSteps: steps.filter(s => s.type === 'thought').length,
      actionSteps: steps.filter(s => s.type === 'action').length,
      observationSteps: steps.filter(s => s.type === 'observation').length,
      toolsUsed: [...new Set(steps.filter(s => s.toolName).map(s => s.toolName))],
    };
  }, [execution]);

  const getStepIcon = (type: string, isSelected: boolean = false) => {
    const iconClass = cn(
      "h-5 w-5 transition-all duration-200",
      isSelected ? "scale-110" : ""
    );
    
    switch (type) {
      case 'thought':
        return <Brain className={cn(iconClass, "text-blue-500")} />;
      case 'action':
        return <Wrench className={cn(iconClass, "text-orange-500")} />;
      case 'observation':
        return <Eye className={cn(iconClass, "text-green-500")} />;
      case 'final_answer':
        return <CheckCircle className={cn(iconClass, "text-green-600")} />;
      default:
        return <AlertTriangle className={cn(iconClass, "text-gray-500")} />;
    }
  };

  const getStepDuration = (step: AgentStep, nextStep?: AgentStep) => {
    if (!nextStep) return null;
    return nextStep.timestamp.getTime() - step.timestamp.getTime();
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getStepProgress = (stepIndex: number) => {
    return ((stepIndex + 1) / flowData.steps.length) * 100;
  };

  return (
    <Card className={cn("h-full", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Zap className="h-5 w-5 text-blue-500" />
            Execution Flow
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {flowData.steps.length} steps
            </Badge>
            <Badge variant="outline" className="text-xs">
              {formatDuration(flowData.totalDuration)}
            </Badge>
          </div>
        </div>
        
        {/* Execution Summary */}
        <div className="grid grid-cols-4 gap-2 mt-3">
          <div className="text-center p-2 bg-blue-50 rounded-lg">
            <Brain className="h-4 w-4 text-blue-500 mx-auto mb-1" />
            <div className="text-xs font-medium">{flowData.thoughtSteps}</div>
            <div className="text-xs text-muted-foreground">Thoughts</div>
          </div>
          <div className="text-center p-2 bg-orange-50 rounded-lg">
            <Wrench className="h-4 w-4 text-orange-500 mx-auto mb-1" />
            <div className="text-xs font-medium">{flowData.actionSteps}</div>
            <div className="text-xs text-muted-foreground">Actions</div>
          </div>
          <div className="text-center p-2 bg-green-50 rounded-lg">
            <Eye className="h-4 w-4 text-green-500 mx-auto mb-1" />
            <div className="text-xs font-medium">{flowData.observationSteps}</div>
            <div className="text-xs text-muted-foreground">Observations</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <Wrench className="h-4 w-4 text-gray-500 mx-auto mb-1" />
            <div className="text-xs font-medium">{flowData.toolsUsed.length}</div>
            <div className="text-xs text-muted-foreground">Tools</div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <ScrollArea className="h-96">
          <div className="p-4">
            {/* Progress Bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Execution Progress</span>
                <span className="text-sm text-muted-foreground">
                  {execution.status === 'completed' ? '100%' : 
                   execution.status === 'running' ? `${Math.round(getStepProgress(flowData.steps.length - 1))}%` : 
                   '0%'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={cn(
                    "h-2 rounded-full transition-all duration-300",
                    execution.status === 'completed' ? "bg-green-500" :
                    execution.status === 'running' ? "bg-blue-500" :
                    execution.status === 'error' ? "bg-red-500" : "bg-gray-400"
                  )}
                  style={{ 
                    width: execution.status === 'completed' ? '100%' : 
                           execution.status === 'running' ? `${Math.round(getStepProgress(flowData.steps.length - 1))}%` : 
                           '0%' 
                  }}
                />
              </div>
            </div>

            {/* Flow Steps */}
            <div className="space-y-3">
              {flowData.steps.map((step, index) => {
                const isSelected = selectedStepId === step.id;
                const nextStep = flowData.steps[index + 1];
                const duration = getStepDuration(step, nextStep);
                const isLast = index === flowData.steps.length - 1;

                return (
                  <div key={step.id} className="relative">
                    {/* Step Node */}
                    <div 
                      className={cn(
                        "flex items-start gap-3 p-3 rounded-lg border-2 transition-all duration-200 cursor-pointer hover:shadow-md",
                        isSelected 
                          ? "border-blue-500 bg-blue-50 shadow-md" 
                          : "border-gray-200 hover:border-gray-300"
                      )}
                      onClick={() => onStepSelect?.(step.id)}
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        {getStepIcon(step.type, isSelected)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge 
                            variant={isSelected ? "default" : "secondary"} 
                            className="text-xs"
                          >
                            {step.type.replace('_', ' ').toUpperCase()}
                          </Badge>
                          {step.toolName && (
                            <Badge variant="outline" className="text-xs">
                              {step.toolName}
                            </Badge>
                          )}
                          {duration && (
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {formatDuration(duration)}
                            </div>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 line-clamp-2">
                          {step.content}
                        </p>
                      </div>
                    </div>

                    {/* Connection Arrow */}
                    {!isLast && (
                      <div className="flex justify-center py-2">
                        <ArrowDown className="h-4 w-4 text-gray-400" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

