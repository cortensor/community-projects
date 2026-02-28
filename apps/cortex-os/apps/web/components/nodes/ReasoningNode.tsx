"use client";

import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { BrainCircuit, Activity, Maximize2 } from "lucide-react";
import {   
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const ReasoningNode = memo(({ data, selected }: any) => {
  const onExpand = data.onOpenDetail;
  return (
    <Card className={`w-[350px] border-purple-700 bg-slate-900/95 shadow-xl backdrop-blur-md transition-all duration-500 hover:shadow-purple-500/10 hover:border-purple-500/30 ${data.status === 'RUNNING' || data.status === 'PENDING' ? 'shadow-purple-500/40 border-purple-400 scale-[1.02]' : 'shadow-purple-900/5'}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-mono text-purple-400 flex items-center gap-2">
          <div className="p-1 rounded bg-purple-500/10">
            <BrainCircuit className="w-3.5 h-3.5" />
          </div>
          [NODE: LLM_REASONING]
        </CardTitle>
        <Badge variant="outline" className="border-purple-500/30 text-[10px] text-purple-400 font-mono tracking-tighter">
          <Activity className="w-2.5 h-2.5 mr-1 animate-pulse" />
          {data.status || "IDLE"}
        </Badge>
      </CardHeader>
      
      <CardContent className="space-y-4 pt-2">
        <div>
          <div className="text-[10px] text-slate-500 font-mono mb-1.5 uppercase tracking-widest">System Instruction</div>
          <div className="bg-black/40 p-2 rounded text-[11px] font-mono text-slate-400 border border-slate-800/50 line-clamp-2 leading-relaxed">
            {data.instruction || "Awaiting execution parameters..."}
          </div>
        </div>

        <div className="relative group/term">
          <div className="flex justify-between items-center mb-1">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Inference Stream</div>
            {data.output && (
              <button 
                onClick={() => onExpand?.('Reasoning Analysis', String(data.output), 'reasoning')}
                className="text-slate-500 hover:text-purple-400 transition-colors p-1"
                title="Expand View"
              >
                <Maximize2 className="w-3 h-3" />
              </button>
            )}
          </div>
          <div className="relative bg-black/60 p-3 rounded text-[11px] font-mono text-purple-300 h-[120px] border border-slate-800/80 overflow-hidden leading-relaxed scrollbar-hide">
            {data.output ? (
              <span className="typing-animation whitespace-pre-wrap">{data.output}</span>
            ) : (
              <span className="text-slate-600 animate-pulse">_ waiting for upstream context...</span>
            )}
            {/* Terminal Masking Fade */}
            {data.output && (
              <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-black to-transparent pointer-events-none" />
            )}
          </div>
        </div>
      </CardContent>

      <CardFooter className="flex justify-between items-center border-t border-slate-800/50 pt-3 pb-3">
         <span className="text-[10px] text-slate-600 font-mono">Model: {data.model || "gemini-3-flash"}</span>
         {data.latency && <span className="text-[10px] text-emerald-500/70 font-mono">{data.latency}ms</span>}
      </CardFooter>

      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-slate-800 border-2 border-purple-500 rounded-sm"
      />
      
      <Handle
        type="target"
        id="context"
        position={Position.Left}
        className="w-2.5 h-2.5 bg-slate-800 border-2 border-slate-600 rounded-full"
      />

      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-purple-500 border-2 border-slate-800 rounded-sm"
      />
    </Card>
  );
});

ReasoningNode.displayName = "ReasoningNode";
