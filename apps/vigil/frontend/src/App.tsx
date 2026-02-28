import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Analytics } from '@vercel/analytics/react';
import { Toaster } from 'react-hot-toast';
import { DashboardContent, IncidentsContent, IncidentDetailContent } from './components/Dashboard';

const navLinks = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/incidents', label: 'Incidents', icon: '🚨' },
  { path: '/about', label: 'About', icon: '📖' },
];

function Navigation() {
  const location = useLocation();

  return (
    <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-7xl">
      <div className="glass rounded-2xl px-6 py-4 border border-app-border shadow-floating flex items-center justify-between">
        <Link to="/" className="flex items-center group">
          <span className="font-serif font-bold text-2xl tracking-tighter text-text-main group-hover:text-accent-indigo transition-colors duration-300">
            Vigil
          </span>
        </Link>

        <div className="flex items-center gap-2">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-accent-indigo text-white shadow-premium'
                    : 'text-text-dim hover:text-accent-indigo hover:bg-app-hover'
                }`}
              >
                {link.icon} {link.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<PageWrapper><Dashboard /></PageWrapper>} />
        <Route path="/incidents" element={<PageWrapper><Incidents /></PageWrapper>} />
        <Route path="/incidents/:id" element={<PageWrapper><IncidentDetail /></PageWrapper>} />
        <Route path="/about" element={<PageWrapper><About /></PageWrapper>} />
      </Routes>
    </AnimatePresence>
  );
}

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -15 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="pt-44 pb-24 px-6 min-h-screen"
    >
      <div className="max-w-7xl mx-auto">
        {children}
      </div>
    </motion.div>
  );
}

function LandingPage() {
  return (
    <div className="pt-32 pb-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-20"
        >
          <h1 className="font-serif font-bold text-6xl md:text-7xl tracking-tighter text-text-main mb-6">
            Autonomous Incident
            <br />
            <span className="italic text-accent-indigo">Response Agent</span>
          </h1>
          <p className="text-xl text-text-dim max-w-2xl mx-auto mb-10">
            Monitor Cortensor network health, detect anomalies with multi-model validation, and respond automatically with full audit trails.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-4 bg-accent-indigo text-white rounded-xl font-medium hover:shadow-premium transition-all"
          >
            View Dashboard →
          </Link>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: '📡', title: 'Real-time Monitoring', desc: 'Track router health, latency, error rates, and validator scores' },
            { icon: '🤖', title: 'Multi-Model Detection', desc: 'Cortensor PoI validates anomalies across 3+ models' },
            { icon: '⚡', title: 'Automated Response', desc: 'GitHub issues, Discord alerts, and complete evidence bundles' }
          ].map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="glass rounded-2xl p-8 border border-app-border"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="font-bold text-xl mb-2">{feature.title}</h3>
              <p className="text-text-dim">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  return <DashboardContent />;
}

function Incidents() {
  return <IncidentsContent />;
}

function IncidentDetail() {
  return <IncidentDetailContent />;
}

function About() {
  return (
    <div className="glass rounded-2xl p-8 border border-app-border">
      <h2 className="font-serif font-bold text-3xl mb-6">About Vigil</h2>
      
      <div className="space-y-6 text-text-dim">
        <div>
          <h3 className="font-bold text-xl text-text-main mb-2">🎯 Mission</h3>
          <p>
            Autonomous agent that monitors Cortensor network health, detects anomalies using multi-model 
            validation (PoI), and automatically responds to incidents with full audit trails.
          </p>
        </div>

        <div>
          <h3 className="font-bold text-xl text-text-main mb-2">🏗️ Architecture</h3>
          <p className="mb-3">The agent follows a complete workflow loop:</p>
          <ol className="list-decimal list-inside space-y-2 ml-4">
            <li><strong>Monitor:</strong> Continuously track router health metrics</li>
            <li><strong>Detect:</strong> Identify anomalies using threshold-based detection</li>
            <li><strong>Analyze:</strong> Validate with Cortensor PoI across 3+ models</li>
            <li><strong>Act:</strong> Execute automated responses (GitHub issues, Discord alerts)</li>
            <li><strong>Report:</strong> Generate complete evidence bundles with audit trails</li>
          </ol>
        </div>

        <div>
          <h3 className="font-bold text-xl text-text-main mb-2">🔒 Safety Features</h3>
          <ul className="list-disc list-inside space-y-2 ml-4">
            <li>Read-only monitoring by default</li>
            <li>Rate limiting (max 1 action per incident type per 5 minutes)</li>
            <li>Multi-model consensus required for action</li>
            <li>Complete audit trails with Cortensor session IDs</li>
            <li>Dry-run mode for testing</li>
          </ul>
        </div>

        <div>
          <h3 className="font-bold text-xl text-text-main mb-2">🤖 Cortensor Integration</h3>
          <ul className="list-disc list-inside space-y-2 ml-4">
            <li><strong>PoI (Proof of Inference):</strong> Runs anomaly detection across 3 models, compares outputs</li>
            <li><strong>PoUW (Proof of Useful Work):</strong> Uses validator scores to weight detection confidence</li>
            <li><strong>Session Management:</strong> Maintains persistent sessions, stores all session IDs</li>
            <li><strong>Evidence Trails:</strong> Complete audit logs with request/response pairs</li>
          </ul>
        </div>

        <div>
          <h3 className="font-bold text-xl text-text-main mb-2">📦 Open Source</h3>
          <p>
            This project is open source under the MIT license. Deploy it for your own Cortensor project 
            or contribute improvements on GitHub.
          </p>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Analytics />
      <Toaster position="top-right" />
      <div className="min-h-screen bg-app-bg grid-subtle selection:bg-accent-indigo/10 selection:text-accent-indigo">
        <Navigation />
        <main className="relative">
          <AnimatedRoutes />
        </main>

        <footer className="border-t border-app-border py-16 px-6 bg-white">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-10">
            <div className="flex flex-col items-center md:items-start gap-5">
              <span className="font-serif font-bold text-2xl tracking-tighter text-text-main">
                Vigil
              </span>
              <p className="text-sm text-text-pale max-w-xs text-center md:text-left leading-relaxed">
                Autonomous incident response for Cortensor network
              </p>
            </div>

            <div className="flex flex-col items-center md:items-end gap-4">
              <p className="text-xs text-text-pale uppercase tracking-widest font-medium">
                © 2026 CORTENSOR HACKATHON #4
              </p>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
