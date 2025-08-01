"use client";

// Connection status indicator for DeepSearchAgents
import { useAppContext } from "@/context/app-context";
import { WifiIcon, WifiOffIcon } from "@/components/terminal-icons";

export default function ConnectionStatus() {
  const { state } = useAppContext();
  const { isConnected } = state;

  return (
    <div className="flex items-center gap-2">
      {isConnected ? (
        <>
          <WifiIcon className="h-4 w-4 text-green-500" />
          <span className="text-sm text-green-500">Connected</span>
        </>
      ) : (
        <>
          <WifiOffIcon className="h-4 w-4 text-red-500" />
          <span className="text-sm text-red-500">Disconnected</span>
        </>
      )}
    </div>
  );
}