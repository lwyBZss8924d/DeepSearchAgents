"use client";

import React, { useState, useRef } from 'react';
import { Search, Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface SearchInputProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  suggestions?: string[];
  className?: string;
}

export function SearchInput({
  onSearch,
  isLoading = false,
  placeholder = "Ask DeepSearchAgent anything...",
  suggestions = [],
  className
}: SearchInputProps) {
  const [query, setQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
      setQuery('');
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const filteredSuggestions = suggestions.filter(s => 
    s.toLowerCase().includes(query.toLowerCase()) && s !== query
  );

  return (
    <div className={cn("relative w-full", className)}>
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowSuggestions(e.target.value.length > 0);
            }}
            onFocus={() => setShowSuggestions(query.length > 0)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder={placeholder}
            className="pl-10 pr-12 h-12 text-base"
            disabled={isLoading}
          />
          <Button
            type="submit"
            size="sm"
            disabled={!query.trim() || isLoading}
            className="absolute right-2 h-8 w-8 p-0"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </form>

      {showSuggestions && filteredSuggestions.length > 0 && (
        <Card className="absolute top-full left-0 right-0 mt-1 p-2 z-50 max-h-48 overflow-y-auto">
          {filteredSuggestions.map((suggestion, index) => (
            <div
              key={index}
              className="px-3 py-2 text-sm cursor-pointer hover:bg-accent rounded-md transition-colors"
              onClick={() => handleSuggestionClick(suggestion)}
            >
              {suggestion}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

