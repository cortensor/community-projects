"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Play,
  Users,
  Shield,
  Database,
  Link,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Globe,
  Lock,
  Pause
} from "lucide-react";

interface ProcessStep {
  id: number;
  title: string;
  subtitle: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  gradient: string;
  features: string[];
}

const processSteps: ProcessStep[] = [
  {
    id: 1,
    title: "Session Creation",
    subtitle: "Web3 Initialization",
    description: "Ephemeral Web3 session initialized with redundancy parameters and timeout settings via decentralized SDK.",
    icon: Play,
    color: "from-primary to-primary/80",
    gradient: "bg-gradient-to-br from-primary/20 to-primary/10",
    features: ["Web3 SDK Integration", "Redundancy Parameters", "Timeout Configuration"]
  },
  {
    id: 2,
    title: "Task Distribution",
    subtitle: "Decentralized Network",
    description: "Query distributed to specialized miner network via TaskQueued events for parallel processing across nodes.",
    icon: Users,
    color: "from-secondary to-secondary/80",
    gradient: "bg-gradient-to-br from-secondary/20 to-secondary/10",
    features: ["P2P Network", "TaskQueued Events", "Parallel Processing"]
  },
  {
    id: 3,
    title: "Multi-Miner Consensus",
    subtitle: "Trustless Verification",
    description: "Deterministic aggregation with confidence scoring, clustering, and majority consensus algorithms.",
    icon: Shield,
    color: "from-accent to-accent/80",
    gradient: "bg-gradient-to-br from-accent/20 to-accent/10",
    features: ["Consensus Algorithm", "Confidence Scoring", "Result Clustering"]
  },
  {
    id: 4,
    title: "IPFS Receipt",
    subtitle: "Immutable Storage",
    description: "Cryptographic proof with miner outputs and confidence scores stored immutably on IPFS network.",
    icon: Database,
    color: "from-primary to-secondary",
    gradient: "bg-gradient-to-br from-primary/15 to-secondary/15",
    features: ["IPFS Storage", "Cryptographic Proof", "Audit Trail"]
  },
  {
    id: 5,
    title: "On-Chain Anchoring",
    subtitle: "Blockchain Registry",
    description: "Optional blockchain registry for maximum trust and public auditability with verifier SDK integration.",
    icon: Link,
    color: "from-secondary to-accent",
    gradient: "bg-gradient-to-br from-secondary/15 to-accent/15",
    features: ["Blockchain Registry", "Public Auditability", "Verifier SDK"]
  }
];

