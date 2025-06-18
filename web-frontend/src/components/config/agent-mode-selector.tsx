"use client";

import React from 'react';
import { Brain, Code, Zap } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useConfigStore } from '@/hooks/use-config-store';
import type { AgentMode, AgentModeOption } from '@/types/config';
import { cn } from '@/lib/utils';

const agentModeOptions: AgentModeOption[] = [
  {
    value: 'react',
    label: 'ReAct Agent',
    description: 'Reasoning and Acting agent that uses chain-of-thought reasoning to solve problems step by step.',
    icon: 'brain',
  },
  {
    value: 'codact',
    label: 'CodeAct Agent',
    description: 'Code-based agent that can execute Python code and use advanced tools for complex tasks.',
    icon: 'code',
  },
];

const getIcon = (iconName: string) => {
  switch (iconName) {
    case 'brain':
      return <Brain className="h-6 w-6" />;
    case 'code':
      return <Code className="h-6 w-6" />;
    default:
      return <Zap className="h-6 w-6" />;
  }
};

interface AgentModeSelectorProps {
  className?: string;
  showDescription?: boolean;
}

export function AgentModeSelector({ 
  className,
  showDescription = true 
}: AgentModeSelectorProps) {
  const { preferences, setAgentMode } = useConfigStore();
  const selectedMode = preferences.selectedAgentMode;

  const handleModeSelect = (mode: AgentMode) => {
    setAgentMode(mode);
  };

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Agent Mode</h3>
        <Badge variant="secondary" className="capitalize">
          {selectedMode}
        </Badge>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agentModeOptions.map((option) => (
          <Card
            key={option.value}
            className={cn(
              "p-4 cursor-pointer transition-all duration-200 hover:shadow-md",
              selectedMode === option.value
                ? "ring-2 ring-primary bg-primary/5"
                : "hover:bg-muted/50"
            )}
            onClick={() => handleModeSelect(option.value)}
          >
            <div className="flex items-start space-x-3">
              <div className={cn(
                "p-2 rounded-lg",
                selectedMode === option.value ? "bg-primary text-primary-foreground" : "bg-muted"
              )}>
                {getIcon(option.icon)}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm">{option.label}</h4>
                {showDescription && (
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    {option.description}
                  </p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}


