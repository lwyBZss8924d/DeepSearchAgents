"use client";

// Simplified Terminal for execution log display
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { forwardRef, Ref, useEffect, useRef, useState } from "react";
import "@xterm/xterm/css/xterm.css";
import { DSButton } from '@/components/ds';
// Terminal-style ASCII icons instead of lucide-react
import { useAppContext } from '@/context/app-context';
import { extractExecutionLogs, isTerminalMessage } from '@/utils/extractors';

interface TerminalProps {
  className?: string;
}

const Terminal = (
  { className }: TerminalProps,
  xtermRef: Ref<XTerm | null>
) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const { state } = useAppContext();
  const { messages } = state;
  const [copied, setCopied] = useState(false);
  const termRef = useRef<XTerm | null>(null);

  // Initialize xterm once
  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new XTerm({
      cursorBlink: false,  // No cursor for read-only
      disableStdin: true,  // Disable input
      fontSize: 14,
      fontFamily: 'var(--ds-font-mono)',
      theme: {
        background: "#0c0c0c",
        foreground: "#cccccc",
        cursor: "transparent",  // Hide cursor
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5'
      },
      allowTransparency: true,
      scrollback: 1000,
    });

    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    term.loadAddon(fitAddon);

    term.open(terminalRef.current);
    
    // Ensure DOM is ready and has dimensions before fitting
    const attemptFit = () => {
      if (terminalRef.current && 
          terminalRef.current.offsetWidth > 0 && 
          terminalRef.current.offsetHeight > 0) {
        try {
          fitAddon.fit();
        } catch (error) {
          console.warn('Terminal fit error:', error);
        }
      } else {
        // Retry after a short delay if dimensions not ready
        setTimeout(attemptFit, 100);
      }
    };
    
    // Use requestAnimationFrame to ensure layout is complete
    requestAnimationFrame(attemptFit);
    
    termRef.current = term;

    // Set ref for parent
    if (typeof xtermRef === "function") {
      xtermRef(term);
    } else if (xtermRef) {
      xtermRef.current = term;
    }

    // Welcome message
    term.writeln('\x1b[36m> DeepSearchAgents Terminal (Read-Only)\x1b[0m');
    term.writeln('\x1b[90m> Execution logs will appear here...\x1b[0m');
    term.writeln('');

    // Handle resize
    const handleResize = () => {
      if (terminalRef.current && 
          terminalRef.current.offsetWidth > 0 && 
          terminalRef.current.offsetHeight > 0) {
        try {
          fitAddon.fit();
        } catch (error) {
          console.warn('Terminal resize fit error:', error);
        }
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      term.dispose();
    };
  }, []);

  // Update terminal content when messages change
  useEffect(() => {
    if (!termRef.current) return;

    // Filter messages that should appear in terminal (based on metadata)
    const terminalMessages = messages.filter(m => {
      // Check if this message is meant for terminal component
      return m.metadata?.component === 'terminal' || isTerminalMessage(m.metadata);
    });
    
    // Clear terminal
    termRef.current.clear();
    
    // Write header
    termRef.current.writeln(`\x1b[36m> DeepSearchAgents Terminal\x1b[0m`);
    termRef.current.writeln('\x1b[90m' + '─'.repeat(50) + '\x1b[0m');
    termRef.current.writeln('');

    let hasLogs = false;

    // Display all terminal messages (not filtered by current step)
    terminalMessages.forEach((message, index) => {
      hasLogs = true;
      
      // Add step indicator with color
      if (message.step_number !== undefined && message.step_number > 0) {
        termRef.current?.writeln(`\x1b[33m━━━ Step ${message.step_number} ━━━\x1b[0m`);
      }
      
      // Show message type if available
      if (message.metadata?.title) {
        termRef.current?.writeln(`\x1b[36m${message.metadata.title}\x1b[0m`);
      }
      
      // Extract and display content
      const logs = extractExecutionLogs(message.content);
      if (logs.length > 0) {
        logs.forEach(log => {
          // Write each line of the log
          log.split('\n').forEach(line => {
            termRef.current?.writeln(line);
          });
        });
      } else {
        // If no code blocks, display the content directly
        // Remove any markdown formatting
        const cleanContent = message.content
          .replace(/^```\w*\n/, '')
          .replace(/\n```$/, '')
          .replace(/\*\*/g, '');
        
        cleanContent.split('\n').forEach(line => {
          termRef.current?.writeln(line);
        });
      }
      
      // Add spacing between messages
      if (index < terminalMessages.length - 1) {
        termRef.current?.writeln('');
      }
    });

    if (!hasLogs) {
      termRef.current.writeln('\x1b[90mNo execution logs yet...\x1b[0m');
    }
    
    // Scroll to bottom
    termRef.current.scrollToBottom();
  }, [messages]);

  const handleCopy = async () => {
    if (!termRef.current) return;
    
    try {
      // Get all terminal content
      const buffer = termRef.current.buffer.active;
      const lines = [];
      for (let i = 0; i < buffer.length; i++) {
        const line = buffer.getLine(i);
        if (line) {
          lines.push(line.translateToString());
        }
      }
      const content = lines.join('\n');
      
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy terminal content:', err);
    }
  };

  const handleClear = () => {
    if (!termRef.current) return;
    termRef.current.clear();
    termRef.current.writeln('\x1b[36m> Terminal Cleared\x1b[0m');
    termRef.current.writeln('');
  };

  return (
    <div className={`flex flex-col h-full w-full ${className}`}>
      {/* Header with controls */}
      <div className="flex items-center justify-between p-3 border-b bg-background">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            Terminal
          </span>
          <span className="text-sm text-muted-foreground">
            Execution Logs - All Steps
          </span>
        </div>
        <div className="flex items-center gap-2">
          <DSButton
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="flex items-center gap-2"
          >
            <span className="font-mono">[×]</span>
            Clear
          </DSButton>
          <DSButton
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="flex items-center gap-2"
          >
            {copied ? (
              <>
                <span className="font-mono">[✓]</span>
                Copied!
              </>
            ) : (
              <>
                <span className="font-mono">[⧉]</span>
                Copy
              </>
            )}
          </DSButton>
        </div>
      </div>
      
      {/* Terminal container */}
      <div className="flex-1 bg-[#0c0c0c] p-2">
        <div
          ref={terminalRef}
          className="h-full w-full"
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </div>
  );
};

export default forwardRef(Terminal);