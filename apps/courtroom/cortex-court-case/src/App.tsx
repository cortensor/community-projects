import '@rainbow-me/rainbowkit/styles.css';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider, lightTheme } from '@rainbow-me/rainbowkit';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { config } from "./config/wagmi";
import { NetworkSwitcher } from "./components/NetworkSwitcher";
import { ConnectionMonitor } from "./components/ConnectionMonitor";
import Index from "./pages/Index";
import Courtroom from "./pages/Courtroom";
import Cases from "./pages/Cases";
import Validators from "./pages/Validators";
import Docs from "./pages/Docs";
import CaseDetail from "./pages/CaseDetail"; 
import NotFound from "./pages/NotFound";
import TestConnection from "./pages/TestConnection";

const queryClient = new QueryClient();

const App = () => (
  <WagmiProvider config={config}>
    <QueryClientProvider client={queryClient}>
      <RainbowKitProvider
        theme={lightTheme({
          accentColor: '#3b82f6',
          accentColorForeground: 'white',
          borderRadius: 'medium',
          fontStack: 'system',
        })}
      >
        <TooltipProvider>
          <ConnectionMonitor />
          <NetworkSwitcher />
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/courtroom" element={<Courtroom />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:id" element={<CaseDetail />} />
              <Route path="/validators" element={<Validators />} />
              <Route path="/docs" element={<Docs />} />
              <Route path="/test" element={<TestConnection />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </RainbowKitProvider>
    </QueryClientProvider>
  </WagmiProvider>
);

export default App;