import { Web3Provider } from "@/providers/web3-provider"
import Dashboard from "./components/Dashboard"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner";
import Navbar from "./Navbar";
import SplashScreen from "./components/SplashScreen";
import { useSplashScreen } from "@/hooks/use-splash-screen";

function App() {
  const { showSplash, hideSplash, isLoading } = useSplashScreen();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (showSplash) {
    return <SplashScreen onComplete={hideSplash} />;
  }

  return (
      <Web3Provider>
        <TooltipProvider>
          <Navbar />
          <Dashboard />
          <Toaster
            position="top-right"
            richColors
            closeButton
            theme="dark"
          />
        </TooltipProvider>
      </Web3Provider>
  )
}

export default App
