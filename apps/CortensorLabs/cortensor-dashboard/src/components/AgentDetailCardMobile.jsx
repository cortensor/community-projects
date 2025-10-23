"use client";
import { useState } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { Info, X } from 'lucide-react'; 

export default function AgentDetailCardMobile({ activeAgent, activeDetail }) {
  const [isOpen, setIsOpen] = useState(false); 
  const popupVariants = {
    hidden: { opacity: 0, scale: 0.9, y: -50 }, 
    visible: { opacity: 1, scale: 1, y: 0 },
  };

  return (
    <>
      {!isOpen && (
        <motion.button
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          onClick={() => setIsOpen(true)}
          className="fixed center-6 right-6 z-40 p-3 bg-blue-600 text-white rounded-full shadow-lg"
        >
          <Info size={24} /> 
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
              className="fixed center-6 right-6 z-50 p-4 bg-white rounded-2xl shadow-lg w-[calc(100vw-3rem)] max-w-sm"
            >
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-lg text-gray-800">Agentic AI Guide :</h3>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-1 rounded-full hover:bg-gray-100"
                >
                  <X size={20} className="text-gray-500" />
                </button>
              </div>

              <div className="flex flex-col gap-2 max-h-[70vh] overflow-y-auto pr-2 scrollbar-thin">
                <h3 className="font-semibold text-gray-800">{activeDetail.title}</h3>
                <p className="text-sm text-gray-600">{activeDetail.desc}</p>
                <p className="text-sm text-gray-600 font-medium">Use it for:</p>
                <p className="text-sm text-gray-600">{activeDetail.use}</p>
                <p className="text-sm italic text-gray-500">Example prompts:</p>
                <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                  {activeDetail.examples.map((ex, idx) => (
                    <li key={idx}>“{ex}”</li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}