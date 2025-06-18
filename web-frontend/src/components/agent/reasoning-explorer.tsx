"use client";

import React, { useState, useMemo } from 'react';
import { 
  Brain, 
  Lightbulb, 
  Target, 
  ArrowRight, 
  ChevronDown, 
  ChevronRight,
  MessageSquare,
  Zap,
  Search,
  BookOpen
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AgentStep } from '@/types/agent';
import { cn } from '@/lib/utils';

interface ReasoningExplorerProps {
  steps: AgentStep[];
  selectedStepId?: string;
  onStepSelect?: (stepId: string) => void;
  className?: string;
}

interface ReasoningChain {
  id: string;
  thought: AgentStep;
  relatedActions: AgentStep[];
  observations: AgentStep[];
  outcome?: string;
  confidence?: number;
}

export function ReasoningExplorer({ 
  steps, 
  selectedStepId,
  onStepSelect,
  className 
}: ReasoningExplorerProps) {
  const [expandedChains, setExpandedChains] = useState<Set<string>>(new Set());
  const [analysisMode, setAnalysisMode] = useState<'chains' | 'insights'>('chains');

  const reasoningChains: ReasoningChain[] = useMemo(() => {
    const thoughtSteps = steps.filter(step => step.type === 'thought');
    
    return thoughtSteps.map((thought, index) => {
      const nextThought = thoughtSteps[index + 1];
      const chainEndTime = nextThought ? nextThought.timestamp : new Date();
      
      const relatedActions = steps.filter(step => 
        step.type === 'action' && 
        step.timestamp > thought.timestamp && 
        step.timestamp < chainEndTime
      );
      
      const observations = steps.filter(step => 
        step.type === 'observation' && 
        step.timestamp > thought.timestamp && 
        step.timestamp < chainEndTime
      );

      return {
        id: thought.id,
        thought,
        relatedActions,
        observations,
        outcome: observations[observations.length - 1]?.content,
        confidence: Math.random() * 0.4 + 0.6 // Mock confidence score
      };
    });
  }, [steps]);

  const reasoningInsights = useMemo(() => {
    const totalThoughts = reasoningChains.length;
    const successfulChains = reasoningChains.filter(chain => 
      chain.relatedActions.length > 0 && chain.observations.length > 0
    ).length;
    
    const avgActionsPerThought = totalThoughts > 0 ? 
      reasoningChains.reduce((sum, chain) => sum + chain.relatedActions.length, 0) / totalThoughts : 0;
    
    const commonPatterns = [
      { pattern: 'Search → Analyze → Conclude', frequency: 3 },
      { pattern: 'Question → Research → Synthesize', frequency: 2 },
      { pattern: 'Hypothesis → Test → Refine', frequency: 1 }
    ];

    return {
      totalThoughts,
      successfulChains,
      successRate: totalThoughts > 0 ? (successfulChains / totalThoughts) * 100 : 0,
      avgActionsPerThought: Math.round(avgActionsPerThought * 10) / 10,
      commonPatterns
    };
  }, [reasoningChains]);

  const toggleExpanded = (chainId: string) => {
    const newExpanded = new Set(expandedChains);
    if (newExpanded.has(chainId)) {
      newExpanded.delete(chainId);
    } else {
      newExpanded.add(chainId);
    }
    setExpandedChains(newExpanded);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const extractKeywords = (text: string) => {
    const words = text.toLowerCase().split(/\W+/);
    const keywords = words.filter(word => 
      word.length > 4 && 
      !['should', 'would', 'could', 'might', 'think', 'need'].includes(word)
    );
    return keywords.slice(0, 3);
  };

  if (reasoningChains.length === 0) {
    return (
      <Card className={cn("h-full", className)}>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center text-muted-foreground">
            <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No reasoning steps yet</p>
            <p className="text-sm">Agent thoughts will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("h-full", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            Reasoning Analysis
          </CardTitle>
          <div className="flex gap-1">
            <button
              className={cn(
                "px-3 py-1 text-xs rounded-md transition-colors",
                analysisMode === 'chains' 
                  ? "bg-purple-100 text-purple-700" 
                  : "text-gray-600 hover:bg-gray-100"
              )}
              onClick={() => setAnalysisMode('chains')}
            >
              Chains
            </button>
            <button
              className={cn(
                "px-3 py-1 text-xs rounded-md transition-colors",
                analysisMode === 'insights' 
                  ? "bg-purple-100 text-purple-700" 
                  : "text-gray-600 hover:bg-gray-100"
              )}
              onClick={() => setAnalysisMode('insights')}
            >
              Insights
            </button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <ScrollArea className="h-96">
          <div className="p-4">
            {analysisMode === 'insights' ? (
              <div className="space-y-4">
                {/* Reasoning Statistics */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Brain className="h-4 w-4 text-purple-500" />
                      <span className="text-sm font-medium">Total Thoughts</span>
                    </div>
                    <div className="text-2xl font-bold text-purple-700">
                      {reasoningInsights.totalThoughts}
                    </div>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Target className="h-4 w-4 text-green-500" />
                      <span className="text-sm font-medium">Success Rate</span>
                    </div>
                    <div className="text-2xl font-bold text-green-700">
                      {reasoningInsights.successRate.toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Common Patterns */}
                <div>
                  <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Zap className="h-4 w-4" />
                    Reasoning Patterns
                  </h4>
                  <div className="space-y-2">
                    {reasoningInsights.commonPatterns.map((pattern, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <span className="text-sm">{pattern.pattern}</span>
                        <Badge variant="secondary" className="text-xs">
                          {pattern.frequency}x
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {reasoningChains.map((chain, index) => {
                  const isExpanded = expandedChains.has(chain.id);
                  const isSelected = selectedStepId === chain.id;
                  const keywords = extractKeywords(chain.thought.content);

                  return (
                    <div 
                      key={chain.id}
                      className={cn(
                        "border rounded-lg transition-all duration-200",
                        isSelected ? "border-purple-500 bg-purple-50" : "border-gray-200"
                      )}
                    >
                      {/* Chain Header */}
                      <div 
                        className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                        onClick={() => toggleExpanded(chain.id)}
                      >
                        <div className="flex items-center gap-3">
                          {isExpanded ? 
                            <ChevronDown className="h-4 w-4 text-gray-500" /> : 
                            <ChevronRight className="h-4 w-4 text-gray-500" />
                          }
                          <div className="flex items-center gap-2">
                            <Lightbulb className="h-4 w-4 text-yellow-500" />
                            <span className="font-medium text-sm">
                              Reasoning Chain {index + 1}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge 
                            className={cn("text-xs", getConfidenceColor(chain.confidence || 0))}
                          >
                            {((chain.confidence || 0) * 100).toFixed(0)}% confidence
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {chain.relatedActions.length} actions
                          </Badge>
                        </div>
                      </div>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <div className="border-t bg-white p-4">
                          {/* Thought Content */}
                          <div className="mb-4">
                            <div className="flex items-center gap-2 mb-2">
                              <MessageSquare className="h-4 w-4 text-blue-500" />
                              <span className="text-sm font-medium">Thought Process</span>
                            </div>
                            <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded">
                              {chain.thought.content}
                            </p>
                            
                            {/* Keywords */}
                            {keywords.length > 0 && (
                              <div className="flex items-center gap-2 mt-2">
                                <span className="text-xs text-gray-500">Key concepts:</span>
                                {keywords.map(keyword => (
                                  <Badge key={keyword} variant="outline" className="text-xs">
                                    {keyword}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Actions and Outcomes */}
                          {chain.relatedActions.length > 0 && (
                            <div className="mb-4">
                              <div className="flex items-center gap-2 mb-2">
                                <ArrowRight className="h-4 w-4 text-orange-500" />
                                <span className="text-sm font-medium">Actions Taken</span>
                              </div>
                              <div className="space-y-2">
                                {chain.relatedActions.map(action => (
                                  <div key={action.id} className="flex items-center gap-2 text-sm">
                                    <div className="w-2 h-2 bg-orange-400 rounded-full" />
                                    <span>{action.toolName || 'Unknown tool'}</span>
                                    <span className="text-gray-500 text-xs">
                                      {action.timestamp.toLocaleTimeString()}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Outcome */}
                          {chain.outcome && (
                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <BookOpen className="h-4 w-4 text-green-500" />
                                <span className="text-sm font-medium">Outcome</span>
                              </div>
                              <p className="text-sm text-gray-700 bg-green-50 p-3 rounded">
                                {chain.outcome.length > 200 ? 
                                  `${chain.outcome.substring(0, 200)}...` : 
                                  chain.outcome
                                }
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

