"use client";

import AgentLayoutV2 from "@/components/agent-layout";
// import DebugPanel from "@/components/debug-panel";

export default function HomeContent() {
  return (
    <>
      <AgentLayoutV2 />
      {/* Debug panel disabled for production - uncomment for debugging */}
      {/* <DebugPanel /> */}
    </>
  );
}