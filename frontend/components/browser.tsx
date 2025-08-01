"use client";

// Simplified Browser component for DeepSearchAgents
import React from "react";
import { Globe, ExternalLink, Info } from "lucide-react";
import { useAppContext } from "@/context/app-context";
import { DSButton } from "@/components/ds";

interface BrowserProps {
  className?: string;
}

const Browser = React.memo(({ className }: BrowserProps) => {
  const { state } = useAppContext();
  const { messages, currentStep } = state;

  // Find any web content for current step
  const stepMessages = messages.filter(m => m.step_number === currentStep);
  const urlPattern = /https?:\/\/[^\s]+/g;
  
  // Extract URLs from messages
  const urls: string[] = [];
  stepMessages.forEach(message => {
    const matches = message.content.match(urlPattern);
    if (matches) {
      urls.push(...matches);
    }
  });

  // Get unique URLs
  const uniqueUrls = [...new Set(urls)];

  return (
    <div className={`flex flex-col h-full w-full ${className}`}>
      {/* Browser Header */}
      <div className="flex items-center justify-between p-3 border-b bg-background">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4" />
          <span className="text-sm font-medium">
            Web Browser
          </span>
          <span className="text-sm text-muted-foreground">
            Step {currentStep}
          </span>
        </div>
      </div>

      {/* Browser Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        {uniqueUrls.length > 0 ? (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground mb-4">
              URLs visited in this step:
            </div>
            {uniqueUrls.map((url, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-muted rounded-lg"
              >
                <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-sm text-blue-500 hover:underline truncate"
                >
                  {url}
                </a>
                <DSButton
                  variant="ghost"
                  size="sm"
                  onClick={() => window.open(url, "_blank")}
                >
                  <ExternalLink className="h-4 w-4" />
                </DSButton>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Info className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">
              No web content for this step
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              Web browsing activity will appear here when the agent visits websites
            </p>
          </div>
        )}
      </div>
    </div>
  );
});

Browser.displayName = "Browser";

export default Browser;