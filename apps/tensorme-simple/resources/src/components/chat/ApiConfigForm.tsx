"use client";
import React from 'react';
import { Settings2, Server } from 'lucide-react';

interface ApiConfigFormProps {
  cortensorApiUrl: string;
  onApiUrlChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const ApiConfigForm: React.FC<ApiConfigFormProps> = ({ cortensorApiUrl, onApiUrlChange }) => {
  return (
    <div className="p-3 bg-neutral-900 border-b border-neutral-800">
      <label htmlFor="apiUrl" className="block text-xs font-medium text-gray-400 mb-1 flex items-center">
        <Settings2 size={14} className="mr-1.5 text-gray-500" /> Cortensor Router API:
      </label>
      <div className="flex">
        <input
          type="text"
          id="apiUrl"
          name="apiUrl"
          value={cortensorApiUrl}
          onChange={onApiUrlChange}
          placeholder="e.g., http://192.168.1.100:8080/api/v1/chat"
          className="flex-grow p-2 bg-neutral-800 border border-neutral-700 rounded-l-md focus:ring-1 focus:ring-yellow-500 focus:border-yellow-500 text-gray-200 placeholder-neutral-500 text-xs"
        />
        <span className="inline-flex items-center px-2.5 rounded-r-md border border-l-0 border-neutral-700 bg-neutral-700 text-gray-400 text-xs">
          <Server size={14} />
        </span>
      </div>
      {/* Optionally add Model selection here in the future */}
    </div>
  );
};

export default ApiConfigForm;