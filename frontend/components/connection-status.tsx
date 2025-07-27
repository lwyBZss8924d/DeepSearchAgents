"use client";

// Connection status indicator for DeepSearchAgents
import { useAppContext } from "@/context/app-context";
import { Wifi, WifiOff } from "lucide-react";

export default function ConnectionStatus() {
  const { state } = useAppContext();
  const { isConnected } = state;

  return (
    <div className="flex items-center gap-2">
      {isConnected ? (
        <>
          <Wifi className="h-4 w-4 text-green-500" />
          <span className="text-sm text-green-500">Connected</span>
        </>
      ) : (
        <>
          <WifiOff className="h-4 w-4 text-red-500" />
          <span className="text-sm text-red-500">Disconnected</span>
        </>
      )}
    </div>
  );
}