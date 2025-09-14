"use client";

import { Button } from "@/components/ui/button";
import { ArrowRight, Vote, BarChart3, AlertTriangle, Globe } from "lucide-react";

const useCases = [
  {
    icon: Vote,
    title: "DAO Proposal Verification",
    description: "Verify claims and statements in governance proposals with multi-miner consensus",
    color: "primary",
    tags: ["Governance", "Web3", "DAOs"]
  },
  {
    icon: BarChart3,
    title: "Fact-Checking Dashboards",
    description: "Real-time verification dashboards for news outlets and content platforms",
    color: "secondary",
    tags: ["Media", "Journalism", "Analytics"]
  },
  {
    icon: AlertTriangle,
    title: "Misinformation Detection",
    description: "Automated detection and verification of false claims on social media",
    color: "accent",
    tags: ["Social Media", "Safety", "AI"]
  },
  {
    icon: Globe,
    title: "Web3-Integrated Truth Boxes",
    description: "Embeddable verification widgets for dApps and Web3 applications",
    color: "primary",
    tags: ["Integration", "dApps", "Widgets"]
  }
];

export const UseCases = () => {
  return (
    <section className="py-16 sm:py-24 lg:py-32 px-4 sm:px-6 neural-bg">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12 sm:mb-16 lg:mb-20 animate-fade-in">
          <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-futura font-bold mb-4 sm:mb-6">
            Use Cases <span className="gradient-text text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl">in the Wild</span>
          </h2>
          <p className="text-base sm:text-lg lg:text-xl text-muted-foreground max-w-3xl mx-auto font-tech px-4">
            Real-world applications of verifiable AI across industries
          </p>
        </div>

        {/* Use Cases Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 mb-12 sm:mb-16">
          {useCases.map((useCase, index) => (
            <div
              key={useCase.title}
              className="group glass p-6 sm:p-8 rounded-2xl transition-all duration-slow animate-slide-up"
              style={{ animationDelay: `${index * 0.15}s` }}
            >
              {/* Icon */}
              <div className={`inline-flex items-center justify-center w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-${useCase.color}/20 border border-${useCase.color}/30 mb-4 sm:mb-6`}>
                <useCase.icon className={`h-6 w-6 sm:h-8 sm:w-8 text-${useCase.color}`} />
              </div>

              {/* Title */}
              <h3 className="text-xl sm:text-2xl font-futura font-bold mb-3 sm:mb-4 text-white transition-colors">
                {useCase.title}
              </h3>

              {/* Description */}
              <p className="text-sm sm:text-base text-muted-foreground mb-4 sm:mb-6 font-tech leading-relaxed">
                {useCase.description}
              </p>

              {/* Tags */}
              <div className="flex flex-wrap gap-2 mb-4 sm:mb-6">
                {useCase.tags.map((tag) => (
                  <span
                    key={tag}
                    className={`px-2 sm:px-3 py-1 text-xs font-tech rounded-full bg-${useCase.color}/20 text-${useCase.color} border border-${useCase.color}/30`}
                  >
                    {tag}
                  </span>
                ))}
              </div>

              {/* Learn More */}
              <Button variant="neural" size="sm" className="w-full sm:w-auto group/btn">
                Learn More
                <ArrowRight className="ml-2 h-3 w-3 sm:h-4 sm:w-4 transition-transform" />
              </Button>
            </div>
          ))}
        </div>

        {/* Call to Action */}
        <div className="text-center px-4">
          <div className="glass p-6 sm:p-8 rounded-2xl max-w-4xl mx-auto animate-fade-in">
            <h3 className="text-2xl sm:text-3xl font-futura font-bold mb-3 sm:mb-4">
              Ready to Build with <span className="gradient-text text-xl sm:text-2xl md:text-3xl lg:text-4xl xl:text-5xl">CortiGPT</span>?
            </h3>
            <p className="text-sm sm:text-base text-muted-foreground mb-6 sm:mb-8 font-tech px-4">
              Integrate verifiable AI into your applications with our comprehensive API and SDK
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button variant="hero" size="lg" className="w-full sm:w-auto group">
                Get API Access
                <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5 transition-transform" />
              </Button>
              <Button variant="neural" size="lg" className="w-full sm:w-auto">
                View Documentation
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};