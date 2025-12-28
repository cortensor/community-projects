"use client";

import { Button } from "@/components/ui/button";
import { Github, Twitter, MessageCircle, ArrowRight } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="py-12 sm:py-16 lg:py-20 px-4 sm:px-6 border-t border-border/50">
      <div className="max-w-7xl mx-auto">
        {/* Main Footer Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 sm:gap-16 mb-12 sm:mb-16">
          {/* Left: Final CTA */}
          <div className="space-y-6 sm:space-y-8 text-center lg:text-left">
            <div>
              <h2 className="text-4xl md:text-5xl font-futura font-bold mb-6">
                Join the Future of{" "}
                <span className="gradient-text text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl">Verifiable AI</span>
              </h2>
              <p className="text-xl text-muted-foreground font-tech leading-relaxed">
                Experience the power of multi-agent intelligence with trustless verification
                and immutable proof receipts.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Button variant="hero" size="lg" className="group">
                Try the Demo
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button variant="neural" size="lg">
                Get API Access
              </Button>
            </div>
          </div>

          {/* Right: Links & Social */}
          <div className="grid grid-cols-2 gap-8">
            {/* Quick Links */}
            <div>
              <h3 className="text-lg font-futura font-bold mb-6 text-white">Platform</h3>
              <ul className="space-y-4 font-tech">
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">CortiTruth</a></li>
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">CortiChat</a></li>
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">CortiTweets</a></li>
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">API Access</a></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h3 className="text-lg font-futura font-bold mb-6 text-white">Resources</h3>
              <ul className="space-y-4 font-tech">
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Documentation</a></li>
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Whitepaper</a></li>
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Developer Guide</a></li>
                <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Support</a></li>
              </ul>
            </div>
          </div>
        </div>

        {/* Social Links */}
        <div className="flex flex-col sm:flex-row justify-between items-center pt-8 border-t border-border/30">
          <div className="flex items-center space-x-6 mb-4 sm:mb-0">
            <a
              href="#"
              className="p-3 glass rounded-full hover:shadow-glow-primary transition-all duration-smooth group"
            >
              <Github className="h-5 w-5 text-muted-foreground group-hover:text-primary" />
            </a>
            <a
              href="#"
              className="p-3 glass rounded-full hover:shadow-glow-secondary transition-all duration-smooth group"
            >
              <Twitter className="h-5 w-5 text-muted-foreground group-hover:text-secondary" />
            </a>
            <a
              href="#"
              className="p-3 glass rounded-full hover:shadow-glow-accent transition-all duration-smooth group"
            >
              <MessageCircle className="h-5 w-5 text-muted-foreground group-hover:text-accent" />
            </a>
          </div>

          <div className="text-center sm:text-right">
            <div className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl font-futura font-bold gradient-text mb-2">CortiGPT</div>
            <p className="text-sm text-muted-foreground font-tech">
              Powered by Cortensor Protocol
            </p>
          </div>
        </div>

        {/* Copyright */}
        <div className="text-center pt-8 border-t border-border/30 mt-8">
          <p className="text-sm text-muted-foreground font-tech">
            © 2024 CortiGPT. Building the future of verifiable AI.
          </p>
        </div>
      </div>
    </footer>
  );
};