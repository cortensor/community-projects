"use client";

import React, { useCallback, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  BackgroundVariant,
  Panel,
  Node
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseAbi } from 'viem';
import { IngestionNode } from '@/components/nodes/IngestionNode';
import { ReasoningNode } from '@/components/nodes/ReasoningNode';
import { CollectorNode } from '@/components/nodes/CollectorNode';
import { TargetConfigurationPanel } from '@/components/mission-control/TargetConfigurationPanel';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Play, RotateCcw, AlertTriangle, CheckCircle2, Copy, Check, ExternalLink, Maximize2, Activity } from 'lucide-react';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const nodeTypes = {
  ingestion: IngestionNode,
  reasoning: ReasoningNode,
  collector: CollectorNode
};

const INITIAL_NODES: Node[] = [
  {
    id: 'node_1_scanner',
    type: 'ingestion',
    position: { x: 380, y: 50 },
    data: { status: 'IDLE', target: '0xTargetSmartContractAddress', output: null },
  },
  {
    id: 'node_2_analyzer',
    type: 'reasoning',
    position: { x: 330, y: 300 },
    data: { status: 'IDLE', instruction: 'Analyze the provided JSON bytecode and ABI for reentrancy, integer overflow, and access control flaws.', model: 'gemini-3-flash', output: null, latency: null },
  },
  {
    id: 'node_3_consensus',
    type: 'collector',
    position: { x: 310, y: 550 },
    data: { status: 'IDLE', primaryModel: 'Groq Llama-3', redundancyModels: ['Cortensor/Mistral'], output: null, latency: null, consensusScore: null, onOpenDetail: null },
  },
];

const INITIAL_EDGES: Edge[] = [
  { id: 'e1-2', source: 'node_1_scanner', target: 'node_2_analyzer' },
  { id: 'e2-3', source: 'node_2_analyzer', target: 'node_3_consensus' },
];

