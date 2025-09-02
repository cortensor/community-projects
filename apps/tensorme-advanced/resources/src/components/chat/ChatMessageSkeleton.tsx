"use client";
import React from 'react';

const ChatMessageSkeleton: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="max-w-xs md:max-w-md lg:max-w-xl xl:max-w-3xl px-5 py-4 rounded-2xl rounded-bl-none bg-black/20 backdrop-blur-md border border-white/10 animate-pulse">
        <div className="space-y-3">
          <div className="h-2.5 bg-white/10 rounded-full w-48"></div>
          <div className="h-2.5 bg-white/10 rounded-full w-64"></div>
          <div className="h-2.5 bg-white/10 rounded-full w-40"></div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessageSkeleton;