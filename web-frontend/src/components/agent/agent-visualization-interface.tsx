"use client";

import React, { useState, useMemo } from 'react';
import { 
  BarChart3, 
  Brain, 
  Wrench, 
  Zap, 
  Eye,
  Settings,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AgentExecution } from '@/types/agent';
import { cn } from '@/lib/utils';

// Import our visualization components
import { ExecutionFlowDiagram } from './execution-flow-diagram';
import { ToolCallVisualizer } from './tool-call-visualizer';
import { ReasoningExplorer } from './reasoning-explorer';
import { StreamingOutput } from './streaming-output';

interface AgentVisualizationInterfaceProps {
  execution: AgentExecution;
  isStreaming?: boolean;
  className?: string;
}

type ViewMode = 'overview' | 'flow' | 'tools' | 'reasoning' | 'stream';

export function AgentVisualizationInterface({ 
  execution, 
  isStreaming = false,
  className 
}: AgentVisualizationInterfaceProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('overview');
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const executionStats = useMemo(() => {
    const steps = execution.steps;
    const duration = execution.endTime 
      ? execution.endTime.getTime() - execution.startTime.getTime()
      : Date.now() - execution.startTime.getTime();

    return {
      totalSteps: steps.length,
      thoughtSteps: steps.filter(s => s.type === 'thought').length,
      actionSteps: steps.filter(s => s.type === 'action').length,
      observationSteps: steps.filter(s => s.type === 'observation').length,
      toolsUsed: [...new Set(steps.filter(s => s.toolName).map(s => s.toolName))].length,
      duration,
      status: execution.status
    };
  }, [execution]);

  const getViewModeIcon = (mode: ViewMode) => {
    switch (mode) {
      case 'overview':
        return <BarChart3 className="h-4 w-4" />;
      case 'flow':
        return <Zap className="h-4 w-4" />;
      case 'tools':
        return <Wrench className="h-4 w-4" />;
      case 'reasoning':
        return <Brain className="h-4 w-4" />;
      case 'stream':
        return <Eye className="h-4 w-4" />;
      default:
        return <BarChart3 className="h-4 w-4" />;
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'running':
        return 'text-blue-600 bg-blue-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      case 'cancelled':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const renderViewContent = () => {
    switch (viewMode) {
      case 'flow':
        return (
          <ExecutionFlowDiagram
            execution={execution}
            selectedStepId={selectedStepId || undefined}
            onStepSelect={setSelectedStepId}
            className="h-full"
          />
        );
      case 'tools':
        return (
          <ToolCallVisualizer
            steps={execution.steps}
            selectedStepId={selectedStepId || undefined}
            className="h-full"
          />
        );
      case 'reasoning':
        return (
          <ReasoningExplorer
            steps={execution.steps}
            selectedStepId={selectedStepId || undefined}
            onStepSelect={setSelectedStepId}
            className="h-full"
          />
        );
      case 'stream':
        return (
          <StreamingOutput
            steps={execution.steps}
            isStreaming={isStreaming}
            className="h-full"
          />
        );
      case 'overview':
      default:
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
            <ExecutionFlowDiagram
              execution={execution}
              selectedStepId={selectedStepId || undefined}
              onStepSelect={setSelectedStepId}
              className="h-full"
            />
            <div className="space-y-4">
              <ToolCallVisualizer
                steps={execution.steps}
                selectedStepId={selectedStepId || undefined}
                className="h-64"
              />
              <ReasoningExplorer
                steps={execution.steps}
                selectedStepId={selectedStepId || undefined}
                onStepSelect={setSelectedStepId}
                className="h-64"
              />
            </div>
          </div>
        );
    }
  };

  return (
    <Card className={cn("h-full flex flex-col", className)}>
      <CardHeader className="pb-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5 text-blue-500" />
              Agent Execution Visualization
            </CardTitle>
            <Badge className={cn("text-xs", getStatusColor(executionStats.status))}>
              {executionStats.status.toUpperCase()}
            </Badge>
            {isStreaming && (
              <Badge variant="outline" className="text-xs animate-pulse">
                Live
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              {isExpanded ? 
                <Minimize2 className="h-4 w-4" /> : 
                <Maximize2 className="h-4 w-4" />
              }
            </button>
          </div>
        </div>

        {/* Execution Summary */}
        <div className="grid grid-cols-5 gap-2 mt-3">
          <div className="text-center p-2 bg-blue-50 rounded-lg">
            <div className="text-sm font-medium text-blue-700">{executionStats.totalSteps}</div>
            <div className="text-xs text-blue-600">Total Steps</div>
          </div>
          <div className="text-center p-2 bg-purple-50 rounded-lg">
            <div className="text-sm font-medium text-purple-700">{executionStats.thoughtSteps}</div>
            <div className="text-xs text-purple-600">Thoughts</div>
          </div>
          <div className="text-center p-2 bg-orange-50 rounded-lg">
            <div className="text-sm font-medium text-orange-700">{executionStats.actionSteps}</div>
            <div className="text-xs text-orange-600">Actions</div>
          </div>
          <div className="text-center p-2 bg-green-50 rounded-lg">
            <div className="text-sm font-medium text-green-700">{executionStats.toolsUsed}</div>
            <div className="text-xs text-green-600">Tools</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <div className="text-sm font-medium text-gray-700">{formatDuration(executionStats.duration)}</div>
            <div className="text-xs text-gray-600">Duration</div>
          </div>
        </div>
        {/* View Mode Selector */}
        <div className="flex gap-1 mt-3 p-1 bg-gray-100 rounded-lg">
          {(['overview', 'flow', 'tools', 'reasoning', 'stream'] as ViewMode[]).map(mode => (
            <button
              key={mode}
              className={cn(
                "flex items-center gap-2 px-3 py-2 text-xs rounded-md transition-colors flex-1 justify-center",
                viewMode === mode 
                  ? "bg-white text-blue-600 shadow-sm" 
                  : "text-gray-600 hover:text-gray-800"
              )}
              onClick={() => setViewMode(mode)}
            >
              {getViewModeIcon(mode)}
              <span className="capitalize">{mode}</span>
            </button>
          ))}
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 p-0 overflow-hidden">
        <div className={cn(
          "h-full transition-all duration-300",
          isExpanded ? "fixed inset-4 z-50 bg-white rounded-lg shadow-2xl" : ""
        )}>
          {isExpanded && (
            <div className="absolute top-4 right-4 z-10">
              <button
                onClick={() => setIsExpanded(false)}
                className="p-2 bg-white rounded-full shadow-md hover:bg-gray-50"
              >
                <Minimize2 className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className="h-full p-4">
            {renderViewContent()}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

