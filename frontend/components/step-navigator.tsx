// Step navigation component for navigating between agent execution steps
import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface StepNavigatorProps {
  currentStep: number;
  maxStep: number;
  onStepChange: (step: number) => void;
}

export function StepNavigator({ currentStep, maxStep, onStepChange }: StepNavigatorProps) {
  const canGoPrevious = currentStep > 0;
  const canGoNext = currentStep < maxStep;

  return (
    <div className="flex items-center justify-between p-3 border-t bg-background">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onStepChange(currentStep - 1)}
        disabled={!canGoPrevious}
        className="flex items-center gap-1"
      >
        <ChevronLeft className="h-4 w-4" />
        Previous
      </Button>
      
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Step</span>
        <select
          value={currentStep}
          onChange={(e) => onStepChange(Number(e.target.value))}
          className="text-sm border rounded px-2 py-1 bg-background"
        >
          {Array.from({ length: maxStep + 1 }, (_, i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>
        <span className="text-sm text-muted-foreground">of {maxStep}</span>
      </div>
      
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onStepChange(currentStep + 1)}
        disabled={!canGoNext}
        className="flex items-center gap-1"
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}