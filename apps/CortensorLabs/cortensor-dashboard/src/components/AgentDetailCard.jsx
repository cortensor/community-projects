"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Minus, Square } from "lucide-react"; 
import useWindowWidth from "@/hooks/useWindowWidth"; 
import AgentDetailCardMobile from "./AgentDetailCardMobile";

function AgentDetailCardDesktop({ activeAgent, activeDetail }) {
  const [isMinimized, setIsMinimized] = useState(false);

  return (
    <Card
      className={`rounded-2xl shadow-md bg-white/80 p-5 backdrop-blur-sm overflow-hidden transition-all duration-300 ${
        isMinimized ? "w-24" : "w-70" 
      }`}
      style={{ 
        height: isMinimized ? "auto" : "calc(100% - 50px)", 
        padding: isMinimized ? "0.5rem" : "1.25rem" 
      }} 
    >
      <div className="flex justify-between items-center border-b pb-2 mb-2">
        {!isMinimized && (
          <h2 className="font-semibold text-lg text-gray-800">
            Agentic AI Guide :
          </h2>
        )}
        
        <div className={`flex space-x-2 ${isMinimized ? "w-full justify-center" : ""}`}>
          <button 
            onClick={() => setIsMinimized(true)}
            className={`p-1 rounded hover:bg-gray-200 ${!isMinimized ? "" : "hidden"}`} 
          >
            <Minus size={16} />
          </button>
          <button 
            onClick={() => setIsMinimized(false)}
            className={`p-1 rounded hover:bg-gray-200 ${isMinimized ? "" : "hidden"}`} 
          >
            <Square size={16} />
          </button>
        </div>
      </div>
      
      {!isMinimized && (
        <div className="p-0 px-1 flex-1 max-h-full text-gray-700 space-y-4 scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeAgent}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4 }}
              className="space-y-3"
            >
              <h3 className="font-semibold text-gray-800">{activeDetail.title}</h3>
              <p className="text-sm text-gray-600">{activeDetail.desc}</p>
              <p className="text-sm text-gray-600 font-medium">Use it for:</p>
              <p className="text-sm text-gray-600">{activeDetail.use}</p>
              <p className="text-sm italic text-gray-500">Example prompts:</p>
              <ul className="text-sm text-gray-600 list-disc list-inside">
                {activeDetail.examples.map((ex, idx) => (
                  <li key={idx}>“{ex}”</li>
                ))}
              </ul>
            </motion.div>
          </AnimatePresence>
        </div>
      )}
    </Card>
  );
}

export default function AgentDetailCard(props) {
  const width = useWindowWidth();
  const isMobile = width < 1024; 

  if (isMobile) {
    return <AgentDetailCardMobile {...props} />;
  }
  return <AgentDetailCardDesktop {...props} />;
}