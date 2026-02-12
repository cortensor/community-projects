'use client';

import Link from 'next/link';
import { ArrowRight, Cpu, Layers, Zap, ShieldCheck, Network, Terminal, Activity, Code, Globe } from 'lucide-react';

export default function LandingPage() {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-background text-text-main font-sans selection:bg-primary/30">
      
      {/* Background Ambience */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#222_1px,transparent_1px),linear-gradient(to_bottom,#222_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-[0.15] pointer-events-none" />
      
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-tr from-primary to-accent rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.5)]">
              <Network className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold tracking-tight text-lg">Fractal Swarm</span>
          </div>
          
          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-text-muted">
            <button onClick={() => scrollToSection('architecture')} className="hover:text-primary transition-colors">Architecture</button>
            <button onClick={() => scrollToSection('protocol')} className="hover:text-primary transition-colors">x402 Protocol</button>
            <button onClick={() => scrollToSection('network')} className="hover:text-primary transition-colors">Network</button>
          </div>

          <Link href="/dashboard" className="bg-white text-black px-5 py-2 rounded-full text-sm font-bold hover:bg-gray-200 transition-all flex items-center gap-2 shadow-lg hover:shadow-white/25">
            Launch Console <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative pt-32 pb-20 px-6 max-w-7xl mx-auto flex flex-col items-center text-center z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/10 text-primary text-xs font-mono mb-8 animate-fade-in">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          MAINNET BETA LIVE
        </div>

        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-white/40 max-w-4xl mx-auto animate-fade-in">
          Orchestrate AI Swarms <br /> at Planetary Scale
        </h1>
        
        <p className="text-xl text-text-muted max-w-2xl mb-10 leading-relaxed animate-fade-in [animation-delay:200ms]">
          Don't rely on a single model. Deploy fractal swarms that split tasks, 
          debate outcomes, and reach consensus. Powered by the x402 micropayment protocol.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center animate-fade-in [animation-delay:400ms]">
          <Link href="/dashboard" className="h-14 px-8 rounded-xl bg-primary hover:bg-primary-dim text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-[0_0_40px_-10px_rgba(59,130,246,0.6)]">
            <Zap className="w-5 h-5" /> Deploy Agent Swarm
          </Link>
          <button onClick={() => scrollToSection('protocol')} className="h-14 px-8 rounded-xl border border-border bg-surface hover:bg-surface-hover text-text-main font-semibold flex items-center justify-center gap-2 transition-all">
            <Code className="w-5 h-5 text-text-muted" /> Read Protocol Docs
          </button>
        </div>

        {/* Hero Visual / Dashboard Preview */}
        <div className="mt-24 w-full max-w-6xl rounded-xl border border-white/10 bg-surface/50 p-2 shadow-2xl relative overflow-hidden group animate-fade-in [animation-delay:600ms]">
          <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent z-10" />
          <div className="aspect-[21/9] bg-[#030303] rounded-lg overflow-hidden relative flex flex-col items-center justify-center border border-white/5">
             <div className="absolute top-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background"></div>
             {/* Fake UI Elements */}
             <div className="z-20 text-center space-y-4">
               <div className="flex items-center justify-center gap-8 mb-8 opacity-50">
                 <div className="w-24 h-24 border border-primary/30 rounded-full flex items-center justify-center animate-pulse-slow">
                    <Cpu className="w-10 h-10 text-primary" />
                 </div>
                 <ArrowRight className="text-text-muted" />
                 <div className="flex gap-4">
                   {[1,2,3].map(i => (
                     <div key={i} className="w-16 h-16 border border-accent/30 bg-accent/5 rounded-lg flex items-center justify-center">
                       <Network className="w-6 h-6 text-accent" />
                     </div>
                   ))}
                 </div>
               </div>
               <div className="font-mono text-sm text-primary bg-primary/10 px-4 py-2 rounded">
                  ORCHESTRATOR: TASK_SPLIT_COMPLETE (3 SUBTASKS)
               </div>
             </div>
          </div>
        </div>
      </main>

      {/* Metrics Strip */}
      <div className="border-y border-white/5 bg-white/[0.02]">
        <div className="max-w-7xl mx-auto px-6 py-8 flex flex-wrap justify-between gap-8">
            <MetricItem label="Active Agents" value="12,405" icon={<Activity className="w-4 h-4 text-success" />} />
            <MetricItem label="Daily Inference" value="1.2M ops" icon={<Cpu className="w-4 h-4 text-primary" />} />
            <MetricItem label="Avg Consensus Time" value="450ms" icon={<Zap className="w-4 h-4 text-warning" />} />
            <MetricItem label="x402 Volume" value="$42.5k" icon={<ShieldCheck className="w-4 h-4 text-accent" />} />
        </div>
      </div>

      {/* Architecture Section */}
      <section id="architecture" className="py-24 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">Fractal Architecture</h2>
          <p className="text-text-muted max-w-2xl mx-auto">
            A modular system designed for reliability. The orchestrator manages lifecycle, 
            while swarms execute logic in parallel.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard 
            icon={<Layers className="w-8 h-8 text-primary" />}
            title="Fractal Task Splitting"
            desc="The Orchestrator recursively breaks high-level objectives into atomic subtasks distributed across N-agents. Complex problems become simple parallel executions."
          />
          <FeatureCard 
            icon={<ShieldCheck className="w-8 h-8 text-accent" />}
            title="Consensus Scoring"
            desc="We don't trust single outputs. Results are validated via a weighted scoring engine: (Confidence * Weight) + (Speed * Weight) + (Reliability * Weight)."
          />
          <FeatureCard 
            icon={<Cpu className="w-8 h-8 text-success" />}
            title="x402 Micropayments"
            desc="Automated settlement layer. Agents are rewarded instantly via mock-ledger tokens based on performance scores, incentivizing high-quality inference."
          />
        </div>
      </section>

      {/* Protocol / Terminal Section */}
      <section id="protocol" className="py-24 bg-surface/30 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded text-accent text-xs font-mono mb-6 bg-accent/10 border border-accent/20">
              <Terminal className="w-3 h-3" />
              PROTOCOL LEVEL
            </div>
            <h2 className="text-3xl md:text-4xl font-bold mb-6">The x402 Payment Standard</h2>
            <div className="space-y-6 text-text-muted">
              <p>
                Traditional AI APIs are black boxes. Fractal Swarms introduce <strong>Proof of Inference</strong>. 
                Agents must provide cryptographic proof of their work to release funds from the escrow smart contract.
              </p>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <div className="mt-1 w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <div className="w-2 h-2 rounded-full bg-primary" />
                  </div>
                  <span>Atomic Settlements per sub-task</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="mt-1 w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <div className="w-2 h-2 rounded-full bg-primary" />
                  </div>
                  <span>Reputation-weighted staking for agents</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="mt-1 w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <div className="w-2 h-2 rounded-full bg-primary" />
                  </div>
                  <span>Transparent ledger history (Immutable)</span>
                </li>
              </ul>
            </div>
            <div className="mt-8">
              <Link href="/dashboard" className="text-primary hover:text-primary-dim font-medium flex items-center gap-2">
                View Live Ledger <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          {/* Code Block Visual */}
          <div className="rounded-xl bg-[#0a0a0a] border border-white/10 p-6 font-mono text-xs shadow-2xl relative overflow-hidden">
             <div className="absolute top-0 left-0 w-full h-8 bg-white/5 border-b border-white/5 flex items-center px-4 gap-2">
               <div className="w-3 h-3 rounded-full bg-red-500/20"></div>
               <div className="w-3 h-3 rounded-full bg-yellow-500/20"></div>
               <div className="w-3 h-3 rounded-full bg-green-500/20"></div>
               <span className="ml-2 text-text-dim">x402-ledger.json</span>
             </div>
             <div className="mt-8 space-y-2">
               <div className="flex">
                 <span className="text-text-dim w-8">1</span>
                 <span className="text-accent">transaction</span> <span className="text-white">{`{`}</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">2</span>
                 <span className="pl-4 text-primary">"id"</span><span className="text-white">:</span> <span className="text-green-400">"tx_99a8b1c..."</span><span className="text-white">,</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">3</span>
                 <span className="pl-4 text-primary">"agent_id"</span><span className="text-white">:</span> <span className="text-green-400">"swarm_alpha_01"</span><span className="text-white">,</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">4</span>
                 <span className="pl-4 text-primary">"task_hash"</span><span className="text-white">:</span> <span className="text-green-400">"0x7f3..."</span><span className="text-white">,</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">5</span>
                 <span className="pl-4 text-primary">"score"</span><span className="text-white">:</span> <span className="text-warning">0.985</span><span className="text-white">,</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">6</span>
                 <span className="pl-4 text-primary">"payout"</span><span className="text-white">:</span> <span className="text-white">{`{`}</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">7</span>
                 <span className="pl-8 text-primary">"amount"</span><span className="text-white">:</span> <span className="text-warning">450</span><span className="text-white">,</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">8</span>
                 <span className="pl-8 text-primary">"token"</span><span className="text-white">:</span> <span className="text-green-400">"X402"</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">9</span>
                 <span className="pl-4 text-white">{`}`}</span>
               </div>
               <div className="flex">
                 <span className="text-text-dim w-8">10</span>
                 <span className="text-white">{`}`}</span>
               </div>
             </div>
          </div>
        </div>
      </section>

      {/* Network / Global Map Placeholder */}
      <section id="network" className="py-24 text-center">
         <div className="max-w-4xl mx-auto px-6">
            <Globe className="w-12 h-12 text-primary mx-auto mb-6 opacity-80" />
            <h2 className="text-3xl font-bold mb-4">Global Node Distribution</h2>
            <p className="text-text-muted mb-12">
              Our swarms are running on decentralized edge compute across 12 regions.
              Low latency. High availability. Zero downtime.
            </p>
            
            {/* Simple Grid Graphic */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               {['USE-1', 'USW-2', 'EU-CENTRAL', 'ASIA-EAST', 'SA-EAST', 'AF-NORTH', 'OC-SOUTH', 'EU-WEST'].map((region) => (
                 <div key={region} className="p-4 border border-white/5 bg-surface rounded flex items-center justify-between group hover:border-primary/50 transition-colors">
                    <span className="font-mono text-sm text-text-muted group-hover:text-white transition-colors">{region}</span>
                    <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                 </div>
               ))}
            </div>
         </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-black py-12">
        <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-4 gap-8 text-sm">
          <div className="col-span-2">
            <div className="flex items-center gap-2 mb-4">
               <div className="w-6 h-6 bg-primary/20 flex items-center justify-center rounded">
                 <Network className="w-4 h-4 text-primary" />
               </div>
               <span className="font-bold text-lg">Fractal Swarm</span>
            </div>
            <p className="text-text-muted max-w-xs">
              Next-generation AI orchestration powered by cryptographic proofs and micropayments.
            </p>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-white">Platform</h4>
            <ul className="space-y-2 text-text-muted">
              <li><Link href="/dashboard" className="hover:text-primary">Dashboard</Link></li>
              <li><a href="#" className="hover:text-primary">Documentation</a></li>
              <li><a href="#" className="hover:text-primary">API Status</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-white">Legal</h4>
            <ul className="space-y-2 text-text-muted">
              <li><a href="#" className="hover:text-primary">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-primary">Terms of Service</a></li>
            </ul>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 mt-12 pt-8 border-t border-white/5 text-center text-text-dim text-xs">
          © 2026 Fractal Systems Inc. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) {
  return (
    <div className="p-8 rounded-2xl border border-white/5 bg-surface/50 hover:bg-surface-hover hover:border-primary/20 transition-all duration-300 group">
      <div className="mb-6 p-4 bg-white/5 w-fit rounded-xl group-hover:scale-110 transition-transform duration-300 shadow-inner shadow-white/5">{icon}</div>
      <h3 className="text-xl font-bold mb-3 text-text-main">{title}</h3>
      <p className="text-text-muted leading-relaxed">{desc}</p>
    </div>
  );
}

function MetricItem({ label, value, icon }: { label: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4">
      <div className="p-2 bg-white/5 rounded-lg">{icon}</div>
      <div>
        <div className="text-2xl font-bold font-mono tracking-tight">{value}</div>
        <div className="text-xs text-text-muted uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}