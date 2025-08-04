// Temporary dropdown menu component to fix build errors
// TODO: Replace with DS components

import React from 'react';

export const DropdownMenu: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div className="relative">{children}</div>;
};

export const DropdownMenuTrigger: React.FC<{ children: React.ReactNode; asChild?: boolean }> = ({ children }) => {
  return <>{children}</>;
};

export const DropdownMenuContent: React.FC<{ children: React.ReactNode; className?: string; align?: string }> = ({ children, className = '' }) => {
  return <div className={`absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 ${className}`}>{children}</div>;
};

export const DropdownMenuItem: React.FC<{ children: React.ReactNode; onClick?: () => void; className?: string; disabled?: boolean }> = ({ children, onClick, className = '', disabled = false }) => {
  return (
    <div 
      className={`block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer ${className} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      onClick={disabled ? undefined : onClick}
    >
      {children}
    </div>
  );
};