"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useEffect, useState, useRef } from "react";
import { generalAssistant } from "@/agents/generalAssistant";
import { businessPlanner } from "@/agents/businessPlanner";
import { textSummarizer } from "@/agents/textSummarizer";
import { insightAnalyzer } from "@/agents/insightAnalyzer";
import { formatConverter } from "@/agents/formatConverter";
import { Download, Copy } from "lucide-react";

const agentFunctions = {
  "💬 General Assistant": generalAssistant,
  "💼 Business Planner": businessPlanner,
  "📝 Text Summarizer": textSummarizer,
  "📊 Insight Analyzer": insightAnalyzer,
  "🔄 Format Converter": formatConverter,
};

export default function ChatSection({ loading, activeAgent, sessionId }) {
  const [isAsking, setIsAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); 
  const [flyText, setFlyText] = useState(null);
  const [showFormatOptions, setShowFormatOptions] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (sessionId) {
      fetch(`/api/chat?sessionId=${sessionId}`)
        .then((r) => r.json())
        .then((data) => {
          const filtered = data.filter((m) => m.agent === activeAgent);
          setMessages(
            filtered.map((m) => {
              let text = m.message;
              let metadata = null;

              if (m.role === "ai") {
                try {
                  const parsed = JSON.parse(m.message);
                  if (parsed && typeof parsed === "object" && parsed.content !== undefined) {
                    text = parsed.content;
                    metadata = parsed.metadata; 
                  }
          
                } catch (e) {
                 
                }
              }

              return {
                id: m.id,
                sender: m.role === "ai" ? "ai" : "user",
                text: text, 
                metadata: metadata, 
              };
            })
          );
        })
        .catch(console.error);
    }
  }, [sessionId, activeAgent]);

  useEffect(() => {

    const style = document.createElement("style");
    style.innerHTML = `
      @keyframes wave { 0%,80%,100%{transform:scale(0);opacity:0.3;}40%{transform:scale(1);opacity:1;} }
      .dot { display:inline-block;width:6px;height:6px;margin:0 3px;
        background-color:#2563eb;border-radius:50%;
        animation:wave 1.4s infinite ease-in-out both; }
      .dot:nth-child(1){animation-delay:-0.32s;}
      .dot:nth-child(2){animation-delay:-0.16s;}
      .dot:nth-child(3){animation-delay:0;}
    `;
    document.head.appendChild(style);
    return () => style.remove();
  }, []);


  useEffect(() => {
    if (activeAgent === "🔄 Format Converter") {
      setShowFormatOptions(true);
      setSelectedFormat(null);
      setQuestion(""); 
    } else {
      setShowFormatOptions(false); 
    }
  }, [activeAgent]); 

  const handleDownload = (content, format) => {
    let filename = "converted_data";
    let mimeType = "text/plain";
    let extension = format.toLowerCase();

    if (format === "JSON") {
      filename += ".json";
      mimeType = "application/json";
    } else if (format === "CSV") {
      filename += ".csv";
      mimeType = "text/csv";
    } else if (format === "HTML") {
      filename += ".html";
      mimeType = "text/html";
    } else {
      filename += `.${extension}`;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleFormatSelect = (formatType) => {
    setSelectedFormat(formatType);
    setShowFormatOptions(false);
  };

  const handleChangeChoice = () => {
    setShowFormatOptions(true);
    setSelectedFormat(null);
    setQuestion("");
  };

 
  const handleAskClick = async () => {

    if (
      !question.trim() ||
      isAsking ||
      (activeAgent === "🔄 Format Converter" && !selectedFormat)
    )
      return;

    const inputText = question.trim();
 
    if (activeAgent !== "🔄 Format Converter") setQuestion("");

    setFlyText(inputText);
    setTimeout(() => setFlyText(null), 700);
    setIsAsking(true);

    const thinkingMsgId = Date.now() + 1;


    const agentFunction = agentFunctions[activeAgent];
    if (!agentFunction) {
      console.error("Unknown agent:", activeAgent);
      setIsAsking(false);

      if (activeAgent !== "🔄 Format Converter") {
        setMessages((prev) => [
          ...prev,
          {
            id: thinkingMsgId,
            sender: "ai",
            text: "⚠️ Error: Agent function not found.",
            metadata: null,
          },
        ]);
      }
      return;
    }

 
    let promptForAI = inputText;
    if (activeAgent === "🔄 Format Converter" && selectedFormat) {
      promptForAI = `Please convert this data to format ${selectedFormat}. The data is: ${inputText}`;
    }

  
    const agentMetadata =
      activeAgent === "🔄 Format Converter"
        ? { format: selectedFormat }
        : null;

   
    if (activeAgent !== "🔄 Format Converter") {
      const userMsg = {
        id: Date.now(),
        sender: "user",
        text: inputText,
        metadata: null, 
      };
      setMessages((prev) => [...prev, userMsg]);
    }

    await agentFunction(
      promptForAI,
      sessionId,
      agentMetadata, 
      () => {
        
        const thinkingText =
          activeAgent === "🔄 Format Converter" ? (
            `Convert to ${selectedFormat}, Please wait ...`
          ) : (
            <span className="flex items-center gap-1 text-gray-600">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </span>
          );
      
        setMessages((p) => [
          ...p,
          {
            id: thinkingMsgId,
            sender: "ai",
            text: thinkingText,
            metadata: null,
          },
        ]);
      },
      (aiResponse) => {
        setIsAsking(false); 

        if (activeAgent === "🔄 Format Converter") {
      
          setMessages((p) =>
            p.map((m) =>
              m.id === thinkingMsgId
                ? {
                    ...m,
                    text: aiResponse, 
                    metadata: { format: selectedFormat }, 
                  }
                : m
            )
          );
         
        } else {
          
          let i = 0;
          setMessages((p) =>
            p.map((m) => (m.id === thinkingMsgId ? { ...m, text: "" } : m))
          );
          const interval = setInterval(() => {
            setMessages((p) =>
              p.map((m) =>
                m.id === thinkingMsgId
                  ? { ...m, text: aiResponse.slice(0, i) }
                  : m
              )
            );
            i++;
            if (i > aiResponse.length) clearInterval(interval);
          }, 25);
        }
      }
    );
  };

 
  const transitionVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  }; 

return (
    <div className="relative flex flex-col flex-1 gap-4 h-full">
      
      <AnimatePresence>
        {loading && (
          <motion.div
            key="loading-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 flex flex-colitems-center justify-center bg-white/80 backdrop-blur-sm z-40 rounded-2xl" 
          >
            <span className="flex items-center gap-1 text-gray-600">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </span>
            <p className="mt-2 text-sm font-medium text-gray-600">
            
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {flyText && (
          <motion.div
            key="fly-text"
            initial={{ opacity: 1, y: 0, scale: 1 }}
            animate={{ opacity: 0, y: -150, scale: 0.3 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="absolute bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 bg-pink-500 text-white rounded-lg shadow-xl z-50 text-sm whitespace-pre-wrap"
          >
            {flyText}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeAgent}
          variants={transitionVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          transition={{ duration: 0.5, ease: "easeInOut" }}
          className="flex-1 overflow-hidden"
        >
          <Card className="rounded-2xl shadow-xl bg-white/80 px-1 backdrop-blur-sm h-full">
            <CardContent className="h-full overflow-y-auto pb-1 space-y-4">
              {messages.length === 0 &&
              activeAgent !== "🔄 Format Converter" ? (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center text-gray-500 pt-8"
                >
                  Start chatting with <strong>{activeAgent}</strong>...
                </motion.p>
              ) : (
           
                messages.map((msg) => {
               
                  const isConverterResult =
                    msg.sender === "ai" &&
                    msg.metadata &&
                    msg.metadata.format;

                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                      className={`flex flex-col ${
                        msg.sender === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      {isConverterResult ? (
                 
                        <div className="flex flex-col items-start gap-3 p-3 bg-gray-100 rounded-lg border border-gray-200 shadow-sm w-full max-w-md">
                          <span className="font-semibold text-gray-800 text-sm">
                            ☑️ Convert to {msg.metadata.format} Complete!
                          </span>
                          <Button
                            onClick={() =>
                              handleDownload(msg.text, msg.metadata.format)
                            }
                            size="sm"
                            className="w-full bg-gradient-to-r from-pink-500 to-pink-400 hover:scale-[1.03] hover:shadow-md"
                          >
                            <Download className="w-4 h-4 mr-1.5" /> Download
                            Converted Result File
                          </Button>
                          <div className="w-full mt-2">
                            <p className="text-xs font-medium text-gray-600 mb-1">
                              Preview:
                            </p>
                            <pre className="bg-white border border-gray-300 rounded p-2 text-xs max-h-40 overflow-auto whitespace-pre-wrap break-words">
                              {msg.text}
                            </pre>
                          </div>
                        </div>
                      ) : (
                     
                        <div
  className={`max-w-[75%] px-4 py-2 rounded-2xl shadow whitespace-pre-line text-sm ${ 
    msg.sender === "user"
      ? "text-white rounded-br-none bg-gradient-to-r from-blue-500 to-blue-400"
      : "bg-white-100 text-gray-800 rounded-bl-none"
  }`}
>
                          {msg.text}
                        </div>
                      )}
                    </motion.div>
                  );
                })
              )}
              <div ref={chatEndRef}></div>
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      <AnimatePresence>
        {showFormatOptions && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 flex items-center justify-center bg-white/30 backdrop-blur-sm z-50"
          >
            <div className="bg-white rounded-2xl shadow-xl p-6 pt-5 text-center space-y-4 w-[320px] border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                Select Conversion Format:
              </h3>
              <div className="grid grid-cols-1 gap-3">
                <Button
                  onClick={() => handleFormatSelect("JSON")}
                  size="lg"
                  className="bg-gradient-to-r from-pink-500 to-pink-400 hover:scale-[1.03] hover:shadow-md"
                >
                  Convert to JSON
                </Button>
                <Button
                  onClick={() => handleFormatSelect("HTML")}
                  size="lg"
                  className="bg-gradient-to-r from-pink-500 to-pink-400 hover:scale-[1.03] hover:shadow-md"
                >
                  Convert to HTML
                </Button>
                <Button
                  onClick={() => handleFormatSelect("CSV")}
                  size="lg"
                  className="bg-gradient-to-r from-pink-500 to-pink-400 hover:scale-[1.03] hover:shadow-md"
                >
                  Convert to CSV
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col gap-2 mt-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder={
              activeAgent === "🔄 Format Converter"
                ? selectedFormat
                  ? `Paste the text data for ${selectedFormat}...`
                  : "Select the format above..."
                : "Ask something..."
            }
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAskClick()}
           
            disabled={
              isAsking ||
              (activeAgent === "🔄 Format Converter" && !selectedFormat)
            }
            className="flex-1 p-3 rounded-xl border border-gray-300 shadow-sm text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <Button
            onClick={handleAskClick}
            disabled={
              isAsking ||
              (activeAgent === "🔄 Format Converter" && !selectedFormat)
            } 
            className={`px-6 py-2 h-11 rounded-xl font-semibold text-white transition-all duration-200 ${
              isAsking ||
              (activeAgent === "🔄 Format Converter" && !selectedFormat)
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-gradient-to-r from-pink-500 to-pink-400 hover:scale-[1.03] hover:shadow-md"
            }`}
          >
            {isAsking ? "Processing..." : "Ask"}
          </Button>
        </div>

        {activeAgent === "🔄 Format Converter" &&
          selectedFormat &&
          !isAsking && (
            <button
              onClick={handleChangeChoice}
              className="text-sm text-blue-600 hover:underline self-start ml-2 mt-1 px-1"
            >
              Change Format (Now: {selectedFormat})
            </button>
          )}
      </div>
    </div>
  );
}