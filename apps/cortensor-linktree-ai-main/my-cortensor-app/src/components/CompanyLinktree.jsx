import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  options,
  aboutButtons,
  socialButtons,
  testnetButtons,
  docButtons,
} from "../data/ButtonFunction";
import { staticResponses } from "../data/StaticData";
import AskCortensorAI from "./AskCortensorAI";

export default function CompanyLinktree() {
  const [aboutSelected, setAboutSelected] = useState(false);
  const [socialSelected, setSocialSelected] = useState(false);
  const [testnetSelected, setTestnetSelected] = useState(false);
  const [docSelected, setDocSelected] = useState(false);

  const [selected, setSelected] = useState(null); // sub button yg dipilih
  const [displayedText, setDisplayedText] = useState("");

  const [model, setModel] = useState("Private LLM");
  const [mainMenuDisabled, setMainMenuDisabled] = useState(false);

  // 🔥 flag loading AI biar X disable
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    setMainMenuDisabled(model === "Cortensor");
  }, [model]);

  // efek typing utk staticResponses
  useEffect(() => {
    if (selected && staticResponses[selected]) {
      const fullText = staticResponses[selected].trimStart();
      let index = 0;
      setDisplayedText("");
      const interval = setInterval(() => {
        setDisplayedText(fullText.slice(0, index + 1));
        index++;
        if (index >= fullText.length) clearInterval(interval);
      }, 40);
      return () => clearInterval(interval);
    }
  }, [selected]);

  const handleClick = (topic) => {
    if (mainMenuDisabled) return;
    if (selected) return;

    setAboutSelected(false);
    setSocialSelected(false);
    setTestnetSelected(false);
    setDocSelected(false);

    if (topic === "About $COR") setAboutSelected(true);
    else if (topic === "Social Media") setSocialSelected(true);
    else if (topic === "Testnet") setTestnetSelected(true);
    else if (topic === "Documentation") setDocSelected(true);
  };

  const handleButtonClick = (topic) => {
    if (selected) return;
    setSelected(topic);
  };

  // hide Ask Cortensor AI kalau ada menu aktif
  const isMenuActive =
    aboutSelected || socialSelected || testnetSelected || docSelected || selected;

  const renderSection = (title, buttons) => (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.8, opacity: 0 }}
      transition={{ duration: 0.56 }}
      className="flex flex-col gap-6 w-full"
    >
      <div className="flex items-center justify-between p-4 bg-white shadow rounded-xl font-medium">
        {title}
        <span
          onClick={() => {
            if (!selected && !aiLoading) {
              setAboutSelected(false);
              setSocialSelected(false);
              setTestnetSelected(false);
              setDocSelected(false);
            }
          }}
          className={`font-bold ${
            selected || aiLoading
              ? "opacity-40 cursor-not-allowed text-gray-400"
              : "cursor-pointer text-red-500 hover:text-red-700"
          }`}
        >
          ✕
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 sm:gap-6 bg-white p-4 sm:p-6 rounded-xl shadow">
        {buttons.map((btn) => (
          <button
            key={btn.label}
            onClick={() => handleButtonClick(btn.label)}
            disabled={!!selected}
            className={`flex flex-col items-center justify-center p-3 sm:p-4 shadow rounded-full text-xs sm:text-sm transition ${
              selected
                ? "bg-gray-200 cursor-not-allowed"
                : "bg-white hover:bg-gray-100"
            }`}
          >
            <span className="text-xl sm:text-2xl md:text-3xl">{btn.icon}</span>
            <span className="mt-1 sm:mt-2 text-center">{btn.label}</span>
          </button>
        ))}
      </div>
    </motion.div>
  );

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-start p-4 sm:p-6 overflow-hidden font-['Inter',sans-serif] bg-white">
      {/* 🌊 Background */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <svg
          className="absolute animate-wave opacity-40 blur-xl"
          viewBox="0 0 3600 300"
          preserveAspectRatio="none"
          style={{ height: "100%", width: "400%", top: 0, left: 0 }}
        >
          <defs>
            <linearGradient id="fullWaveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#0000FF" stopOpacity="0.7" />
              <stop offset="50%" stopColor="#FF69B4" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#FFFF00" stopOpacity="0.7" />
            </linearGradient>
          </defs>
          <path
            fill="url(#fullWaveGradient)"
            d="M0,150 C300,100 600,200 900,150 C1200,100 1500,200 1800,150 
             C2100,100 2400,200 2700,150 C3000,100 3300,200 3600,150 L3600,300 L0,300 Z"
          />
        </svg>
      </div>

      {/* Logo */}
      <div className="absolute top-2 sm:top-4 left-2 sm:left-4 z-10">
        <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-black px-2 sm:px-3 py-1">
          <span className="text-blue-600">&lt;/&gt;</span> CORTENSOR
        </h2>
      </div>

      {/* Headline */}
      <div className="text-center z-10 mt-16 sm:mt-20 mb-8 sm:mb-12 px-2">
        <h1 className="text-3xl sm:text-4xl md:text-6xl font-black text-gray-900 whitespace-pre-line">
          Decentralized AI{"\n"}for Everyone
        </h1>
      </div>

      {/* Menu */}
      <div className="flex flex-col md:flex-row justify-center items-start gap-6 sm:gap-8 w-full max-w-5xl mt-12 sm:mt-24 z-10 px-2">
        {!aboutSelected && !socialSelected && !testnetSelected && !docSelected && (
          <motion.div className="w-full md:w-1/2 max-w-xs mx-auto">
            <select
              onChange={(e) => handleClick(e.target.value)}
              value={""}
              disabled={mainMenuDisabled || !!selected}
              className={`appearance-none w-full text-center p-2 sm:p-3 text-sm sm:text-base ${
                mainMenuDisabled || selected
                  ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                  : "bg-white/80 text-gray-800"
              } border border-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-md rounded-md focus:rounded-full`}
            >
              <option value="" disabled>
                Main Menu
              </option>
              {options.map((opt) => (
                <option key={opt.label} value={opt.label}>
                  {opt.icon} {opt.label}
                </option>
              ))}
            </select>
          </motion.div>
        )}

        <AnimatePresence>
          {socialSelected && renderSection("🌐 Social Media", socialButtons)}
        </AnimatePresence>
        <AnimatePresence>
          {aboutSelected && renderSection("💠 About $COR", aboutButtons)}
        </AnimatePresence>
        <AnimatePresence>
          {testnetSelected && renderSection("🧪 Testnet", testnetButtons)}
        </AnimatePresence>
        <AnimatePresence>
          {docSelected && renderSection("📄 Documentation", docButtons)}
        </AnimatePresence>
      </div>

      {/* Popup untuk staticResponses */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 px-4"
          >
            <div className="bg-white w-full max-w-md rounded-2xl shadow-xl p-4 sm:p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-base sm:text-lg font-semibold">{selected}</h2>
                <button
                  onClick={() => setSelected(null)}
                  className="text-lg sm:text-xl font-bold text-purple-600 hover:text-purple-800"
                >
                  ✕
                </button>
              </div>
              <div className="border rounded-xl p-3 sm:p-4 bg-gray-100 whitespace-pre-line min-h-[60px] w-full max-h-[60vh] overflow-y-auto">
                {staticResponses[selected] ? (
                  <span
                    dangerouslySetInnerHTML={{
                      __html: displayedText.replace(
                        /(https?:\/\/[^\s]+)/g,
                        '<a href="$1" target="_blank" class="text-blue-600 underline">$1</a>'
                      ),
                    }}
                  />
                ) : (
                  `Berikan informasi tentang ${selected}`
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ask Cortensor AI */}
      <AskCortensorAI isMenuActive={isMenuActive} setAiLoading={setAiLoading} />

      <style jsx="true">{`
        @keyframes waveSlide {
          0% {
            transform: translateX(0%);
          }
          100% {
            transform: translateX(-25%);
          }
        }
        .animate-wave {
          animation: waveSlide 6s linear infinite;
        }
      `}</style>
    </div>
  );
}
