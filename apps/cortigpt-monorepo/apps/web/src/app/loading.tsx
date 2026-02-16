"use client";

export default function Loading() {
  return (
    <div className="min-h-screen neural-bg flex items-center justify-center relative overflow-hidden">
      {/* Animated background particles */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-2 h-2 bg-secondary rounded-full animate-pulse opacity-60 glow-secondary"></div>
        <div className="absolute top-3/4 right-1/4 w-1 h-1 bg-primary rounded-full animate-ping opacity-40 glow-primary"></div>
        <div className="absolute top-1/2 left-3/4 w-1.5 h-1.5 bg-accent rounded-full animate-bounce opacity-50 glow-accent"></div>
        <div className="absolute top-1/3 right-1/3 w-1 h-1 bg-neural-tertiary rounded-full animate-pulse opacity-30"></div>
      </div>
      
      <div className="text-center z-10">
        {/* Main loading animation */}
        <div className="relative mb-8">
          {/* Outer ring */}
          <div className="w-24 h-24 border-4 border-transparent border-t-accent border-r-secondary rounded-full animate-spin mx-auto"></div>
          
          {/* Inner ring */}
          <div className="absolute inset-2 w-20 h-20 border-4 border-transparent border-b-primary border-l-neural-secondary rounded-full animate-spin animate-reverse mx-auto" style={{animationDirection: 'reverse', animationDuration: '1.5s'}}></div>
          
          {/* Center dot */}
          <div className="absolute inset-1/2 w-3 h-3 bg-gradient-primary rounded-full animate-pulse transform -translate-x-1/2 -translate-y-1/2"></div>
        </div>
        
        {/* Loading text with gradient */}
        <div className="space-y-2">
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl font-bold gradient-text animate-pulse">
            CortiGPT
          </h2>
          <p className="text-muted-foreground text-sm tracking-wider">
            <span className="inline-block animate-bounce text-primary-glow" style={{animationDelay: '0ms'}}>I</span>
            <span className="inline-block animate-bounce text-secondary-glow" style={{animationDelay: '100ms'}}>n</span>
            <span className="inline-block animate-bounce text-accent-glow" style={{animationDelay: '200ms'}}>i</span>
            <span className="inline-block animate-bounce text-primary-glow" style={{animationDelay: '300ms'}}>t</span>
            <span className="inline-block animate-bounce text-secondary-glow" style={{animationDelay: '400ms'}}>i</span>
            <span className="inline-block animate-bounce text-accent-glow" style={{animationDelay: '500ms'}}>a</span>
            <span className="inline-block animate-bounce text-primary-glow" style={{animationDelay: '600ms'}}>l</span>
            <span className="inline-block animate-bounce text-secondary-glow" style={{animationDelay: '700ms'}}>i</span>
            <span className="inline-block animate-bounce text-accent-glow" style={{animationDelay: '800ms'}}>z</span>
            <span className="inline-block animate-bounce text-primary-glow" style={{animationDelay: '900ms'}}>i</span>
            <span className="inline-block animate-bounce text-secondary-glow" style={{animationDelay: '1000ms'}}>n</span>
            <span className="inline-block animate-bounce text-accent-glow" style={{animationDelay: '1100ms'}}>g</span>
            <span className="inline-block animate-bounce text-primary-glow" style={{animationDelay: '1200ms'}}>.</span>
            <span className="inline-block animate-bounce text-secondary-glow" style={{animationDelay: '1300ms'}}>.</span>
            <span className="inline-block animate-bounce text-accent-glow" style={{animationDelay: '1400ms'}}>.</span>
          </p>
        </div>
        
        {/* Progress bar */}
        <div className="mt-8 w-64 h-1 bg-muted rounded-full mx-auto overflow-hidden">
          <div className="h-full bg-gradient-secondary rounded-full animate-pulse" style={{width: '60%', animation: 'loading-progress 2s ease-in-out infinite'}}></div>
        </div>
      </div>
      
      {/* Custom keyframes for progress animation */}
      <style jsx>{`
        @keyframes loading-progress {
          0% { width: 20%; }
          50% { width: 80%; }
          100% { width: 20%; }
        }
      `}</style>
    </div>
  );
}