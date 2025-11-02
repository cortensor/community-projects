import React, { useEffect, useState, useRef, useCallback } from "react";
import "simplebar-react/dist/simplebar.min.css";
import { useLocation } from "react-router-dom";
import Navbar from "../components/ui/Navbar";
import ChatInterface from "../components/ChatInterface";
import { Layers } from "lucide-react";
import { startChaplinStream } from "../services/apiService";
import { mockState } from '../_mockData';
const USE_MOCK_DATA = false;


function getClientSessionId() {
  let id = localStorage.getItem("clientSessionId");
  if (!id) {
    id = `cs_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    try { localStorage.setItem("clientSessionId", id); } catch (e) { }
  }
  return id;
}
async function generateImageFromPrompt(imagePrompt) {
  const workerUrl = import.meta.env.VITE_IMAGE_WORKER_URL;
  if (!workerUrl) { console.error("VITE_IMAGE_WORKER_URL não está definido no .env"); return null; }
  const url = `${workerUrl}/?prompt=${encodeURIComponent(imagePrompt)}`;
  try {
    const response = await fetch(url);
    if (!response.ok) { throw new Error(`Image generation failed with status: ${response.status}`); }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error) { console.error("Failed to generate image:", error); return null; }
}

function App() {
  const location = useLocation();
  const [isNavbarOpen, setIsNavbarOpen] = useState(true);
  const [userInput, setUserInput] = useState('');
  const [originalInput, setOriginalInput] = useState(USE_MOCK_DATA ? mockState.originalInput : '');
  const [isProcessing, setIsProcessing] = useState(USE_MOCK_DATA ? mockState.isProcessing : false);
  
  const [displayResult, setDisplayResult] = useState(USE_MOCK_DATA ? mockState.finalResult : null);
  const [displayImageUrl, setDisplayImageUrl] = useState(USE_MOCK_DATA ? mockState.generatedImageUrl : null);
  const [displayOriginalInput, setDisplayOriginalInput] = useState(USE_MOCK_DATA ? mockState.originalInput : '');

  const [progressSteps, setProgressSteps] = useState([]);
  const streamControllerRef = useRef(null);
  const imageGenerationTriggeredRef = useRef(false);
  const jobIdRef = useRef(null);
  const pausedDueToHiddenRef = useRef(false);

  // Substitua a definição atual de startStream por esta versão:
const startStream = useCallback((jobId = null, currentRequestInput) => {
  if (streamControllerRef.current) {
    streamControllerRef.current.abort();
  }
  if (!currentRequestInput) {
    console.error("startStream foi chamada sem um input válido!");
    setIsProcessing(false);
    return;
  }
  const payload = {
    chaplin_id: "-OcwWkaAeD-aE1Aj3Wij",
    input: currentRequestInput,
    clientSessionId: getClientSessionId(),
    jobId: jobId,
  };


  streamControllerRef.current = startChaplinStream(payload, {
    onData: (chunk) => {
      if (chunk.type === "start" && chunk.jobId && !jobIdRef.current) {
        jobIdRef.current = chunk.jobId;
      }

      if (chunk.type === 'integrator_result') {
        if (imageGenerationTriggeredRef.current) return;
        imageGenerationTriggeredRef.current = true;

        setProgressSteps(prevSteps => [
          ...prevSteps.map(step =>
            step.type === 'integrator'
              ? { ...step, status: 'processing', content: 'output formatter is working...' }
              : step
          ),
          { id: prevSteps.length + 1, name: "Generate Image", status: "processing", type: "image", content: "building image..." }
        ]);
        setTimeout(() => {
          setProgressSteps(currentSteps => currentSteps.map(step =>
            step.type === 'integrator'
              ? { ...step, status: 'completed', content: chunk.data.final }
              : step
          ));
        }, 500);

        generateImageFromPrompt(chunk.data.final.image_prompt).then(
          (imageUrl) => {
            if (imageUrl) {
              setDisplayResult(chunk.data.final);
              setDisplayImageUrl(imageUrl);
              setDisplayOriginalInput(currentRequestInput);

              setProgressSteps(currentSteps => currentSteps.map(step =>
                step.type === 'image' ? { ...step, status: 'completed', content: 'Image generated successfully.' } : step
              ));
            } else {
              // erro na geração da imagem — interrompe o estado de processamento
              setIsProcessing(false);
              setProgressSteps(currentSteps => currentSteps.map(step =>
                step.type === 'image' ? { ...step, status: 'error', content: 'Failed to generate image.' } : step
              ));
            }
            jobIdRef.current = null;
            // NOTA: não setIsProcessing(false) aqui — deixamos o useEffect([displayImageUrl]) cuidar disso
          }
        );
        return;
      }

      // resto do onData (atualiza progressSteps)
      setProgressSteps((prevSteps) => {
        let newSteps = [...prevSteps];
        if ((chunk.type === "agent_start" || chunk.type === "start") && newSteps.length > 0 && newSteps[0].type === "connection" && newSteps[0].status === "processing") {
          newSteps[0].status = "completed";
          newSteps[0].content = "Connection established.";
        }
        switch (chunk.type) {
          case "agent_start":
            if (!newSteps.some((step) => step.name === chunk.data.name)) {
              newSteps.push({ id: prevSteps.length + 1, name: chunk.data.name, status: "processing", type: "agent", content: "requesting to cortensor..." });
            }
            break;
          case "agent_attempt": {
            const agentIndex = newSteps.findIndex((step) => step.name === chunk.data.name);
            if (agentIndex > -1) { newSteps[agentIndex].content = `waiting for cortensor ${chunk.data.attempt} of ${chunk.data.maxAttempts}`; }
            break;
          }
          case "agent_result": {
            const agentIndex = newSteps.findIndex((step) => step.name === chunk.data.name);
            if (agentIndex > -1) { newSteps[agentIndex].status = "generated"; newSteps[agentIndex].content = chunk.data.output; }
            break;
          }
          case "integrator_start":
            if (!newSteps.some((step) => step.type === "integrator")) {
              newSteps.push({ id: prevSteps.length + 1, name: "Output", status: "processing", type: "integrator", content: "requesting to output formatter..." });
            }
            break;
        }
        return newSteps;
      });
    },
    onError: (err) => {
      console.error("Stream error:", err);
      setIsProcessing(false);
      setProgressSteps((prev) => [...prev, { id: prev.length + 1, name: "Error", status: "error", type: "error", content: err.message }]);
    },
    onClose: () => {

      if (!imageGenerationTriggeredRef.current && !jobIdRef.current) {
        setIsProcessing(false);
      }
    },
  });

}, []); 


  const handleSendMessage = () => {
    const currentInput = userInput.trim();
    if (!currentInput || isProcessing) return;

    setOriginalInput(currentInput);
    setIsProcessing(true);
    

    
    setProgressSteps([
      { id: 1, name: "Connect to Chaplin", status: "processing", type: "connection", content: "Connecting..." },
    ]);
    imageGenerationTriggeredRef.current = false;
    jobIdRef.current = null;

    startStream(null, currentInput);
  };

  useEffect(() => {

    if (displayImageUrl) {

      setIsProcessing(false);
      setUserInput("");
    }
  }, [displayImageUrl]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (streamControllerRef.current) {
          pausedDueToHiddenRef.current = true;
          streamControllerRef.current.abort();
          streamControllerRef.current = null;
        }
      } else {
        if (pausedDueToHiddenRef.current && jobIdRef.current) {
          startStream(jobIdRef.current, originalInput);
        }
        pausedDueToHiddenRef.current = false;
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [originalInput, startStream]);

  useEffect(() => {
    const isDesktop = window.innerWidth >= 1024;
    setIsNavbarOpen(isDesktop);
  }, []);

  return (
    <div className="bg-[#18181B] min-h-screen font-inter text-white flex">
      <Navbar
        isOpen={isNavbarOpen}
        setIsOpen={setIsNavbarOpen}
        progressSteps={progressSteps}
      />
      <button
        onClick={() => setIsNavbarOpen(true)}
        className={`fixed top-5 left-2 z-20 p-2 rounded-full cursor-pointer hover:bg-[#1F1F22] lg:hidden ${isNavbarOpen ? "hidden" : "block"}`}
      >
        <Layers color="#A2A2AB" size={21} />
      </button>
      <main className={`flex-grow transition-all duration-300 relative ${isNavbarOpen ? "lg:ml-[340px]" : "ml-0"}`}>
        {!isNavbarOpen && (
          <button
            onClick={() => setIsNavbarOpen(true)}
            className="fixed top-5 left-4 z-20 p-2 rounded-full cursor-pointer hover:bg-[#1F1F22] hidden lg:block"
          >
            <Layers color="#A2A2AB" size={21} />
          </button>
        )}
        <ChatInterface
          isProcessing={isProcessing}
          finalResult={displayResult}
          generatedImageUrl={displayImageUrl}
          userInput={userInput}
          setUserInput={setUserInput}
          handleSendMessage={handleSendMessage}
          originalInput={displayOriginalInput}
        />
      </main>
    </div>
  );
}

export default App;