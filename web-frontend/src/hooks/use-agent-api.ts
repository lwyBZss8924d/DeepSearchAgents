/**
 * Custom React hooks for DeepSearchAgents API integration
 */

import { useState, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient, ApiError } from '@/lib/api-client';
import { AgentType, AgentRequest, AgentResponse, AgentExecutionState } from '@/types/agent';

/**
 * Hook for executing agent searches with loading states and error handling
 */
export function useAgentExecution() {
  const [executionState, setExecutionState] = useState<AgentExecutionState>({
    isExecuting: false,
    currentStep: null,
    error: null,
    result: null,
  });

  const executeAgent = useMutation({
    mutationFn: async (request: AgentRequest): Promise<AgentResponse> => {
      setExecutionState(prev => ({
        ...prev,
        isExecuting: true,
        error: null,
        currentStep: 'Initializing agent...',
      }));

      try {
        let response: AgentResponse;
        
        switch (request.agentType) {
          case 'react':
            setExecutionState(prev => ({ ...prev, currentStep: 'Executing ReAct agent...' }));
            response = await apiClient.runReactAgent(request.userInput);
            break;
          case 'codact':
            setExecutionState(prev => ({ ...prev, currentStep: 'Executing CodeAct agent...' }));
            response = await apiClient.runDeepSearchAgent(request.userInput);
            break;
          default:
            setExecutionState(prev => ({ ...prev, currentStep: 'Executing agent...' }));
            response = await apiClient.runAgent(request);
            break;
        }

        setExecutionState(prev => ({
          ...prev,
          isExecuting: false,
          currentStep: 'Completed',
          result: response,
        }));

        return response;
      } catch (error) {
        const apiError = error instanceof ApiError ? error : new ApiError('Unknown error occurred');
        setExecutionState(prev => ({
          ...prev,
          isExecuting: false,
          error: apiError,
          currentStep: null,
        }));
        throw apiError;
      }
    },
    onSuccess: (data) => {
      console.log('Agent execution completed:', data);
    },
    onError: (error) => {
      console.error('Agent execution failed:', error);
    },
  });

  const resetExecution = useCallback(() => {
    setExecutionState({
      isExecuting: false,
      currentStep: null,
      error: null,
      result: null,
    });
  }, []);

  return {
    executeAgent: executeAgent.mutate,
    executionState,
    resetExecution,
    isLoading: executeAgent.isPending,
    error: executeAgent.error,
  };
}

/**
 * Hook for ReAct agent specifically
 */
export function useReactAgent() {
  return useMutation({
    mutationFn: (userInput: string) => apiClient.runReactAgent(userInput),
    onError: (error) => {
      console.error('ReAct agent execution failed:', error);
    },
  });
}

/**
 * Hook for DeepSearch agent specifically
 */
export function useDeepSearchAgent() {
  return useMutation({
    mutationFn: (userInput: string) => apiClient.runDeepSearchAgent(userInput),
    onError: (error) => {
      console.error('DeepSearch agent execution failed:', error);
    },
  });
}

/**
 * Hook for API health check
 */
export function useApiHealth() {
  return useQuery({
    queryKey: ['api-health'],
    queryFn: () => apiClient.healthCheck(),
    refetchInterval: 30000, // Check every 30 seconds
    retry: 3,
    staleTime: 10000, // Consider data stale after 10 seconds
  });
}

/**
 * Hook for managing agent configuration
 */
export function useAgentConfig() {
  const [config, setConfig] = useState<{
    agentType: AgentType;
    modelArgs?: Record<string, any>;
  }>({
    agentType: 'codact',
  });

  const updateConfig = useCallback((updates: Partial<typeof config>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

  const resetConfig = useCallback(() => {
    setConfig({ agentType: 'codact' });
  }, []);

  return {
    config,
    updateConfig,
    resetConfig,
  };
}

// Export types for convenience
export type { AgentType, AgentRequest, AgentResponse, AgentExecutionState };