export const HowItWorksNew = () => {
  const [activeStep, setActiveStep] = useState(1);
  const [hoveredStep, setHoveredStep] = useState<number | null>(null);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const [progress, setProgress] = useState(0);

  const currentStep = processSteps.find(step => step.id === activeStep) || processSteps[0];

  // Auto-progression effect
  useEffect(() => {
    if (!isAutoPlaying) {
      setProgress(0);
      return;
    }

    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          return 0;
        }
        return prev + (100 / 40); // 4000ms / 100ms = 40 steps
      });
    }, 100);

    const stepInterval = setInterval(() => {
      setActiveStep(prev => {
        const nextStep = prev >= processSteps.length ? 1 : prev + 1;
        return nextStep;
      });
      setProgress(0);
    }, 4000); // Change step every 4 seconds

    return () => {
      clearInterval(progressInterval);
      clearInterval(stepInterval);
    };
  }, [isAutoPlaying]);

  // Pause auto-play on hover
  const handleStepClick = (stepId: number) => {
    setActiveStep(stepId);
    setIsAutoPlaying(false);
    setProgress(0);
    // Resume auto-play after 10 seconds of inactivity
    setTimeout(() => setIsAutoPlaying(true), 10000);
  };

  return (
    <section className="relative py-12 sm:py-16 lg:py-20 xl:py-32 overflow-hidden bg-gradient-to-b from-background via-background/98 to-background">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-64 sm:w-80 lg:w-96 h-64 sm:h-80 lg:h-96 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-64 sm:w-80 lg:w-96 h-64 sm:h-80 lg:h-96 bg-gradient-to-r from-secondary/10 to-accent/10 rounded-full blur-3xl animate-pulse delay-1000" />

        {/* Floating Particles - Reduced for mobile performance */}
        {[...Array(typeof window !== 'undefined' && window.innerWidth < 768 ? 8 : 20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-primary/30 rounded-full hidden sm:block"
            initial={{
              x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1200),
              y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 800),
              opacity: 0
            }}
            animate={{
              y: [null, -30, 30, -15],
              opacity: [0, 1, 0.5, 1, 0],
              scale: [1, 1.5, 1]
            }}
            transition={{
              duration: 4 + Math.random() * 6,
              repeat: Infinity,
              delay: Math.random() * 8,
              ease: 'easeInOut'
            }}
          />
        ))}
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Section */}
        <motion.div
          className="text-center mb-8 sm:mb-12 lg:mb-16 xl:mb-24"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <motion.div
            className="inline-flex items-center gap-2 sm:gap-3 mb-4 sm:mb-6 px-4 sm:px-6 py-2 sm:py-3 rounded-full bg-gradient-to-r from-primary/20 to-secondary/20 border border-primary/30 backdrop-blur-sm"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            >
              <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            </motion.div>
            <span className="text-xs sm:text-sm font-semibold text-primary tracking-wider">DECENTRALIZED AI INFERENCE</span>
            <Sparkles className="h-3 w-3 sm:h-4 sm:w-4 text-secondary" />
          </motion.div>

          <motion.h2
            className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl 2xl:text-7xl font-bold mb-4 sm:mb-6 bg-gradient-to-r from-white via-white to-white/80 bg-clip-text text-transparent"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            How <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl">Cortensor</span> Works
          </motion.h2>

          <motion.p
            className="text-sm sm:text-base lg:text-lg xl:text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed px-4 sm:px-0"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            Experience trustless verification through decentralized consensus with Web3 ownership and complete on-chain auditability
          </motion.p>
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-12 gap-8 lg:gap-12 items-start">
          {/* Step Navigation - Left Side */}
          <motion.div
            className="lg:col-span-5 xl:col-span-4 order-2 lg:order-1"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.8 }}
          >
            <div className="lg:sticky lg:top-8">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 lg:mb-8 gap-4">
                <motion.h3
                  className="text-lg sm:text-xl font-semibold text-white flex items-center gap-3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1 }}
                >
                  <Globe className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                  Process Flow
                </motion.h3>

                <div className="flex flex-row sm:flex-col items-center sm:items-end gap-2">
                  <motion.button
                    onClick={() => setIsAutoPlaying(!isAutoPlaying)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 transition-all duration-300 text-xs sm:text-sm"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {isAutoPlaying ? (
                      <Pause className="h-3 w-3 sm:h-4 sm:w-4 text-white" />
                    ) : (
                      <Play className="h-3 w-3 sm:h-4 sm:w-4 text-primary" />
                    )}
                    <span className="text-xs text-white/80">
                      {isAutoPlaying ? 'Auto' : 'Manual'}
                    </span>
                  </motion.button>

                  {isAutoPlaying && (
                    <div className="w-16 sm:w-20 h-1 bg-white/20 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                        style={{ width: `${progress}%` }}
                        transition={{ duration: 0.1 }}
                      />
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                {processSteps.map((step, index) => (
                  <motion.div
                    key={step.id}
                    className="relative"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 1.2 + index * 0.1 }}
                  >
                    <motion.button
                      onClick={() => handleStepClick(step.id)}
                      onHoverStart={() => setHoveredStep(step.id)}
                      onHoverEnd={() => setHoveredStep(null)}
                      className={`w-full text-left p-3 sm:p-4 rounded-xl border transition-all duration-300 group ${activeStep === step.id
                          ? 'bg-gradient-to-r from-primary/20 to-secondary/20 border-primary/50 shadow-lg shadow-primary/25'
                          : 'bg-background/50 border-white/10 hover:border-white/20 hover:bg-background/70'
                        }`}
                      whileHover={{ scale: 1.02, x: 8 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <div className="flex items-center gap-3 sm:gap-4">
                        <motion.div
                          className={`flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-full border-2 ${activeStep === step.id
                              ? 'bg-primary/20 border-primary text-primary'
                              : 'bg-white/5 border-white/20 text-white/60 group-hover:text-white/80'
                            }`}
                          animate={{
                            scale: activeStep === step.id ? 1.1 : 1,
                            rotate: hoveredStep === step.id ? 5 : 0
                          }}
                        >
                          <step.icon className="h-5 w-5 sm:h-6 sm:w-6" />
                        </motion.div>

                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${activeStep === step.id
                                ? 'bg-primary/20 text-primary'
                                : 'bg-white/10 text-white/60'
                              }`}>
                              STEP {step.id}
                            </span>
                            {activeStep === step.id && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                className="w-2 h-2 bg-primary rounded-full"
                              />
                            )}
                          </div>
                          <h4 className={`text-sm sm:text-base font-semibold transition-colors ${activeStep === step.id ? 'text-white' : 'text-white/80 group-hover:text-white'
                            }`}>
                            {step.title}
                          </h4>
                          <p className={`text-xs sm:text-sm transition-colors ${activeStep === step.id ? 'text-white/80' : 'text-white/60 group-hover:text-white/70'
                            }`}>
                            {step.subtitle}
                          </p>
                        </div>

                        <motion.div
                          animate={{ x: activeStep === step.id ? 4 : 0 }}
                          className={`transition-colors ${activeStep === step.id ? 'text-primary' : 'text-white/40 group-hover:text-white/60'
                            }`}
                        >
                          <ArrowRight className="h-4 w-4" />
                        </motion.div>
                      </div>
                    </motion.button>

                    {/* Connection Line */}
                    {index < processSteps.length - 1 && (
                      <motion.div
                        className="absolute left-8 top-full w-0.5 h-4 bg-gradient-to-b from-primary/50 to-white/20"
                        initial={{ scaleY: 0 }}
                        animate={{ scaleY: 1 }}
                        transition={{ delay: 1.4 + index * 0.1 }}
                      />
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Step Content - Right Side */}
          <motion.div
            className="lg:col-span-7 xl:col-span-8 order-1 lg:order-2"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 1 }}
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={activeStep}
                className="relative"
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -30, scale: 0.95 }}
                transition={{ duration: 0.5, type: "spring", stiffness: 100 }}
              >
                {/* Main Step Card */}
                <div className={`relative p-4 sm:p-6 lg:p-8 xl:p-10 rounded-xl lg:rounded-2xl border backdrop-blur-sm overflow-hidden ${currentStep.gradient
                  } border-white/20 shadow-2xl`}>
                  {/* Background Pattern */}
                  <div className="absolute inset-0 opacity-5">
                    <div className="absolute inset-0" style={{
                      backgroundImage: `radial-gradient(circle at 2px 2px, white 1px, transparent 0)`,
                      backgroundSize: '24px 24px'
                    }} />
                  </div>

                  {/* Floating Icon */}
                  <motion.div
                    className="absolute top-4 right-4 sm:top-6 sm:right-6"
                    animate={{
                      rotate: [0, 10, -10, 0],
                      scale: [1, 1.1, 1]
                    }}
                    transition={{
                      duration: 4,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  >
                    <div className={`p-3 sm:p-4 rounded-full bg-gradient-to-r ${currentStep.color} shadow-lg`}>
                      <currentStep.icon className="h-6 w-6 sm:h-8 sm:w-8 text-white" />
                    </div>
                  </motion.div>

                  <div className="relative z-10">
                    {/* Step Header */}
                    <motion.div
                      className="mb-4 sm:mb-6 pr-12 sm:pr-16"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                    >
                      <div className="flex items-center gap-2 sm:gap-3 mb-3">
                        <span className="px-2 sm:px-3 py-1 text-xs font-bold bg-white/20 text-white rounded-full backdrop-blur-sm">
                          STEP {currentStep.id} OF {processSteps.length}
                        </span>
                        <Lock className="h-3 w-3 sm:h-4 sm:w-4 text-white/60" />
                      </div>
                      <h3 className="text-xl sm:text-2xl lg:text-3xl xl:text-4xl font-bold text-white mb-2">
                        {currentStep.title}
                      </h3>
                      <p className="text-sm sm:text-base lg:text-lg text-white/80 font-medium">
                        {currentStep.subtitle}
                      </p>
                    </motion.div>

                    {/* Description */}
                    <motion.p
                      className="text-white/90 text-sm sm:text-base lg:text-lg leading-relaxed mb-6 sm:mb-8"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 }}
                    >
                      {currentStep.description}
                    </motion.p>

                    {/* Features List */}
                    <motion.div
                      className="space-y-3"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.6 }}
                    >
                      <h4 className="text-sm sm:text-base text-white font-semibold mb-3 sm:mb-4 flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                        Key Features
                      </h4>
                      <div className="grid gap-3">
                        {currentStep.features.map((feature, index) => (
                          <motion.div
                            key={feature}
                            className="flex items-center gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.8 + index * 0.1 }}
                            whileHover={{ scale: 1.02, x: 4 }}
                          >
                            <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-primary rounded-full flex-shrink-0" />
                            <span className="text-xs sm:text-sm lg:text-base text-white/90 font-medium">{feature}</span>
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  </div>
                </div>

                {/* Progress Indicator */}
                <motion.div
                  className="mt-8 flex justify-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1 }}
                >
                  <div className="flex items-center gap-2">
                    {processSteps.map((step) => (
                      <motion.button
                        key={step.id}
                        onClick={() => handleStepClick(step.id)}
                        className={`w-3 h-3 rounded-full transition-all duration-300 ${activeStep === step.id
                            ? 'bg-primary scale-125 shadow-lg shadow-primary/50'
                            : 'bg-white/30 hover:bg-white/50'
                          }`}
                        whileHover={{ scale: 1.2 }}
                        whileTap={{ scale: 0.9 }}
                      />
                    ))}
                  </div>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Bottom CTA Section */}
        <motion.div
          className="mt-12 sm:mt-16 lg:mt-20 text-center"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.5 }}
        >
          <div className="inline-flex items-center gap-3 sm:gap-4 px-4 sm:px-6 lg:px-8 py-3 sm:py-4 rounded-full bg-gradient-to-r from-primary/20 to-secondary/20 border border-primary/30 backdrop-blur-sm">
            <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            <span className="text-sm sm:text-base text-white font-medium">Ready to experience decentralized AI?</span>
            <motion.div
              animate={{ x: [0, 4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <ArrowRight className="h-4 w-4 sm:h-5 sm:w-5 text-secondary" />
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};