import { CortexFlow } from "@/components/canvas/CortexFlow";
import { ConnectButton } from "@rainbow-me/rainbowkit";

export default function Dashboard() {
  return (
    <main className="min-h-screen bg-black text-slate-50 font-sans selection:bg-emerald-500/30">
      
      {/* Top Navigation Bar */}
      <nav className="fixed top-0 w-full h-16 border-b border-white/5 bg-black/50 backdrop-blur-md z-50 flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <img src="/Cortex_OS.png" alt="Cortex.OS" className="w-11 h-11 object-contain drop-shadow-[0_0_20px_rgba(16,185,129,0.7)]" />
          <h1 className="font-mono font-bold tracking-widest text-sm">CORTEX<span className="text-emerald-500">.OS</span></h1>
          <div className="h-4 w-px bg-slate-800 mx-2" />
          <span className="text-xs font-mono text-slate-500 hidden md:inline">VERIFIABLE INTELLIGENCE ENGINE</span>
        </div>
        
        <div className="flex items-center gap-4">
           {/* Web3 Native Connection */}
           <ConnectButton showBalance={false} />
        </div>
      </nav>

      <div className="pt-24 px-6 pb-24 min-h-screen flex flex-col">
        {/* Header Controls */}
        <header className="mb-6 shrink-0">
          <h2 className="text-3xl font-bold tracking-tight mb-2">DeGen Risk Auditor</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Fractal reasoning workspace. Executes multi-agent consensus to generate a deterministic, cryptographically proven smart contract vulnerability report.
          </p>
        </header>

        {/* Dynamic Canvas Container */}
        <div className="w-full rounded-2xl border border-white/10 relative bg-slate-950/50 h-[750px] shadow-inner">
          <CortexFlow />
        </div>
      </div>
    </main>
  );
}
