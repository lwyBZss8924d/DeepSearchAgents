"use client";

import React from 'react';
import { ExternalLink, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SearchResult, AgentExecution } from '@/types/agent';
import { cn } from '@/lib/utils';

interface ResultsDisplayProps {
  execution?: AgentExecution;
  searchResults?: SearchResult[];
  className?: string;
}

export function ResultsDisplay({ 
  execution, 
  searchResults = [], 
  className 
}: ResultsDisplayProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const formatDuration = (start: Date, end?: Date) => {
    const endTime = end || new Date();
    const duration = Math.round((endTime.getTime() - start.getTime()) / 1000);
    return `${duration}s`;
  };

  if (!execution && searchResults.length === 0) {
    return (
      <div className={cn("flex items-center justify-center h-64 text-muted-foreground", className)}>
        <div className="text-center">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No results yet</p>
          <p className="text-sm">Start a search to see results here</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {execution && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                {getStatusIcon(execution.status)}
                Agent Execution
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{execution.config.type}</Badge>
                <Badge variant="secondary">
                  {formatDuration(execution.startTime, execution.endTime)}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div>
                <span className="text-sm font-medium text-muted-foreground">Query:</span>
                <p className="text-sm mt-1">{execution.query}</p>
              </div>
              {execution.finalAnswer && (
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Final Answer:</span>
                  <p className="text-sm mt-1 p-3 bg-muted rounded-md">{execution.finalAnswer}</p>
                </div>
              )}
              {execution.error && (
                <div>
                  <span className="text-sm font-medium text-red-500">Error:</span>
                  <p className="text-sm mt-1 p-3 bg-red-50 text-red-700 rounded-md">{execution.error}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {searchResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Search Results ({searchResults.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-64">
              <div className="space-y-3">
                {searchResults.map((result) => (
                  <div key={result.id} className="border-b pb-3 last:border-b-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-sm truncate">{result.title}</h4>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {result.snippet}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs text-blue-600 truncate">{result.url}</span>
                          {result.score && (
                            <Badge variant="outline" className="text-xs">
                              {Math.round(result.score * 100)}%
                            </Badge>
                          )}
                        </div>
                      </div>
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-shrink-0 p-1 hover:bg-accent rounded"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

