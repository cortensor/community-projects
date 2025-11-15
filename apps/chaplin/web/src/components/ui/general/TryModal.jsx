import React, { useState, useRef, useEffect } from "react";
import { Wrench, X } from "lucide-react";
import { SendSolid } from "iconoir-react";
import SimpleBar from "simplebar-react";
import "simplebar-react/dist/simplebar.min.css";
import Avatar from "../../../assets/avatar.png";
import ChaplinImage from "../../../assets/persona.png";
import { startChaplinStream } from "../../../services/apiService";

// Funções auxiliares para obter um ID de sessão do cliente
function getClientSessionId() {
  let id = localStorage.getItem("clientSessionId");
  if (!id) {
    id = `cs_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    try { localStorage.setItem("clientSessionId", id); } catch (e) { }
  }
  return id;
}

// Sub-componente para renderizar a tabela de resultados
function ResultsTable({ data }) {
  if (!data || typeof data !== "object") {
    const errorMessage = data?.error || data?.raw || "An unknown error occurred.";
    return <div className="text-sm text-red-400 p-3 bg-[#1B1B1B] rounded-xl">{String(errorMessage)}</div>;
  }

  return (
    <div className="table w-full max-w-lg rounded-xl overflow-hidden border border-[#303135]">
      {Object.entries(data).map(([key, value], index) => {
        const displayValue = typeof value === 'object' && value !== null
          ? JSON.stringify(value, null, 2)
          : String(value);

        return (
          <div key={key} className={`table-row ${index % 2 === 0 ? 'bg-[#2A2A2A]' : 'bg-[#1B1B1B]'}`}>
            <div className="table-cell p-3 w-0 whitespace-nowrap align-middle">
              <p className="font-mono text-center text-xs px-2 py-1 bg-[#363636] rounded-full">{key}</p>
            </div>
            <div className="table-cell p-3 pl-4 border-l border-l-[#353535] align-middle">
              <p className="text-sm text-[#C1C1C2] whitespace-pre-wrap">{displayValue}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChaplinMessage({ persona, message }) {
  const personaImage = persona.image_url || ChaplinImage;

  return (
    <div className="flex justify-start items-start gap-3">
      <img src={personaImage} alt={persona.name} className="w-10 h-10 rounded-full" />
      <div className="flex flex-col items-start w-full">
        <p className="text-xs font-medium text-[#F3F6FA] mb-1">{persona.name}</p>
        {message.status === 'processing' ? (
          <div className="text-sm text-[#9e9e9e] italic animate-pulse">{message.statusText}</div>
        ) : (
          <ResultsTable data={message.content} />
        )}
      </div>
    </div>
  );
}

// Componente Principal do Modal
export default function TryModal({ chaplin, onClose, onSaveResults }) {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentResults, setAgentResults] = useState({});
  const [currentJobId, setCurrentJobId] = useState(null);

  const simpleBarRef = useRef(null);
  const streamControllerRef = useRef(null);
  const currentChaplinMessageIdRef = useRef(null);
  const processedChunkIdsRef = useRef(new Set());

  const chaplinId = chaplin?.id;
  const chaplinName = chaplin?.name || "Chaplin";
  const chaplinInstructions = chaplin?.instructions || "No instructions provided.";
  const chaplinImage = chaplin?.image_url || chaplin?.avatarUrl || ChaplinImage;

  // Efeito para scroll automático
  useEffect(() => {
    if (simpleBarRef.current) {
      const el = simpleBarRef.current.getScrollElement();
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  // Efeito para fechar com a tecla 'Escape'
  useEffect(() => {
    const handleEsc = (event) => {
      if (event.key === 'Escape') handleCloseExplicit();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Efeito para gerenciar a visibilidade da aba e a reconexão
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.hidden) {
        if (streamControllerRef.current) {
          console.log("[TryModal] Tab hidden, aborting stream to re-attach later.");
          streamControllerRef.current.abort();
          streamControllerRef.current = null;
        }
      } else {
        if (isProcessing && currentJobId && !streamControllerRef.current) {
          console.log(`[TryModal] Tab visible, re-attaching to job ${currentJobId}.`);
          const payload = {
            jobId: currentJobId,
          };
          startStreamWithPayload(payload);
        }
      }
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [isProcessing, currentJobId]);

  // Função para iniciar/conectar à stream
  function startStreamWithPayload(payload) {
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
    }

    streamControllerRef.current = startChaplinStream(payload, {
      onData: (chunk) => {
        if (chunk.type === 'start' && chunk.jobId && chunk.jobId !== currentJobId) {
          console.log(`[TryModal] Acquired and setting Job ID: ${chunk.jobId}`);
          setCurrentJobId(chunk.jobId);
        }

        if (!currentChaplinMessageIdRef.current) {
          const newChaplinMessage = {
            id: `chaplin-${Date.now()}`, type: "chaplin", status: "processing",
            statusText: "Processing...", content: null, meta: { jobId: payload.jobId || null },
          };
          currentChaplinMessageIdRef.current = newChaplinMessage.id;
          setMessages((prev) => [...prev, newChaplinMessage]);
        }

        const chunkId = `${chunk.type}-${JSON.stringify(chunk.data || {})}`;
        if (processedChunkIdsRef.current.has(chunkId)) return;
        processedChunkIdsRef.current.add(chunkId);

        applyChunkToMessage(chunk, currentChaplinMessageIdRef.current);
      },
      onError: (err) => {
        console.error("[TryModal] Stream error received:", err.message);
        streamControllerRef.current = null;
        // Opcional: Adicionar mensagem de erro na UI
        applyChunkToMessage({ type: 'error', data: { message: "Connection error. Please try again." } }, currentChaplinMessageIdRef.current);
        setIsProcessing(false);
      },
      onClose: () => {
        setIsProcessing(false);
        streamControllerRef.current = null;
      },
    });
  }

  // Função para atualizar a UI com os dados da stream
  function applyChunkToMessage(chunk, mid) {
    if (!mid || !chunk) return;
    setMessages(prev => prev.map(m => {
      if (m.id !== mid) return m;
      const updated = { ...m };
      const name = chunk.data?.name || chunk.data?.agentName || 'Agent';

      if (chunk.type === 'start') {
        updated.statusText = 'Processing your request...';
      } else if (chunk.type === 'agent_start') {
        updated.statusText = `${name} started...`;
      } else if (chunk.type === 'agent_attempt') {
        const attempt = chunk.data?.attempt ?? chunk.data?.attemptNumber ?? 0;
        const max = chunk.data?.maxAttempts ?? chunk.data?.max ?? '?';
        updated.statusText = `Waiting for ${name} attempt ${attempt} of ${max}...`;
      } else if (chunk.type === 'agent_result') {
        updated.statusText = `${name} responded`;
        if (chunk.data?.name && chunk.data?.output) {
          setAgentResults(prev => ({ ...prev, [chunk.data.name]: chunk.data.output }));
        }
      } else if (chunk.type === 'integrator_start') {
        updated.statusText = 'Assembling final response...';
      } else if (chunk.type === 'integrator_result') {
        updated.status = 'complete';
        updated.content = chunk.data?.final || {};
        updated.statusText = '';
      } else if (chunk.type === 'error' || chunk.type === 'agent_error') {
        updated.status = 'complete';
        updated.content = { Error: chunk.data?.message || chunk.data?.error || 'Unknown error' };
        updated.statusText = '';
      } else if (chunk.type === 'done') {
        if (updated.status !== 'complete') { // Só finaliza se não tiver um resultado final ainda
          updated.status = 'complete';
          updated.statusText = '';
          if (!updated.content) updated.content = { Info: "Processing finished." };
        }
      }
      return updated;
    }));
  }

  // Handler para o envio de uma nova mensagem
  const handleSendMessage = () => {
    if (!userInput.trim() || isProcessing) return;
    const text = userInput.trim();

    const userMsg = { id: `user-${Date.now()}`, type: 'user', text };
    const chapMsg = { id: `chaplin-${Date.now()}`, type: 'chaplin', status: 'processing', statusText: 'Connecting to Chaplin...', content: null };
    currentChaplinMessageIdRef.current = chapMsg.id;

    setMessages(prev => [...prev, userMsg, chapMsg]);
    setUserInput("");
    setIsProcessing(true);
    processedChunkIdsRef.current.clear();
    setAgentResults({});
    setCurrentJobId(null);

    let payload;
    if (chaplinId) {
      payload = { chaplin_id: chaplinId, input: text, clientSessionId: getClientSessionId() };
    } else {
      payload = {
        chaplinData: { workgroup: chaplin.workgroup, responseformat: chaplin.responseformat },
        input: text, clientSessionId: getClientSessionId()
      };
    }
    startStreamWithPayload(payload);
  };

  // Handler para fechar o modal explicitamente
  const handleCloseExplicit = () => {
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
    }
    if (typeof onSaveResults === 'function') {
      onSaveResults(agentResults);
    }
    setMessages([]);
    setIsProcessing(false);
    setCurrentJobId(null);
    if (typeof onClose === 'function') {
      onClose();
    }
  };

  // Efeito de limpeza ao desmontar o componente
  useEffect(() => {
    return () => {
      if (streamControllerRef.current) {
        streamControllerRef.current.abort();
      }
    };
  }, []);

  const displayPersona = { name: chaplinName, image_url: chaplinImage };

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex justify-center items-center z-50" onClick={handleCloseExplicit}>
      <div className="bg-[#26272B] rounded-2xl w-[800px] h-[600px] p-6 flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center">
          <h2 className="text-md font-semibold text-[#E3E3E4]">{chaplinName}</h2>
          <button onClick={handleCloseExplicit} className="cursor-pointer p-1 pb-5"><X color="#BFBCBC" size={22} /></button>
        </div>
        <div className="w-full h-px bg-[#303135] mt-1"></div>
        <div className="flex-grow overflow-hidden my-4">
          <SimpleBar ref={simpleBarRef} className="category-dropdown-scrollbar h-full">
            <div className="flex flex-col gap-8 pr-3 pb-5">
              <div className="flex justify-start items-start gap-3 pt-1">
                <div className="flex-shrink-0 items-center justify-center w-10 h-10 rounded-full bg-gradient-to-r from-[#0A0A0A] to-[#2B2B2B] shadow-lg flex">
                  <Wrench color="#B3B3B3" size={21} />
                </div>
                <div className="flex flex-col items-start">
                  <p className="text-sm font-semibold text-[#E3E3E4] mb-1">Instructions</p>
                  <div className="bg-gradient-to-r from-[#1B1B1B] to-[#2B2B2B] rounded-xl p-4 max-w-xl shadow-lg">
                    <p className="text-justify text-sm text-[#BDBBBE]">{chaplinInstructions}</p>
                  </div>
                </div>
              </div>
              {messages.map((msg) => msg.type === 'user' ? (
                <div key={msg.id} className="flex justify-end items-start gap-3">
                  <div className="flex flex-col items-end">
                    <p className="text-xs font-medium text-[#F3F6FA] mb-1">You</p>
                    <div className="bg-[#35373B] rounded-xl p-3 max-w-md">
                      <p className="text-sm text-[#C1C1C2] whitespace-pre-wrap">{msg.text}</p>
                    </div>
                  </div>
                  <img src={Avatar} alt="user" className="w-10 h-10 rounded-full" />
                </div>
              ) : (
                <ChaplinMessage key={msg.id} persona={displayPersona} message={msg} />
              ))}
            </div>
          </SimpleBar>
        </div>
        <div className="flex-shrink-0">
          <div className="relative flex items-center">
            <input
              type="text"
              placeholder={`Ask ${chaplinName}...`}
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={isProcessing}
              className="w-full bg-[#37393D] text-[#FAFAFA] text-sm placeholder:text-[#7C7C7C] rounded-full py-3 pl-5 pr-14 border border-[#505050] focus:outline-none focus:ring-1 focus:ring-[#FAFAFA] transition-all duration-200"
            />
            <button
              onClick={handleSendMessage}
              disabled={isProcessing || !userInput.trim()}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-white p-2.5 rounded-full font-semibold hover:bg-[#E4E4E5] transition-all duration-200 cursor-pointer "
            >
              <SendSolid color="#242424" height={15} width={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}