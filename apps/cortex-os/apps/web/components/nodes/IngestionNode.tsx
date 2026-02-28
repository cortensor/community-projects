"use client";

import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { Database, Activity, Maximize2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const IngestionNode = memo(({ data }: any) => {
  const onExpand = data.onOpenDetail;
  
  return (
    <Card className={`w-[350px] border-slate-700 bg-slate-900/95 shadow-xl backdrop-blur-md transition-all duration-500 hover:shadow-blue-500/10 hover:border-blue-500/30 ${data.status === 'RUNNING' || data.status === 'PENDING' ? 'shadow-blue-500/20 border-blue-500/50 scale-[1.02]' : 'shadow-blue-900/5'}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-mono text-blue-400 flex items-center gap-2">
          <div className="p-1 rounded bg-blue-500/10">
            <Database className="w-3.5 h-3.5" />
          </div>
          [NODE: INGESTION]
        </CardTitle>
        <Badge variant="outline" className="border-blue-500/30 text-[10px] text-blue-400 font-mono tracking-tighter">
          <Activity className="w-2.5 h-2.5 mr-1 animate-pulse" />
          {data.status || "IDLE"}
        </Badge>
      </CardHeader>
      
      <CardContent className="space-y-4 pt-2">
        <div>
          <div className="text-[10px] text-slate-500 font-mono mb-1.5 uppercase tracking-widest">Target Resolution</div>
          <div className="text-[11px] bg-black/30 p-2 rounded border border-slate-800/50 text-emerald-400 font-mono break-all leading-tight">
            {data.target || "Awaiting target address..."}
          </div>
        </div>

        <div className="relative group/term">
          <div className="flex justify-between items-center mb-1">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Direct Context</div>
            {data.output && (
              <button 
                onClick={() => onExpand?.('Ingestion Results', String(data.output), 'ingestion')}
                className="text-slate-500 hover:text-blue-400 transition-colors p-1"
                title="Expand View"
              >
                <Maximize2 className="w-3 h-3" />
              </button>
            )}
          </div>
          
          <div className="relative bg-black/60 p-3 rounded text-[10px] font-mono text-slate-400 h-[100px] border border-slate-800/80 overflow-hidden leading-relaxed">
            {data.output ? (
              <span className="text-emerald-500/80">&gt; {data.output}</span>
            ) : (
              <span className="text-slate-600 animate-pulse">&gt; Initializing probe...</span>
            )}
            {/* Terminal Masking Fade */}
            {data.output && (
              <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />
            )}
          </div>
        </div>
      </CardContent>

      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-slate-800 border-2 border-blue-500 rounded-sm"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-blue-500 border-2 border-slate-800 rounded-sm"
      />
    </Card>
  );
});

IngestionNode.displayName = "IngestionNode";
