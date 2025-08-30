import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';

interface SplashScreenProps {
  onComplete: () => void;
}

const SplashScreen = ({ onComplete }: SplashScreenProps) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  const features = [
    {
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      ),
      title: "Web Search",
      description: "Search the web for real-time information and answers to your questions"
    },
    {
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      title: "Text Explanation",
      description: "Highlight any text on the web and get instant explanations and insights"
    }
  ];

  useEffect(() => {
    const timer = setTimeout(() => {
      if (currentStep < features.length - 1) {
        setCurrentStep(prev => prev + 1);
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [currentStep, features.length]);

  const handleGetStarted = () => {
    setIsVisible(false);
    setTimeout(() => {
      onComplete();
    }, 300);
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 bg-background neural-bg grid-bg">
      {/* Animated particles */}
      <div className="particles">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="particle"
            style={{
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 6}s`,
              animationDuration: `${6 + Math.random() * 4}s`
            }}
          />
        ))}
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen p-6">
        {/* Logo and Title */}
        <div className="text-center mb-12 animate-in fade-in-50 duration-700">
          <div className="mb-6">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center glow-primary">
              <svg className="w-12 h-12 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mb-3 gradient-text">
            Welcome to CortiGPT
          </h1>
          <p className="text-muted-foreground text-lg max-w-md mx-auto">
            Your AI-powered browser companion for intelligent web interactions
          </p>
        </div>

        {/* Features */}
        <div className="w-full max-w-md space-y-6 mb-12">
          {features.map((feature, index) => (
            <div
              key={index}
              className={`glass rounded-xl p-6 transition-all duration-700 ${
                index <= currentStep 
                  ? 'opacity-100 translate-y-0' 
                  : 'opacity-0 translate-y-4'
              }`}
              style={{ transitionDelay: `${index * 200}ms` }}
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center text-primary glow-primary">
                  {feature.icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Get Started Button */}
        <div className="animate-in fade-in-50 duration-1000 delay-1000">
          <Button
            onClick={handleGetStarted}
            size="lg"
            className="bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 text-primary-foreground font-semibold px-8 py-3 rounded-xl glow-primary transition-all duration-300 hover:scale-105"
          >
            Get Started
          </Button>
        </div>

        {/* Progress indicator */}
        <div className="mt-8 flex space-x-2">
          {features.map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                index <= currentStep 
                  ? 'bg-primary scale-125' 
                  : 'bg-muted-foreground/30'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default SplashScreen;
