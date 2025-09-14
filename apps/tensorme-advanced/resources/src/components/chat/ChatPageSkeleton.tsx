"use client";
import React from 'react';

const ChatPageSkeleton: React.FC = () => {
  return (
    <div className="flex h-screen bg-neutral-950 text-gray-200 font-sans antialiased">
      {/* Sidebar Skeleton */}
      <aside className="bg-neutral-900 flex flex-col w-64 md:w-72 border-r border-neutral-800 animate-pulse">
        <div className="p-4 flex items-center justify-between h-16 border-b border-neutral-800">
          <div className="h-4 bg-neutral-700 rounded w-3/4"></div>
        </div>
        <div className="p-2">
          <div className="h-10 bg-neutral-700 rounded-md"></div>
        </div>
        <nav className="flex-grow p-2 space-y-2">
          <div className="h-8 bg-neutral-700 rounded-md"></div>
          <div className="h-8 bg-neutral-700 rounded-md"></div>
          <div className="h-8 bg-neutral-700 rounded-md"></div>
        </nav>
        <div className="p-4 border-t border-neutral-800">
          <div className="h-2 bg-neutral-700 rounded w-1/2"></div>
        </div>
      </aside>

      {/* Main Content Skeleton */}
      <div className="flex-1 flex flex-col bg-neutral-950">
        <header className="bg-neutral-900 h-16 shadow-sm flex items-center justify-between px-4 border-b border-neutral-800">
          <div className="h-4 bg-neutral-700 rounded w-1/4"></div>
        </header>
        <main className="flex-grow p-4 sm:p-6 overflow-y-auto space-y-4">
          <div className="flex justify-end">
            <div className="max-w-xs md:max-w-md lg:max-w-xl xl:max-w-3xl">
              <div className="h-12 bg-slate-700 rounded-xl rounded-br-none animate-pulse"></div>
            </div>
          </div>
          <div className="flex justify-start">
            <div className="max-w-xs md:max-w-md lg:max-w-xl xl:max-w-3xl">
              <div className="h-16 bg-neutral-800 rounded-xl rounded-bl-none animate-pulse"></div>
            </div>
          </div>
        </main>
        <footer className="p-3 bg-neutral-900 border-t border-neutral-800">
          <div className="h-12 bg-neutral-800 rounded-lg animate-pulse"></div>
        </footer>
      </div>
    </div>
  );
};

export default ChatPageSkeleton;