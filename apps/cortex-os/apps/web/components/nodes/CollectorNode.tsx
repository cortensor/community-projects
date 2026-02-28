"use client";

import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { ShieldAlert, Activity, CheckCircle2, AlertTriangle, Maximize2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const CollectorNode = memo(({ data }: any) => {
  const onExpand = data.onOpenDetail;
  const isConsensusReached = data.consensusScore && data.consensusScore > 0.8;

  return (
    <Card className={`w-[350px] border-emerald-700 bg-slate-900/95 shadow-xl backdrop-blur-md transition-all duration-500 hover:shadow-emerald-500/10 hover:border-emerald-500/30 ${isConsensusReached ? 'shadow-emerald-500/40 border-emerald-400 scale-[1.05]' : 'shadow-emerald-900/5'}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-mono text-emerald-400 flex items-center gap-2">
          <div className="p-1 rounded bg-emerald-500/10">
            <ShieldAlert className="w-3.5 h-3.5" />
          </div>
          [NODE: CONSENSUS]
        </CardTitle>
        <Badge variant={isConsensusReached ? "default" : "destructive"} className={isConsensusReached ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[10px] hover:bg-emerald-500/30 font-mono tracking-tighter" : "text-[10px] font-mono tracking-tighter"}>
          <Activity className="w-2.5 h-2.5 mr-1 animate-pulse" />
          {data.status || "IDLE"}
        </Badge>
      </CardHeader>
      
      <CardContent className="space-y-4 pt-2">
        <div className="relative group/term">
          <div className="flex justify-between items-center mb-1">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Auditor Conclusion</div>
            {data.output && (
              <button 
                onClick={() => onExpand?.('Consensus Report', String(data.output), 'consensus')}
                className="text-slate-500 hover:text-emerald-400 transition-colors p-1"
                title="Expand View"
              >
                <Maximize2 className="w-3 h-3" />
              </button>
            )}
          </div>
          
          <div className="relative bg-black/60 p-3 rounded text-[11px] font-mono text-slate-300 h-[140px] border border-slate-800/80 overflow-hidden leading-relaxed">
            {data.output ? (
               <div className="flex flex-col gap-2">
                  <span className="text-emerald-300/90 font-medium whitespace-pre-wrap">{data.output}</span>
                  {isConsensusReached ? (
                    <div className="flex items-center text-emerald-500 mt-2 py-1 px-2 bg-emerald-500/5 border border-emerald-500/20 rounded">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-2 shrink-0"/>
                      <span className="text-[9px] font-bold uppercase tracking-tight">Proof Generated. Ready for Settlement.</span>
                    </div>
                  ) : (
                    <div className="flex items-center text-red-400 mt-2 py-1 px-2 bg-red-500/5 border border-red-500/20 rounded">
                      <AlertTriangle className="w-3.5 h-3.5 mr-2 shrink-0"/>
                      <span className="text-[9px] font-bold uppercase tracking-tight">Consensus Rejected. Hallucination Risk.</span>
                    </div>
                  )}
               </div>
            ) : (
               <span className="text-slate-600 animate-pulse tracking-tight">&gt; Awaiting cross-verification...</span>
            )}
            {/* Terminal Masking Fade */}
            {data.output && (
              <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-black to-transparent pointer-events-none" />
            )}
          </div>
        </div>
      </CardContent>

      <CardFooter className="flex flex-col items-start gap-2 border-t border-slate-800/50 pt-3 pb-3">
         <div className="flex justify-between w-full text-[9px] text-slate-600 font-mono uppercase tracking-widest">
           <span>Model: {data.primaryModel || "Groq Llama-3"}</span>
           {data.latency && <span className="text-emerald-500/70">{data.latency}ms</span>}
         </div>
      </CardFooter>

      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-slate-800 border-2 border-emerald-500 rounded-sm"
      />
    </Card>
  );
});

CollectorNode.displayName = "CollectorNode";
