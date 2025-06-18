"use client";

import React, { useState } from 'react';
import { 
  Wrench, 
  ChevronDown, 
  ChevronRight, 
  Play, 
  CheckCircle, 
  XCircle, 
  Clock,
  Code,
  FileText,
  Database,
  Globe
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AgentStep } from '@/types/agent';
import { cn } from '@/lib/utils';

interface ToolCallVisualizerProps {
  steps: AgentStep[];
  selectedStepId?: string;
  className?: string;
}

interface ToolCallData {
  step: AgentStep;
  toolName: string;
  input: any;
  output: any;
  duration?: number;
  status: 'success' | 'error' | 'running';
}

export function ToolCallVisualizer({ 
  steps, 
  selectedStepId,
  className 
}: ToolCallVisualizerProps) {
  const [expandedCalls, setExpandedCalls] = useState<Set<string>>(new Set());
  const [selectedTab, setSelectedTab] = useState<'input' | 'output'>('input');

  const toolCalls: ToolCallData[] = React.useMemo(() => {
    return steps
      .filter(step => step.type === 'action' && step.toolName)
      .map(step => {
        const nextStep = steps.find(s => 
          s.timestamp > step.timestamp && s.type === 'observation'
        );
        
        return {
          step,
          toolName: step.toolName!,
          input: step.toolInput,
          output: step.toolOutput || nextStep?.content,
          duration: nextStep ? 
            nextStep.timestamp.getTime() - step.timestamp.getTime() : 
            undefined,
          status: step.error ? 'error' : nextStep ? 'success' : 'running'
        };
      });
  }, [steps]);

  const toggleExpanded = (stepId: string) => {
    const newExpanded = new Set(expandedCalls);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedCalls(newExpanded);
  };

  const getToolIcon = (toolName: string) => {
    const iconClass = "h-4 w-4";
    
    switch (toolName.toLowerCase()) {
      case 'search':
      case 'web_search':
        return <Globe className={cn(iconClass, "text-blue-500")} />;
      case 'readurl':
      case 'read_url':
        return <FileText className={cn(iconClass, "text-green-500")} />;
      case 'code':
      case 'python':
        return <Code className={cn(iconClass, "text-purple-500")} />;
      case 'embed':
      case 'rerank':
        return <Database className={cn(iconClass, "text-orange-500")} />;
      default:
        return <Wrench className={cn(iconClass, "text-gray-500")} />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Play className="h-4 w-4 text-blue-500 animate-pulse" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatJson = (data: any) => {
    if (typeof data === 'string') return data;
    return JSON.stringify(data, null, 2);
  };

  const toolStats = React.useMemo(() => {
    const stats = toolCalls.reduce((acc, call) => {
      const tool = call.toolName;
      if (!acc[tool]) {
        acc[tool] = { count: 0, success: 0, error: 0, totalDuration: 0 };
      }
      acc[tool].count++;
      if (call.status === 'success') acc[tool].success++;
      if (call.status === 'error') acc[tool].error++;
      if (call.duration) acc[tool].totalDuration += call.duration;
      return acc;
    }, {} as Record<string, any>);

    return Object.entries(stats).map(([tool, data]) => ({
      tool,
      ...data,
      avgDuration: data.count > 0 ? data.totalDuration / data.count : 0,
      successRate: data.count > 0 ? (data.success / data.count) * 100 : 0
    }));
  }, [toolCalls]);

  if (toolCalls.length === 0) {
    return (
      <Card className={cn("h-full", className)}>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center text-muted-foreground">
            <Wrench className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No tool calls yet</p>
            <p className="text-sm">Tool executions will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("h-full", className)}>
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Wrench className="h-5 w-5 text-orange-500" />
          Tool Call Analysis
        </CardTitle>
        
        {/* Tool Statistics */}
        <div className="grid grid-cols-2 gap-2 mt-3">
          {toolStats.slice(0, 4).map(stat => (
            <div key={stat.tool} className="p-2 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                {getToolIcon(stat.tool)}
                <span className="text-xs font-medium truncate">{stat.tool}</span>
              </div>
              <div className="text-xs text-muted-foreground">
                {stat.count} calls • {stat.successRate.toFixed(0)}% success
              </div>
            </div>
          ))}
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <ScrollArea className="h-96">
          <div className="p-4 space-y-3">
            {toolCalls.map((call) => {
              const isExpanded = expandedCalls.has(call.step.id);
              const isSelected = selectedStepId === call.step.id;

              return (
                <div 
                  key={call.step.id}
                  className={cn(
                    "border rounded-lg transition-all duration-200",
                    isSelected ? "border-blue-500 bg-blue-50" : "border-gray-200"
                  )}
                >
                  {/* Tool Call Header */}
                  <div 
                    className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => toggleExpanded(call.step.id)}
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? 
                        <ChevronDown className="h-4 w-4 text-gray-500" /> : 
                        <ChevronRight className="h-4 w-4 text-gray-500" />
                      }
                      {getToolIcon(call.toolName)}
                      <div>
                        <div className="font-medium text-sm">{call.toolName}</div>
                        <div className="text-xs text-muted-foreground">
                          {call.step.timestamp.toLocaleTimeString()}
                          {call.duration && ` • ${formatDuration(call.duration)}`}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(call.status)}
                      <Badge 
                        variant={call.status === 'success' ? 'default' : 
                                call.status === 'error' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {call.status}
                      </Badge>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="border-t bg-white">
                      {/* Tab Navigation */}
                      <div className="flex border-b">
                        <button
                          className={cn(
                            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                            selectedTab === 'input' 
                              ? "border-blue-500 text-blue-600" 
                              : "border-transparent text-gray-500 hover:text-gray-700"
                          )}
                          onClick={() => setSelectedTab('input')}
                        >
                          Input
                        </button>
                        <button
                          className={cn(
                            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                            selectedTab === 'output' 
                              ? "border-blue-500 text-blue-600" 
                              : "border-transparent text-gray-500 hover:text-gray-700"
                          )}
                          onClick={() => setSelectedTab('output')}
                        >
                          Output
                        </button>
                      </div>

                      {/* Tab Content */}
                      <div className="p-4">
                        {selectedTab === 'input' ? (
                          <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                            {formatJson(call.input || call.step.content)}
                          </pre>
                        ) : (
                          <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                            {formatJson(call.output || 'No output available')}
                          </pre>
                        )}
                        
                        {call.step.error && (
                          <div className="mt-3 p-3 bg-red-50 text-red-700 rounded text-xs">
                            <strong>Error:</strong> {call.step.error}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