export function CortexFlow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const [isExecuting, setIsExecuting] = useState(false);
  const [copied, setCopied] = useState(false);
  
  // Dynamic Mission Control State
  const [targetAddress, setTargetAddress] = useState("");
  const [primaryModel, setPrimaryModel] = useState("gemini-3-flash");
  const [consensusModel, setConsensusModel] = useState("groq-llama-3");
  const [selectedTerminalOutput, setSelectedTerminalOutput] = useState<{title: string, content: string, type?: string} | null>(null);

  // Simple EVM Address Validation
  const isValidAddress = /^0x[a-fA-F0-9]{40}$/.test(targetAddress);

  // Web3 Settlement State
  const [proofData, setProofData] = useState<{ cid: string; hash: string } | null>(null);
  const { writeContract, data: hash, isPending: isConfirmingWallet, error: txError } = useWriteContract();
  const { isLoading: isTxConfirming, isSuccess: isTxConfirmed } = useWaitForTransactionReceipt({ hash });

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const resetGraph = () => {
    setNodes(INITIAL_NODES);
    setEdges(INITIAL_EDGES);
    setProofData(null);
  };

  const executeSwarm = async () => {
    if (isExecuting || !isValidAddress) return;
    
    console.log("[CORTEX] Initiating swarm for target:", targetAddress);
    toast.info("SWARM_INITIATION: Validating topology...");
    setIsExecuting(true);

    try {
      // Step 1: Set all nodes to pending natively and update local state
      const updatedNodes = nodes.map(n => {
        let newData: Record<string, any> = { ...n.data, status: 'PENDING', output: null, onOpenDetail: openTerminalDetail };
        if (n.type === 'ingestion') newData.target = targetAddress;
        if (n.type === 'reasoning') newData.model = primaryModel;
        if (n.type === 'collector') newData.primaryModel = consensusModel;
        return { ...n, id: n.id, data: newData };
      });
      setNodes(updatedNodes);

      // Step 2: Trigger Engine via SSE POST
      const payload = {
        swarmId: `EXEC-${Date.now()}`,
        targetSmartContract: targetAddress,
        modelOverrides: {
          primary: primaryModel,
          consensus: consensusModel
        },
        graphConfig: { nodes: updatedNodes, edges }
      };

      console.log("[CORTEX] API Connection established. Reading stream...");
      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP_ERROR_${response.status}`);
      }

      if (!response.body) throw new Error("No ReadableStream provided by engine.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      toast.success("SWARM_ACTIVE: Intelligence sequence broadcasting...");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        
        // Process complete chunks
        for (let i = 0; i < lines.length - 1; i++) {
          const chunk = lines[i];
          if (!chunk.trim()) continue;

          // SSE parsing
          const eventMatch = chunk.match(/event: (.+)/);
          const dataMatch = chunk.match(/data: (.+)/);

          if (eventMatch && dataMatch) {
            const eventName = eventMatch[1].trim();
            const rawData = dataMatch[1].trim();
            let payloadObj;
            try {
              payloadObj = JSON.parse(rawData);
            } catch(e) { 
              console.warn("[SSE_PARSE_ERROR] Failed to parse JSON:", rawData);
              continue; 
            }

            console.log(`[SSE_${eventName}]`, payloadObj);

            if (eventName === 'node_status') {
               setNodes((nds) => nds.map(n => 
                 n.id === payloadObj.nodeId ? { ...n, data: { ...n.data, status: payloadObj.status } } : n
               ));
            } else if (eventName === 'node_complete') {
               setNodes((nds) => nds.map(n => 
                 n.id === payloadObj.nodeId ? { 
                   ...n, 
                   data: { 
                     ...n.data, 
                     status: 'COMPLETED', 
                     output: payloadObj.output,
                     latency: payloadObj.latency,
                     consensusScore: payloadObj.consensusScore
                   } 
                 } : n
               ));
            } else if (eventName === 'system' && payloadObj.ipfsCid) {
               console.log("DAG Execution finalized.", payloadObj.finalMemory);
               setProofData({ cid: payloadObj.ipfsCid, hash: payloadObj.executionHash });
               toast.success("SWARM_COMPLETE: Verifiable Proof Generated!", {
                 description: "Artifact pinned to IPFS. Ready for on-chain settlement.",
                 icon: <CheckCircle2 className="w-4 h-4 text-emerald-500" />
               });
            } else if (eventName === 'system_error') {
               console.error("[SYSTEM_ERROR_RECEIVED]", payloadObj);
               const errorMsg = payloadObj.message || payloadObj.error || "Unknown failure.";
               const errorDetails = payloadObj.details ? ` Details: ${payloadObj.details}` : "";
               
               toast.error("ENGINE_SYSTEM_ERROR", {
                 description: `${errorMsg}${errorDetails}`,
                 icon: <AlertTriangle className="w-4 h-4 text-red-500" />
               });
            }
          }
        }
        
        // Keep the last broken chunk in the buffer
        buffer = lines[lines.length - 1];
      }
      console.log("[CORTEX] Stream fully read and closed.");
    } catch (e: any) {
      console.error("Swarm Execution Failed:", e);
      toast.error("SWARM_ERROR: Execution Interrupted", {
        description: e.message || "Unknown engine failure.",
        icon: <AlertTriangle className="w-4 h-4 text-red-500" />
      });
    } finally {
      setIsExecuting(false);
    }
  };
  const openTerminalDetail = useCallback((title: string, content: string, type?: string) => {
    setSelectedTerminalOutput({ title, content, type });
  }, []);

  return (
    <div className="w-full h-full border border-slate-800 rounded-xl bg-black/50 relative overflow-hidden group custom-flow-container">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{ animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } }}
        fitView
        className="bg-slate-950 rounded-xl"
        style={{ width: '100%', height: '100%' }}
      >
        <Controls 
          className="bg-slate-900 border-2 border-slate-700 !scale-150 !origin-bottom-left m-6 shadow-2xl shadow-emerald-500/10 custom-controls" 
          showInteractive={false}
        />
        <MiniMap 
          nodeColor={(node) => {
            switch (node.type) {
              case 'ingestion': return '#3b82f6';
              case 'reasoning': return '#8b5cf6';
              case 'collector': return '#10b981';
              default: return '#1e293b';
            }
          }}
          className="bg-slate-900/60 border-2 border-slate-800/50 rounded-xl !bottom-6 !right-6 shadow-2xl backdrop-blur-md custom-minimap"
          maskColor="rgba(0, 0, 0, 0.6)"
        />
        <Background variant={BackgroundVariant.Dots} gap={24} size={2} color="#1e293b" />
        
        {/* Mission Control Sidebar Panel */}
        <Panel position="top-left" className="m-6 max-w-[calc(100vw-80px)] md:max-w-sm">
           <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 backdrop-blur-2xl shadow-2xl shadow-black/50 overflow-hidden transition-all duration-700 hover:border-emerald-500/20">
             <TargetConfigurationPanel 
                targetAddress={targetAddress}
                setTargetAddress={setTargetAddress}
                primaryModel={primaryModel}
                setPrimaryModel={setPrimaryModel}
                consensusModel={consensusModel}
                setConsensusModel={setConsensusModel}
                isExecuting={isExecuting}
                isValidAddress={isValidAddress}
             />
           </div>
        </Panel>

        {/* Swarm Command Panel */}
        <Panel position="top-right" className="flex flex-col md:flex-row gap-3 m-4">
             <Button 
                variant="outline" 
                onClick={resetGraph}
                disabled={isExecuting}
                className="border-slate-700 bg-slate-900/80 hover:bg-slate-800 hover:text-white backdrop-blur-sm"
             >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset Graph
             </Button>
             <Button 
                onClick={executeSwarm}
                disabled={isExecuting || !!proofData || !isValidAddress}
                className={`text-white font-mono gap-2 transition-all shadow-lg backdrop-blur-sm ${isExecuting ? 'bg-slate-700' : (!isValidAddress ? 'bg-slate-800 opacity-50 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-500 animate-pulse shadow-emerald-500/20')}`}
             >
                <Play className={`w-4 h-4 fill-current ${isExecuting ? 'animate-spin' : ''}`}/>
                {isExecuting ? '[EXECUTING_SWARM...]' : (!isValidAddress ? '[INVALID_ADDRESS]' : '[INITIATE_SWARM]')}
             </Button>
        </Panel>

        {/* Web3 Settlement Panel */}
        {proofData && (
          <Panel position="bottom-center" className="bg-slate-900/60 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-3xl shadow-[0_-20px_80px_-15px_rgba(0,0,0,0.8)] flex flex-col items-center gap-5 w-[90vw] md:w-[550px] mb-12 group animate-in slide-in-from-bottom-10 fade-in duration-700 border-b-emerald-500/30">
             <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald-500 text-black text-[10px] font-black px-4 py-1.5 rounded-full shadow-2xl shadow-emerald-500/40 tracking-[0.2em]">
               MISSION_ACCOMPLISHED
             </div>
             <div className="text-xs font-mono text-emerald-400 text-center space-y-2 mt-2">
               <div className="flex items-center justify-center gap-2">
                 <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                 CRYPTOGRAPHIC PROOF READY
               </div>
               <div className="flex items-center gap-2 w-full">
                 <div className="flex-1 text-slate-500 bg-black/40 p-2 rounded border border-slate-800 break-all font-mono text-[10px] select-all hover:border-slate-600 transition-colors">
                   {proofData.cid}
                 </div>
                 <Button
                   size="icon"
                   variant="ghost"
                   className="h-8 w-8 hover:bg-slate-800 shrink-0"
                   onClick={() => {
                     navigator.clipboard.writeText(proofData.cid);
                     setCopied(true);
                     toast.success("CID_COPIED: Ready for verification.");
                     setTimeout(() => setCopied(false), 2000);
                   }}
                 >
                   {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4 text-slate-400" />}
                 </Button>
               </div>
               
               <a 
                 href={`https://gateway.pinata.cloud/ipfs/${proofData.cid}`} 
                 target="_blank" 
                 rel="noreferrer"
                 className="flex items-center gap-1.5 text-[10px] text-emerald-500/70 hover:text-emerald-400 transition-colors font-mono uppercase tracking-wider mt-1"
               >
                 <ExternalLink className="w-3 h-3" />
                 View Raw Metadata on IPFS
               </a>
             </div>
             <Button
                disabled={isConfirmingWallet || isTxConfirming || isTxConfirmed}
                className={`w-full font-mono font-bold h-12 text-sm shadow-xl transition-all active:scale-95 ${isTxConfirmed ? 'bg-blue-600 hover:bg-blue-500' : 'bg-gradient-to-r from-purple-600 to-emerald-600 hover:from-purple-500 hover:to-emerald-500'}`}
                onClick={() => {
                  writeContract({
                    address: "0xABeEDDDbB67Ec02B1c426C6EaE8d1618a6278e2f" as `0x${string}`,
                    abi: parseAbi(["function mintVerificationArtifact(string memory _ipfsCid, bytes32 _executionHash) external returns (uint256)"]),
                    functionName: "mintVerificationArtifact",
                    args: [proofData.cid, (proofData.hash.startsWith('0x') ? proofData.hash : `0x${proofData.hash}`) as `0x${string}`],
                  });
                }}
             >
                {isConfirmingWallet ? "APPROVE IN WALLET..." : isTxConfirming ? "MINING TX..." : isTxConfirmed ? "✓ PROOF MINTED ON-CHAIN" : "MINT ERC-8004 ARTIFACT"}
             </Button>
             
             {isTxConfirmed && hash && (
               <a href={`https://sepolia.basescan.org/tx/${hash}`} target="_blank" rel="noreferrer" className="text-xs text-blue-400 hover:text-blue-300 font-mono underline decoration-blue-400/30 underline-offset-4 hover:decoration-blue-400 flex items-center gap-1 transition-all">
                 <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                 Explore Evidence on BaseScan
               </a>
             )}
             
             {txError && (
               <div className="text-red-400 text-[10px] font-mono mt-2 p-3 bg-red-950/30 border border-red-900/50 rounded-lg w-full break-words">
                 <span className="text-red-500 font-bold mr-2">[!]</span> {txError.message}
               </div>
             )}
          </Panel>
        )}
      </ReactFlow>
      
      <div className="absolute top-4 left-1/2 -translate-x-1/2 md:left-[380px] md:translate-x-0 pointer-events-none text-center md:text-left flex items-center gap-4">
        <img src="/Cortex_OS.png" alt="Cortex.OS Logo" className="w-20 h-20 object-contain drop-shadow-[0_0_25px_rgba(16,185,129,0.6)] transition-transform hover:scale-105" />
        <div>
          <h2 className="text-xl font-mono font-bold tracking-[0.2em] text-slate-100 uppercase drop-shadow-[0_0_15px_rgba(16,185,129,0.4)]">
            CORTEX<span className="text-emerald-500">.OS</span> <span className="text-slate-700 font-light">//</span> CANVAS
          </h2>
          <p className="text-[10px] text-slate-500 font-mono tracking-widest opacity-80 uppercase mt-1">DAG EXECUTION ENGINE v2.1-STABLE</p>
        </div>
      </div>
      <Dialog open={!!selectedTerminalOutput} onOpenChange={(open) => !open && setSelectedTerminalOutput(null)}>
        <DialogContent className={`max-w-4xl h-[85vh] md:h-[80vh] bg-slate-900 border-slate-800 text-slate-300 font-mono shadow-2xl flex flex-col p-0 overflow-hidden ring-1 transition-all duration-500 ${
          selectedTerminalOutput?.type === 'consensus' ? 'ring-emerald-500/40' : 
          selectedTerminalOutput?.type === 'reasoning' ? 'ring-purple-500/50' : 
          'ring-blue-500/40'
        }`}>
          {/* Subtle Dynamic Background Glow */}
          <div className={`absolute inset-0 opacity-[0.03] pointer-events-none transition-colors duration-700 ${
            selectedTerminalOutput?.type === 'consensus' ? 'bg-emerald-500' : 
            selectedTerminalOutput?.type === 'reasoning' ? 'bg-purple-500' : 
            'bg-blue-500'
          }`} />

          <DialogHeader className="p-6 border-b border-slate-800 shrink-0 bg-slate-900/80 backdrop-blur-md relative z-20">
            <DialogTitle className={`flex items-center gap-3 text-xl font-bold tracking-tight transition-colors ${
              selectedTerminalOutput?.type === 'consensus' ? 'text-emerald-400' : 
              selectedTerminalOutput?.type === 'reasoning' ? 'text-purple-400' : 
              'text-blue-400'
            }`}>
              <div className={`p-1.5 rounded-lg border transition-colors ${
                selectedTerminalOutput?.type === 'consensus' ? 'bg-emerald-500/10 border-emerald-500/20 shadow-[0_0_15px_-5px_#10b981]' : 
                selectedTerminalOutput?.type === 'reasoning' ? 'bg-purple-500/10 border-purple-500/20 shadow-[0_0_15px_-5px_#8b5cf6]' : 
                'bg-blue-500/10 border-blue-500/20 shadow-[0_0_15px_-5px_#3b82f6]'
              }`}>
                <Activity className={`w-5 h-5 animate-pulse ${
                  selectedTerminalOutput?.type === 'consensus' ? 'text-emerald-400' : 
                  selectedTerminalOutput?.type === 'reasoning' ? 'text-purple-400' : 
                  'text-blue-400'
                }`} />
              </div>
              {selectedTerminalOutput?.title}
            </DialogTitle>
          </DialogHeader>
          
          <div className={`flex-1 overflow-y-auto p-8 bg-black/40 scroll-smooth relative pb-12 custom-scrollbar ${
            selectedTerminalOutput?.type === 'consensus' ? '[&::-webkit-scrollbar-thumb]:bg-emerald-500/20' : 
            selectedTerminalOutput?.type === 'reasoning' ? '[&::-webkit-scrollbar-thumb]:bg-purple-500/20' : 
            '[&::-webkit-scrollbar-thumb]:bg-blue-500/20'
          }`}>
            <div className="text-[16px] leading-relaxed whitespace-pre-wrap selection:bg-white/10 text-slate-300 font-sans opacity-95 hover:opacity-100 transition-opacity max-w-none relative z-10">
              {/* V4: Recursive Inline Markdown Parser */}
              {(() => {
                const renderFormatted = (text: string) => {
                  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
                  return parts.map((part, index) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                      const boldText = part.slice(2, -2);
                      return <strong key={index} className={`font-black text-[105%] transition-colors ${
                        selectedTerminalOutput?.type === 'consensus' ? 'text-emerald-400' : 
                        selectedTerminalOutput?.type === 'reasoning' ? 'text-purple-400' : 
                        'text-blue-400'
                      }`}>{boldText}</strong>;
                    }
                    if (part.startsWith('`') && part.endsWith('`')) {
                      return <code key={index} className="bg-white/5 px-2 py-0.5 rounded text-xs font-mono text-white/80 border border-white/5 mx-0.5">{part.slice(1, -1)}</code>;
                    }
                    return part;
                  });
                };

                return selectedTerminalOutput?.content.split('\n').map((line, i) => {
                  const trimmed = line.trim();
                  
                  // Header 3 - Major Section
                  if (trimmed.startsWith('### ')) return <h3 key={i} className={`text-2xl font-black mt-10 mb-6 border-l-4 pl-5 transition-colors tracking-tight ${
                    selectedTerminalOutput?.type === 'consensus' ? 'text-emerald-500 border-emerald-500/50' : 
                    selectedTerminalOutput?.type === 'reasoning' ? 'text-purple-400 border-purple-500/50' : 
                    'text-blue-400 border-blue-500/50'
                  }`}>{line.replace('### ', '')}</h3>;
                  
                  // Header 4 - Sub Section
                  if (trimmed.startsWith('#### ')) return <h4 key={i} className={`text-xl font-bold mt-8 mb-3 transition-colors ${
                    selectedTerminalOutput?.type === 'consensus' ? 'text-emerald-300' : 
                    selectedTerminalOutput?.type === 'reasoning' ? 'text-purple-300' : 
                    'text-blue-300'
                  }`}>{line.replace('#### ', '')}</h4>;
                  
                  // Custom List with Themed Dots & Nested Formatting
                  if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
                     const content = line.replace(/^[\s]*[\*\-]\s/, '');
                     return (
                       <div key={i} className="ml-6 mb-3 flex gap-3 items-start group">
                         <span className={`mt-2.5 w-1.5 h-1.5 rounded-full shrink-0 transition-all group-hover:scale-125 ${
                           selectedTerminalOutput?.type === 'consensus' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 
                           selectedTerminalOutput?.type === 'reasoning' ? 'bg-purple-500 shadow-[0_0_8px_#8b5cf6]' : 
                           'bg-blue-500 shadow-[0_0_8px_#3b82f6]'
                         }`} />
                         <span className="text-slate-300 group-hover:text-slate-100 transition-colors">
                           {renderFormatted(content)}
                         </span>
                       </div>
                     );
                  }
                  
                  // Horizontal Rule
                  if (trimmed === '---') return <hr key={i} className={`my-10 opacity-30 ${
                    selectedTerminalOutput?.type === 'consensus' ? 'border-emerald-500/30' : 
                    selectedTerminalOutput?.type === 'reasoning' ? 'border-purple-500/30' : 
                    'border-blue-500/30'
                  }`} />;
                  
                  // Standard Paragraph with Inline Formatting
                  return <p key={i} className="mb-5 tracking-normal text-slate-300/90 leading-[1.7]">{renderFormatted(line)}</p>;
                });
              })()}
            </div>
          </div>
          
          {/* Faded Overflow Indicator (Shadow) - Positioned at the very exit of the scroll container */}
          <div className={`absolute bottom-[68px] left-0 right-0 h-16 bg-gradient-to-t pointer-events-none z-10 transition-colors duration-700 opacity-90 ${
            selectedTerminalOutput?.type === 'consensus' ? 'from-slate-950/80 to-transparent' : 
            selectedTerminalOutput?.type === 'reasoning' ? 'from-slate-950/90 to-transparent' : 
            'from-slate-950/80 to-transparent'
          }`} />
          
          <div className="p-5 border-t border-slate-800/80 bg-slate-900/95 backdrop-blur-xl flex justify-between items-center shrink-0 z-30 relative">
             <div className="text-[10px] text-slate-600 uppercase tracking-[0.3em] font-black pl-3 flex items-center gap-2">
               <div className={`w-1 h-1 rounded-full animate-blink ${
                  selectedTerminalOutput?.type === 'consensus' ? 'bg-emerald-500' : 
                  selectedTerminalOutput?.type === 'reasoning' ? 'bg-purple-500' : 
                  'bg-blue-500'
               }`} />
               DATA_SYNC_VERIFIED_V2.1
             </div>
             <Button 
               variant="outline" 
               size="sm" 
               className={`border-slate-700 font-black tracking-widest text-[10px] h-9 px-6 transition-all active:scale-95 ${
                 selectedTerminalOutput?.type === 'consensus' ? 'hover:border-emerald-500/50 hover:bg-emerald-500/10 hover:text-emerald-300' : 
                 selectedTerminalOutput?.type === 'reasoning' ? 'hover:border-purple-500/50 hover:bg-purple-500/10 hover:text-purple-300' : 
                 'hover:border-blue-500/50 hover:bg-blue-500/10 hover:text-blue-300'
               }`}
               onClick={() => setSelectedTerminalOutput(null)}
             >
               TERMINATE VIEW
             </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
