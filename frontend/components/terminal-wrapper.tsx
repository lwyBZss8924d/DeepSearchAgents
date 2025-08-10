"use client";

import dynamic from 'next/dynamic';

// Dynamically import Terminal with SSR disabled
const Terminal = dynamic(() => import('./terminal'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full min-h-[400px] bg-[#0c0c0c] text-white">
      <p className="text-sm">Loading terminal...</p>
    </div>
  )
});

export default Terminal;