// Hook for session creation and management
import { useState, useCallback } from 'react';
import { CreateSessionRequest, CreateSessionResponse } from '@/types/api.types';

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const createSession = useCallback(async (options: CreateSessionRequest) => {
    setIsCreating(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v2/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: options.agent_type,
          max_steps: options.max_steps || 20
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to create session');
      }
      
      const data: CreateSessionResponse = await response.json();
      setSessionId(data.session_id);
      return data.session_id;
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setIsCreating(false);
    }
  }, []);
  
  const clearSession = useCallback(() => {
    setSessionId(null);
    setError(null);
  }, []);
  
  return {
    sessionId,
    isCreating,
    error,
    createSession,
    clearSession
  };
}