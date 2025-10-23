"use client";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { useEffect } from "react";

export default function PopupSession({
  showRestoreInput,
  restoreInput,
  setRestoreInput,
  generateSession,
  restoreSession,
  setShowRestoreInput
}) {
  useEffect(() => {
    const style = document.createElement("style");
    style.innerHTML = `
      @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }

      .btn-gradient {
        background: linear-gradient(270deg, #1e3a8a, #2563eb, #3b82f6, #60a5fa);
        background-size: 250% 250%;
        animation: gradientShift 5s ease-in-out infinite;
        color: white;
        transition: all 0.4s ease;
        box-shadow: 0 3px 8px rgba(37, 99, 235, 0.25);
      }

      .btn-gradient:hover {
        background: linear-gradient(
          270deg,
          #e5e7eb,
          #d1d5db,
          #f9fafb,
          #9ca3af,
          #e5e7eb
        );
        background-size: 300% 300%;
        animation: gradientShift 3.5s ease-in-out infinite;
        color: #1f2937;
        transform: scale(1.04);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
      }

      .btn-gradient:active {
        transform: scale(0.97);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
      }
    `;
    document.head.appendChild(style);
    return () => style.remove();
  }, []);

  return (
    <div className="absolute inset-0 bg-white/80 backdrop-blur-md flex flex-col items-center justify-center text-center p-8 z-40">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/70 rounded-2xl p-8 shadow-lg max-w-md"
      >
        <h2 className="text-2xl font-semibold mb-4 text-gray-800">
          Welcome to Cortensor
        </h2>

        <p className="text-sm text-gray-700 mb-4">
          If you are a new user, please select{" "}
          <strong>“Generate Session.”</strong>
          <br />
          If you already have an ID, please select{" "}
          <strong>“Restore Session.”</strong>
          <br />
          <br />
          Don’t forget to save your Session ID to restore previous
          conversations.
        </p>

        <div className="flex flex-col gap-3">
          <Button
            onClick={generateSession}
            className="btn-gradient text-base font-semibold rounded-lg"
          >
            Generate Session
          </Button>

          <Button
            onClick={() => setShowRestoreInput(true)}
            className="btn-gradient text-base font-semibold rounded-lg"
          >
            Restore Session
          </Button>
        </div>

        {showRestoreInput && (
          <div className="mt-4">
            <input
              type="text"
              placeholder="Enter your Session ID..."
              value={restoreInput}
              onChange={(e) => setRestoreInput(e.target.value)}
              className="p-2 border rounded-md w-full text-center mt-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            <Button
              onClick={restoreSession}
              className="btn-gradient mt-3 text-base font-semibold rounded-lg"
            >
              Confirm Restore
            </Button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
