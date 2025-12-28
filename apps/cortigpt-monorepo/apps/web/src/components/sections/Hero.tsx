"use client";

import { Button } from "@/components/ui/button";
import { ArrowRight, Play } from "lucide-react";
import Link from "next/link";
// Hero image is now referenced directly from the public folder

export const Hero = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden neural-bg pt-32 lg:pt-40">

      {/* Clean modern overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-background/70 via-background/30 to-background/80 backdrop-blur-sm" />

      {/* Minimal particles for subtle effect */}
      <div className="particles">
        {Array.from({ length: 8 }, (_, i) => (
          <div
            key={i}
            className="particle"
            style={{
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 6}s`,
              animationDuration: `${8 + Math.random() * 4}s`,
              opacity: 0.3,
            }}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative z-10 text-center max-w-7xl mx-auto px-4 sm:px-6 flex flex-col justify-center min-h-[calc(100vh-8rem)] lg:min-h-[calc(100vh-10rem)]">
        <div className="animate-fade-in">
          {/* Main Content Area */}
          <div className="mb-8 sm:mb-12 lg:mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-futura font-black mb-4 sm:mb-6 lg:mb-8 leading-tight">
              <span className="gradient-text block mb-2 text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl">CortiGPT</span>
              <span className="text-white block mb-2 text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl">The Decentralized</span>
              <span className="text-primary-glow block text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl">Perplexity</span>
            </h1>

            <p className="text-sm sm:text-base md:text-lg lg:text-xl xl:text-2xl text-muted-foreground mb-8 sm:mb-10 lg:mb-12 max-w-5xl mx-auto leading-relaxed font-tech px-4">
              When <span className="text-secondary">Perplexity meets Decentralization</span> - 
              Experience the future of AI-powered search with{" "}
              <span className="text-accent">verifiable, trustless intelligence</span>.
            </p>
          </div>

          {/* Buttons - Better responsive layout */}
          <div className="flex flex-col gap-3 sm:gap-4 justify-center items-center animate-slide-up px-4 mb-8 sm:mb-12 lg:mb-16">
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 lg:gap-6 w-full max-w-sm sm:max-w-lg lg:max-w-xl justify-center">
              <Link href="/choose-mode">
                <Button variant="hero" size="default" className="w-full sm:w-auto sm:px-6 lg:px-8 group text-sm sm:text-base">
                  Explore CortiGPT
                  <ArrowRight className="ml-2 h-3 w-3 sm:h-4 sm:w-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>


            </div>
          </div>

          {/* Enhanced Stats with glass morphism */}
          <div className="hidden sm:grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 lg:gap-8 max-w-4xl mx-auto px-4">
            <div className="glass p-4 sm:p-6 rounded-xl text-center animate-float border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent backdrop-blur-md">
              <div className="text-2xl sm:text-3xl font-bold text-primary mb-2 drop-shadow-lg">∞</div>
              <div className="text-sm sm:text-base text-muted-foreground font-tech">AI Queries Processed</div>
            </div>
            <div className="glass p-4 sm:p-6 rounded-xl text-center animate-float border border-secondary/20 bg-gradient-to-br from-secondary/5 to-transparent backdrop-blur-md" style={{ animationDelay: "0.5s" }}>
              <div className="text-2xl sm:text-3xl font-bold text-secondary mb-2 drop-shadow-lg">100%</div>
              <div className="text-sm sm:text-base text-muted-foreground font-tech">Verifiable Results</div>
            </div>
            <div className="glass p-4 sm:p-6 rounded-xl text-center animate-float border border-accent/20 bg-gradient-to-br from-accent/5 to-transparent backdrop-blur-md" style={{ animationDelay: "1s" }}>
              <div className="text-2xl sm:text-3xl font-bold text-accent mb-2 drop-shadow-lg">∞</div>
              <div className="text-sm sm:text-base text-muted-foreground font-tech">Decentralized Miners</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};