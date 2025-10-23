"use client";
import { motion } from "framer-motion";

export default function LoadingScreen() {
  const letters = "CORTENSOR".split("");

  return (
    <motion.div
      key="initial-loading"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 flex flex-col items-center justify-center bg-white z-50"
    >
      <motion.p
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8 }}
        className="mb-6 text-blue-600 text-sm font-medium tracking-wide"
      >
        Launching ...
      </motion.p>
      <div className="flex space-x-2">
        {letters.map((letter, i) => (
          <motion.span
            key={i}
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.3 }}
            className="text-4xl font-extrabold text-blue-700 tracking-widest"
          >
            {letter}
          </motion.span>
        ))}
      </div>
    </motion.div>
  );
}
