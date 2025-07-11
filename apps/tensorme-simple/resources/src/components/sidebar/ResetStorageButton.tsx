"use client";
import React from 'react';
import { Trash2 } from 'lucide-react';

const ResetStorageButton = () => {
  const handleReset = () => {
    const isConfirmed = window.confirm(
      'Are you sure you want to reset all application data? This action will clear your chat history and settings and cannot be undone.'
    );

    if (isConfirmed) {
      // Clear all items from localStorage
      localStorage.clear();
      // Reload the page to apply the changes and re-initialize the state
      window.location.reload();
    }
  };

  return (
    <div className="mt-4">
      <button
        onClick={handleReset}
        className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-red-400 border border-red-400/50 rounded-lg hover:bg-red-400/10 hover:text-red-300 transition-colors duration-150"
        title="Reset All Application Data"
      >
        <Trash2 size={16} className="mr-2" />
        Reset All Data
      </button>
    </div>
  );
};

export default ResetStorageButton;