"use client";

import { useState, useEffect } from "react";
import { NeuralBackground } from "@/components/ui/neural-background";
import { Hero } from "@/components/sections/Hero";
import { AgentShowcase } from "@/components/sections/AgentShowcase";
import { HowItWorksNew } from "@/components/sections/HowItWorksNew";
import { UseCases } from "@/components/sections/UseCases";
import { Footer } from "@/components/sections/Footer";
import Navbar from "@/components/layout/Navbar";
import NewIntroSplash from "@/components/ui/new-intro-splash";

const Index = () => {
  const [showIntro, setShowIntro] = useState(false);

  useEffect(() => {
    // Check if intro has been shown in this session
    // const hasSeenIntro = sessionStorage.getItem('cortigpt-intro-seen');
    const hasSeenIntro = false;
    
    if (!hasSeenIntro) {
      setShowIntro(true);
    }
    
  }, []);

  const handleIntroComplete = () => {
    // Mark intro as seen for this session
    sessionStorage.setItem('cortigpt-intro-seen', 'true');
    setShowIntro(false);
  };

  

  return (
    <>
      {showIntro && <NewIntroSplash onComplete={handleIntroComplete} />}
      <div className="min-h-screen bg-background relative">
        <Navbar />
        <Hero />
        <AgentShowcase />
        <HowItWorksNew />
        <UseCases />
        <Footer />
      </div>
    </>
  );
};

export default Index;