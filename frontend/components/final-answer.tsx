"use client";

import { CheckCircle2 } from "lucide-react";
import Markdown from "@/components/markdown";

interface FinalAnswerProps {
  content: string;
}

export default function FinalAnswer({ content }: FinalAnswerProps) {
  return (
    <div className="w-full bg-green-500/10 border-2 border-green-500/30 rounded-lg p-6 mt-4">
      <div className="flex items-center gap-3 mb-4">
        <CheckCircle2 className="h-6 w-6 text-green-500" />
        <h3 className="text-lg font-semibold text-green-500">Final Answer</h3>
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <Markdown>{content}</Markdown>
      </div>
    </div>
  );
}