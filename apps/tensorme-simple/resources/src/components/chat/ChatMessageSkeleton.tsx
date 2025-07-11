"use client";
import React from 'react';

const ChatMessageSkeleton: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="max-w-xs md:max-w-md lg:max-w-xl xl:max-w-3xl px-4 py-2.5 rounded-xl rounded-bl-none bg-neutral-800 animate-pulse">
        <div className="space-y-2">
          <div className="h-2.5 bg-neutral-700 rounded-full w-48"></div>
          <div className="h-2.5 bg-neutral-700 rounded-full w-64"></div>
          <div className="h-2.5 bg-neutral-700 rounded-full w-40"></div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessageSkeleton;