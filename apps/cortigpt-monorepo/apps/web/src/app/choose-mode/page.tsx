"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, Globe, Chrome, Zap, Eye, MessageSquare, Search, Shield, Star } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

const ChooseModePage = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="min-h-screen bg-background pt-32 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={containerVariants}
          className="text-center mb-16"
        >
          <motion.h1 
            variants={itemVariants}
            className="text-4xl sm:text-5xl md:text-6xl font-futura font-bold mb-6"
          >
            Choose Your <span className="gradient-text text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl">CortiGPT</span> Experience
          </motion.h1>
          <motion.p 
            variants={itemVariants}
            className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto font-tech"
          >
            Select how you want to interact with the world&apos;s first decentralized AI assistant
          </motion.p>
        </motion.div>

        <motion.div 
          initial="hidden"
          animate="visible"
          variants={containerVariants}
          className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto"
        >
          {/* Chrome Extension Option - Recommended */}
          <motion.div variants={itemVariants}>
            <Card className="relative h-full glass border-primary/30 bg-gradient-to-br from-primary/10 to-transparent backdrop-blur-xl overflow-hidden group hover:shadow-glow-primary transition-all duration-slow">
              {/* Recommended Badge */}
              <div className="absolute top-4 right-4 z-10">
                <Badge className="bg-primary text-primary-foreground font-semibold px-3 py-1">
                  <Star className="w-3 h-3 mr-1" />
                  RECOMMENDED
                </Badge>
              </div>

              <CardHeader className="pb-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-3 rounded-full bg-primary/20 border border-primary/30">
                    <Chrome className="w-8 h-8 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-2xl font-futura text-primary">Chrome Extension</CardTitle>
                    <CardDescription className="text-base font-tech">Full-powered CortiGPT experience</CardDescription>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Eye className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-primary mb-1">Context-Aware Intelligence</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Understands the webpage you&apos;re on and provides relevant explanations
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <MessageSquare className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-primary mb-1">Text Highlighting Magic</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Just like Perplexity Comet - highlight any text to get instant AI explanations
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Search className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-primary mb-1">Seamless Search Integration</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Search the web with decentralized AI without leaving your current page
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-primary mb-1">Always Available</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Sidepanel interface accessible from any website with one click
                      </p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-primary/20">
                  <p className="text-xs text-primary/80 font-tech mb-4 text-center">
                    🚀 Get the complete CortiGPT experience with all features unlocked
                  </p>
                  <Link href="/extension-install" className="block">
                    <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground group">
                      Install Chrome Extension
                      <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Web Interface Option */}
          <motion.div variants={itemVariants}>
            <Card className="h-full glass border-secondary/30 bg-gradient-to-br from-secondary/5 to-transparent backdrop-blur-xl group hover:shadow-glow-secondary transition-all duration-slow">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-3 rounded-full bg-secondary/20 border border-secondary/30">
                    <Globe className="w-8 h-8 text-secondary" />
                  </div>
                  <div>
                    <CardTitle className="text-2xl font-futura text-secondary">Web Interface</CardTitle>
                    <CardDescription className="text-base font-tech">Browser-based CortiGPT access</CardDescription>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Zap className="w-5 h-5 text-secondary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-secondary mb-1">Web3 & Web2 Modes</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Choose between blockchain-powered or traditional AI interactions
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <MessageSquare className="w-5 h-5 text-secondary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-secondary mb-1">Chat Interface</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Full-featured chat with conversation history and context
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Search className="w-5 h-5 text-secondary mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-secondary mb-1">Decentralized Search</h4>
                      <p className="text-sm text-muted-foreground font-tech">
                        Access verified AI search capabilities through web interface
                      </p>
                    </div>
                  </div>

                  <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3">
                    <p className="text-xs text-orange-400 font-tech">
                      ⚠️ Limited context awareness - cannot analyze content from other tabs
                    </p>
                  </div>
                </div>

                <div className="pt-4 border-t border-secondary/20">
                  <Link href="/cortensorChat" className="block">
                    <Button variant="outline" className="w-full border-secondary/50 text-secondary hover:bg-secondary/10 group">
                      Use Web Interface
                      <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>

        {/* Bottom Info */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="text-center mt-16"
        >
          <div className="glass p-6 rounded-2xl max-w-4xl mx-auto border border-accent/30">
            <h3 className="text-xl font-futura font-bold text-accent mb-3">
              🔗 100% Decentralized Architecture
            </h3>
            <p className="text-muted-foreground font-tech">
              Both options are powered by the same decentralized network of AI miners. 
              No central servers, no single points of failure - just pure, verifiable intelligence.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ChooseModePage;