"use client";
import { useState, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import { agents, agentDetails } from "@/data/agentData";
import LoadingScreen from "@/components/LoadingScreen";
import PopupSession from "@/components/PopupSession";
import AgentSidebar from "@/components/AgentSidebar";
import AgentDetailCard from "@/components/AgentDetailCard";
import ChatSection from "@/components/ChatSection";
import { Copy, Check } from "lucide-react";

export default function Page() {
  const [initialLoading, setInitialLoading] = useState(true);
  const [showPopup, setShowPopup] = useState(true);
  const [popupLoading, setPopupLoading] = useState(false);
  const [restoreInput, setRestoreInput] = useState("");
  const [showRestoreInput, setShowRestoreInput] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeAgent, setActiveAgent] = useState(agents[0]);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setInitialLoading(false), 5000);
    return () => clearTimeout(timer);
  }, []);

  const generateSession = () => {
    setPopupLoading(true);
    setTimeout(() => {
      const id = Math.random().toString(36).substr(2, 9).toUpperCase();
      setSessionId(id);
      setPopupLoading(false);
      setShowPopup(false);
    }, 1500);
  };

  const restoreSession = () => {
    if (restoreInput.trim() === "") {
      setShowRestoreInput(true);
      return;
    }
    setPopupLoading(true);
    setTimeout(() => {
      setSessionId(restoreInput.trim().toUpperCase());
      setPopupLoading(false);
      setShowPopup(false);
      setShowRestoreInput(false);
    }, 1500);
  };

  const handleAgentClick = (agent) => {
    if (activeAgent === agent) return;
    setLoading(true);
    setTimeout(() => {
      setActiveAgent(agent);
      setLoading(false);
    }, 1000);
  };

  const handleCopy = () => {
    if (sessionId) {
      navigator.clipboard.writeText(sessionId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const activeDetail = agentDetails[activeAgent];

  return (
    <main className="flex flex-col h-screen text-gray-800 relative overflow-hidden bg-white">
      <AnimatePresence>{initialLoading && <LoadingScreen />}</AnimatePresence>

      {!initialLoading && (
        <>
          <AnimatePresence>
            {popupLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-md z-50">
                <div className="flex flex-col items-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-blue-500"></div>
                  <p className="mt-4 text-gray-700 font-medium">Loading ...</p>
                </div>
              </div>
            )}
          </AnimatePresence>

          {showPopup && !popupLoading ? (
            <PopupSession
              showRestoreInput={showRestoreInput}
              restoreInput={restoreInput}
              setRestoreInput={setRestoreInput}
              generateSession={generateSession}
              restoreSession={restoreSession}
              setShowRestoreInput={setShowRestoreInput}
            />
          ) : (
            <>
              <div className="flex justify-center pb-1 mt-6 mb-5 px-6">
                <header className="w-[94%] bg-white/90 backdrop-blur-sm border border-gray-100 rounded-2xl shadow-[5px_8px_30px_rgba(236,72,153,0.35)] px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-0 transition-all duration-300 hover:shadow-[0_12px_35px_rgba(0,0,0,0.18)]">
                  <div className="flex items-center space-x-2 select-none">
                    <div className="text-2xl font-extrabold text-blue-600 tracking-tighter">
                      &lt;/&gt;
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 tracking-wide">
                      CORTENSOR
                    </h1>
                  </div>

                  {sessionId && (
                    <div className="flex items-center space-x-2 text-sm text-gray-600">
                      <p>
                        Session ID: <strong>{sessionId}</strong>
                      </p>
                      <button
                        onClick={handleCopy}
                        className="p-1 rounded-md hover:bg-gray-100 transition-all"
                        title="Copy Session ID"
                      >
                        {copied ? (
                          <Check className="w-4 h-4 text-green-500" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-500" />
                        )}
                      </button>
                    </div>
                  )}
                </header>
              </div>

               <div className="flex flex-1 overflow-hidden bg-white px-4 pb-4 gap-4">
                <AgentSidebar
                  agents={agents}
                  activeAgent={activeAgent}
                   handleAgentClick={handleAgentClick}
                />

                <ChatSection
                   key={sessionId} 
                   loading={loading}
                   activeAgent={activeAgent}
                   sessionId={sessionId} 
                />
                <AgentDetailCard
                   activeAgent={activeAgent}
                   activeDetail={activeDetail}
                />
              </div>

              <footer className="p-3 text-center text-sm text-gray-500 bg-white border-t shadow-[5px_-6px_25px_rgba(59,130,246,0.35)] z-30">
                Build by{" "}
                <a
                  href="https://x.com/Ajipur26"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-blue-700 hover:underline"
                >
                  PapaCZ
                </a>
              </footer>
            </>
          )}
        </>
      )}
    </main>
  );
}
