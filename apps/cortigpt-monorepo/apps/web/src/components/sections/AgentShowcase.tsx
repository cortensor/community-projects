"use client";
import { Button } from "@/components/ui/button";
import { ArrowRight, Globe, Search, Shield, Chrome, Zap, MessageSquare } from "lucide-react";
import Link from "next/link";
// Images are now referenced directly from the public folder

const capabilities = [
  {
    name: "Smart Web Analysis",
    description: "Instantly analyze and explain content on any webpage with decentralized AI verification",
    icon: Globe,
    image: "/agent-chat-neon.jpg",
    color: "primary",
    features: ["Text selection analysis", "Page content understanding", "Real-time explanations", "Context-aware responses"]
  },
  {
    name: "Decentralized Search",
    description: "Search the internet with blockchain-verified results and consensus-based accuracy",
    icon: Search,
    image: "/agent-truth.jpg",
    color: "secondary",
    features: ["Multi-node consensus", "Verified search results", "Fact-checking integration", "Source validation"]
  },
  {
    name: "Chrome Extension Power",
    description: "Seamless browser integration with sidepanel interface for instant AI assistance",
    icon: Chrome,
    image: "/agent-tweets-neon.jpg",
    color: "accent",
    features: ["One-click activation", "Tab-aware context", "Persistent chat history", "Cross-site continuity"]
  }
];

export const AgentShowcase = () => {
  return (
    <section className="py-16 sm:py-24 lg:py-32 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12 sm:mb-16 lg:mb-20 animate-fade-in">
          <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-futura font-bold mb-4 sm:mb-6">
            Meet <span className="gradient-text text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl">CortiGPT</span>
          </h2>
          <p className="text-base sm:text-lg lg:text-xl text-muted-foreground max-w-3xl mx-auto font-tech px-4">
            The decentralized Perplexity. Verifiable AI powered by blockchain consensus.
          </p>
        </div>

        {/* Capability Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8 mb-12 sm:mb-16">
          {capabilities.map((capability, index) => (
            <div
              key={capability.name}
              className="group glass p-6 sm:p-8 rounded-2xl transition-all duration-slow animate-slide-up"
              style={{ animationDelay: `${index * 0.2}s` }}
            >
              {/* Capability Image */}
              <div className="relative mb-4 sm:mb-6 overflow-hidden rounded-xl">
                <img
                  src={capability.image}
                  alt={capability.name}
                  className="w-full h-40 sm:h-48 object-cover transition-transform duration-slow"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent" />
                <div className={`absolute top-3 right-3 sm:top-4 sm:right-4 p-2 sm:p-3 rounded-full glass border-${capability.color}/30`}>
                  <capability.icon className={`h-5 w-5 sm:h-6 sm:w-6 text-${capability.color}`} />
                </div>
              </div>

              {/* Capability Info */}
              <h3 className={`text-xl sm:text-2xl font-futura font-bold mb-3 sm:mb-4 text-${capability.color}`}>
                {capability.name}
              </h3>
              <p className="text-sm sm:text-base text-muted-foreground mb-4 sm:mb-6 font-tech leading-relaxed">
                {capability.description}
              </p>

              {/* Features */}
              <ul className="space-y-2 mb-6 sm:mb-8">
                {capability.features.map((feature) => (
                  <li key={feature} className="flex items-center text-xs sm:text-sm font-tech">
                    <div className={`w-2 h-2 rounded-full bg-${capability.color} mr-3 flex-shrink-0`} />
                    {feature}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <Button variant="neural" className="w-full group">
                Try {capability.name}
                <ArrowRight className="ml-2 h-3 w-3 sm:h-4 sm:w-4 transition-transform" />
              </Button>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center animate-fade-in px-4">
          <div className="mb-6">
            <p className="text-sm sm:text-base text-muted-foreground mb-4 font-tech">
              Everything is <span className="text-primary font-semibold">100% decentralized</span> - no central servers, no single points of failure
            </p>
            <p className="text-xs sm:text-sm text-muted-foreground/80 font-tech">
              Powered by blockchain consensus • Verified by multiple AI nodes • Transparent and trustless
            </p>
          </div>
          <Link href="/extension-install">
            <Button variant="hero" size="lg" className="w-full sm:w-auto group">
              Install Chrome Extension
              <Chrome className="ml-2 h-4 w-4 sm:h-5 sm:w-5 transition-transform" />
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
};