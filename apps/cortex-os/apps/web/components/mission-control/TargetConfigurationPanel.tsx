"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MissionControlProps {
  targetAddress: string;
  setTargetAddress: (address: string) => void;
  primaryModel: string;
  setPrimaryModel: (model: string) => void;
  consensusModel: string;
  setConsensusModel: (model: string) => void;
  isExecuting: boolean;
  isValidAddress: boolean;
}

export function TargetConfigurationPanel({
  targetAddress,
  setTargetAddress,
  primaryModel,
  setPrimaryModel,
  consensusModel,
  setConsensusModel,
  isExecuting,
  isValidAddress
}: MissionControlProps) {
  return (
    <Card className="w-full md:w-[320px] max-h-[calc(100vh-180px)] overflow-y-auto bg-black/80 border-slate-800 shadow-2xl backdrop-blur-md custom-scrollbar">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono tracking-widest text-emerald-400">MISSION CONTROL</CardTitle>
        </div>
        <CardDescription className="text-xs text-slate-400">
          Configure swarm parameters and target contract natively.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <label className="text-xs font-mono font-bold text-slate-300">TARGET SMART CONTRACT</label>
          <input
            type="text"
            className={`w-full bg-slate-950 border rounded-md p-2 text-xs font-mono text-slate-50 focus:outline-none transition-all disabled:opacity-50 ${
              targetAddress === "" 
                ? "border-slate-800 focus:border-emerald-500" 
                : isValidAddress 
                  ? "border-emerald-500/50 focus:border-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.1)]" 
                  : "border-red-500/50 focus:border-red-500 shadow-[0_0_10px_rgba(239,68,68,0.1)]"
            }`}
            placeholder="Enter Smart Contract Address (0x...)"
            value={targetAddress}
            onChange={(e) => setTargetAddress(e.target.value)}
            disabled={isExecuting}
          />
          {!isValidAddress && targetAddress !== "" && (
            <p className="text-[10px] text-red-400 font-mono mt-1 animate-pulse">
              [!] INVALID_EVM_FORMAT
            </p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-xs font-mono font-bold text-slate-300">PRIMARY REASONING MODEL</label>
          <select 
            className="w-full bg-slate-950 border border-slate-800 rounded-md p-2 text-xs font-mono text-slate-50 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-50"
            value={primaryModel}
            onChange={(e) => setPrimaryModel(e.target.value)}
            disabled={isExecuting}
          >
            <option value="gemini-3-flash">Gemini 3 Flash (Fast)</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep)</option>
            <option value="llama-3-70b" disabled>Llama-3 70B (Offline)</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-mono font-bold text-slate-300">CONSENSUS VALIDATOR</label>
          <select 
            className="w-full bg-slate-950 border border-slate-800 rounded-md p-2 text-xs font-mono text-slate-50 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-50"
            value={consensusModel}
            onChange={(e) => setConsensusModel(e.target.value)}
            disabled={isExecuting}
          >
            <option value="groq-llama-3">Groq LPU (Llama-3)</option>
            <option value="mistral-large">Mistral Large (Redundant)</option>
            <option value="gemma-7b">Gemma 7b (Redundant)</option>
          </select>
        </div>
      </CardContent>
    </Card>
  );
}
