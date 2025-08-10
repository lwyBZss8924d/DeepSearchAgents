// Temporary stub for use-app-events hook
// TODO: Update to work with v2 API DSAgentRunMessage format

import { useCallback } from "react";

export const useAppEvents = () => {
  const handleEvent = useCallback((data: any) => {
    console.log('App event received (disabled):', data);
  }, []);

  return { handleEvent };
};