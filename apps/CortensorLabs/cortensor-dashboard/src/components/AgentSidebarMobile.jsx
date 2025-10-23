"use client";
import { useState } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { LayoutGrid, X } from 'lucide-react'; 

export default function AgentSidebarMobile({ agents, activeAgent, handleAgentClick }) {
  const [isOpen, setIsOpen] = useState(false);
  const popupVariants = {
    hidden: { opacity: 0, scale: 0.9, y: 50 },
    visible: { opacity: 1, scale: 1, y: 0 },
  };

  const onAgentClick = (agent) => {
    handleAgentClick(agent); 
    setIsOpen(false);        
  };

  return (
    <>
      {!isOpen && (
        <motion.button
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          onClick={() => setIsOpen(true)}
          className="fixed center-6 left-6 z-40 p-3 bg-blue-600 text-white rounded-full shadow-lg"
        >
          <LayoutGrid size={24} />
        </motion.button>
      )}

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)} 
              className="fixed inset-0 bg-black/50 z-50"
            />

            <motion.div
              variants={popupVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="fixed center-6 left-6 z-50 p-4 bg-white rounded-2xl shadow-lg w-[calc(100vw-3rem)] max-w-sm"
            >
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-lg text-gray-800">Pilih Agent</h3>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-1 rounded-full hover:bg-gray-100"
                >
                  <X size={20} className="text-gray-500" />
                </button>
              </div>

              <div className="flex flex-col gap-2">
                {agents.map((agent) => {
                  const isActive = activeAgent === agent;
                  return (
                    <Button
                      key={agent}
                      onClick={() => onAgentClick(agent)}
                      className={`w-full rounded-lg border font-medium transition-all duration-300 ${
                        isActive
                          ? "bg-gray-200 text-gray-900 border-gray-400"
                          : "bg-white text-gray-800 border-gray-200 hover:bg-gray-50"
                      }`}
                      variant="ghost"
                    >
                      {agent}
                    </Button>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}