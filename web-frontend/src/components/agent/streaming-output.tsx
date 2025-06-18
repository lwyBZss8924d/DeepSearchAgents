"use client";

import React, { useEffect, useRef } from 'react';
import { Brain, Wrench, Eye, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AgentStep } from '@/types/agent';
import { cn } from '@/lib/utils';

interface StreamingOutputProps {
  steps: AgentStep[];
  isStreaming?: boolean;
  className?: string;
}

export function StreamingOutput({ 
  steps, 
  isStreaming = false, 
  className 
}: StreamingOutputProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new steps are added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps]);

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'thought':
        return <Brain className="h-4 w-4 text-blue-500" />;
      case 'action':
        return <Wrench className="h-4 w-4 text-orange-500" />;
      case 'observation':
        return <Eye className="h-4 w-4 text-green-500" />;
      case 'final_answer':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStepBadgeVariant = (type: string) => {
    switch (type) {
      case 'thought':
        return 'default';
      case 'action':
        return 'secondary';
      case 'observation':
        return 'outline';
      case 'final_answer':
        return 'default';
      default:
        return 'outline';
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  if (steps.length === 0 && !isStreaming) {
    return (
      <div className={cn("flex items-center justify-center h-64 text-muted-foreground", className)}>
        <div className="text-center">
          <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No agent steps yet</p>
          <p className="text-sm">Agent execution steps will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <Card className={cn("h-full", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Agent Execution Steps
          </CardTitle>
          {isStreaming && (
            <Badge variant="outline" className="animate-pulse">
              Streaming...
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-96" ref={scrollRef}>
          <div className="p-4 space-y-4">
            {steps.map((step, index) => (
              <div key={step.id} className="flex gap-3">
                <div className="flex-shrink-0 mt-1">
                  {getStepIcon(step.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant={getStepBadgeVariant(step.type)} className="text-xs">
                      {step.type.replace('_', ' ').toUpperCase()}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatTimestamp(step.timestamp)}
                    </span>
                    {step.toolName && (
                      <Badge variant="outline" className="text-xs">
                        {step.toolName}
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm space-y-2">
                    <p className="whitespace-pre-wrap">{step.content}</p>
                    {step.error && (
                      <div className="p-2 bg-red-50 text-red-700 rounded text-xs">
                        <strong>Error:</strong> {step.error}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

