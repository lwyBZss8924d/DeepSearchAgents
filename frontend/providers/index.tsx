"use client";

import { AppProgressBar as ProgressBar } from "next-nprogress-bar";
import "../app/github-markdown.css";
import { ThemeProvider } from "@/components/theme-provider-v2";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      defaultTheme="classic"
    >
      <ProgressBar
        height="2px"
        color="#BAE9F4"
        options={{ showSpinner: false }}
        shallowRouting
      />
      {children}
    </ThemeProvider>
  );
}
