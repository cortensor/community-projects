'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';

interface NewIntroSplashProps {
  onComplete: () => void;
}

export default function NewIntroSplash({ onComplete }: NewIntroSplashProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [currentScene, setCurrentScene] = useState(0);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingText, setLoadingText] = useState('Initializing...');

  useEffect(() => {
    const scenes = [
      { duration: 3000 }, // Scene 0: Brand intro
      { duration: 3000 }, // Scene 1: Tagline
      { duration: 3000 }, // Scene 2: Features
      { duration: 4000 }, // Scene 3: Final loading
    ];

    const totalDuration = scenes.reduce((sum, scene) => sum + scene.duration, 0);
    
    // Progress animation
    const progressInterval = setInterval(() => {
      setLoadingProgress(prev => {
        const newProgress = prev + (100 / (totalDuration / 50)); // Update every 50ms
        return Math.min(newProgress, 100);
      });
    }, 50);

    // Loading text updates
    const loadingTexts = [
      'Initializing Neural Networks...',
      'Connecting to Blockchain...',
      'Loading AI Models...',
      'Synchronizing Decentralized Nodes...',
      'Optimizing Performance...',
      'Finalizing Setup...'
    ];

    let textIndex = 0;
    const textInterval = setInterval(() => {
      setLoadingText(loadingTexts[textIndex % loadingTexts.length]);
      textIndex++;
    }, 1800);

    // Scene transitions
    let totalTime = 0;
    scenes.forEach((scene, index) => {
      setTimeout(() => {
        if (index < scenes.length - 1) {
          setCurrentScene(index + 1);
        } else {
          setIsVisible(false);
          setTimeout(onComplete, 1000);
        }
      }, totalTime + scene.duration);
      totalTime += scene.duration;
    });

    return () => {
      clearInterval(progressInterval);
      clearInterval(textInterval);
    };
  }, [onComplete]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.8 }}
          className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
          style={{
            background: '#000000'
          }}
        >
          {/* Enhanced Background Elements */}
          <div className="absolute inset-0">
            {/* Animated Grid */}
            <div className="absolute inset-0 opacity-20">
              <svg width="100%" height="100%" className="absolute inset-0">
                <defs>
                  <pattern id="grid" x="0" y="0" width="50" height="50" patternUnits="userSpaceOnUse">
                    <path d="M 50 0 L 0 0 0 50" fill="none" stroke="hsl(120, 100%, 50%)" strokeWidth="0.5" opacity="0.3"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
              </svg>
            </div>

            {/* AI Neural Network Nodes - Performance Optimized */}
            {Array.from({ length: 12 }, (_, i) => (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-primary/40 rounded-full"
                style={{
                  left: `${20 + (i % 4) * 20}%`,
                  top: `${20 + Math.floor(i / 4) * 20}%`,
                }}
                animate={{
                  opacity: [0.2, 0.8, 0.2],
                  scale: [1, 1.5, 1],
                }}
                transition={{
                  duration: 2 + (i % 3),
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
            
            {/* Neural Network Connections */}
            <svg className="absolute inset-0 w-full h-full opacity-20" style={{ zIndex: 1 }}>
              {Array.from({ length: 8 }, (_, i) => (
                <motion.line
                  key={i}
                  x1={`${20 + (i % 4) * 20}%`}
                  y1={`${20 + Math.floor(i / 4) * 20}%`}
                  x2={`${20 + ((i + 1) % 4) * 20}%`}
                  y2={`${20 + Math.floor((i + 1) / 4) * 20}%`}
                  stroke="hsl(120, 100%, 50%)"
                  strokeWidth="0.5"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.6 }}
                  transition={{
                    duration: 2,
                    delay: i * 0.3,
                    repeat: Infinity,
                    repeatType: "reverse",
                  }}
                />
              ))}
            </svg>

            {/* Scanning Lines */}
            <motion.div
              className="absolute inset-0"
              style={{
                background: 'linear-gradient(90deg, transparent 0%, hsl(180, 100%, 50%, 0.1) 50%, transparent 100%)',
                width: '200px',
              }}
              animate={{
                x: ['-200px', 'calc(100vw + 200px)'],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: 'linear',
              }}
            />
          </div>

          {/* Scene-based Content */}
          <div className="relative z-10 text-center px-4 sm:px-6 md:px-8 w-full max-w-7xl mx-auto">
            {/* Scene 0: Brand Introduction */}
             {currentScene === 0 && (
               <motion.div
                 initial={{ opacity: 0, scale: 0.8 }}
                 animate={{ opacity: 1, scale: 1 }}
                 exit={{ opacity: 0, scale: 1.1 }}
                 transition={{ duration: 0.8 }}
                 className="flex flex-col items-center justify-center min-h-screen py-8 sm:py-12"
               >
                 {/* Holographic Effect */}
                 <motion.div
                   className="absolute inset-0 pointer-events-none"
                   animate={{
                     background: [
                       'radial-gradient(circle at 30% 30%, hsl(120, 100%, 50%, 0.1) 0%, transparent 50%)',
                       'radial-gradient(circle at 70% 70%, hsl(195, 100%, 50%, 0.1) 0%, transparent 50%)',
                       'radial-gradient(circle at 30% 70%, hsl(180, 100%, 50%, 0.1) 0%, transparent 50%)',
                       'radial-gradient(circle at 70% 30%, hsl(120, 100%, 50%, 0.1) 0%, transparent 50%)',
                     ],
                   }}
                   transition={{
                     duration: 6,
                     repeat: Infinity,
                   }}
                 />

                 <motion.h1 
                   className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl xl:text-9xl font-black mb-4 sm:mb-6 md:mb-8 leading-none relative px-4"
                   animate={{
                     scale: [1, 1.02, 1],
                   }}
                   transition={{
                     duration: 3,
                     repeat: Infinity,
                   }}
                 >
                   <motion.span
                     className="inline-block relative"
                     style={{
                       background: 'linear-gradient(45deg, hsl(120, 100%, 50%), hsl(195, 100%, 50%), hsl(180, 100%, 50%))',
                       backgroundSize: '300% 300%',
                       WebkitBackgroundClip: 'text',
                       WebkitTextFillColor: 'transparent',
                       backgroundClip: 'text',
                       filter: 'drop-shadow(0 0 40px hsl(120, 100%, 50%, 0.6))',
                     }}
                     animate={{
                       backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
                     }}
                     transition={{
                       duration: 4,
                       repeat: Infinity,
                     }}
                   >
                     CorTensorGPT
                     {/* Glitch Effect */}
                     <motion.span
                       className="absolute inset-0"
                       style={{
                         background: 'linear-gradient(45deg, hsl(120, 100%, 50%), hsl(195, 100%, 50%), hsl(180, 100%, 50%))',
                         backgroundSize: '300% 300%',
                         WebkitBackgroundClip: 'text',
                         WebkitTextFillColor: 'transparent',
                         backgroundClip: 'text',
                         transform: 'translateX(2px)',
                         opacity: 0,
                       }}
                       animate={{
                         opacity: [0, 0.3, 0],
                         x: [0, 2, -2, 0],
                       }}
                       transition={{
                         duration: 0.1,
                         repeat: Infinity,
                         repeatDelay: 3,
                       }}
                     >
                       CorTensorGPT
                     </motion.span>
                   </motion.span>
                 </motion.h1>
                 
                 <motion.div
                   initial={{ opacity: 0, y: 20 }}
                   animate={{ opacity: 1, y: 0 }}
                   transition={{ delay: 1, duration: 0.8 }}
                   className="text-lg sm:text-xl md:text-2xl text-white/90 font-light tracking-wide px-4"
                 >
                   <motion.span
                     animate={{
                       textShadow: [
                         '0 0 10px hsl(180, 100%, 50%, 0.5)',
                         '0 0 20px hsl(180, 100%, 50%, 0.8)',
                         '0 0 10px hsl(180, 100%, 50%, 0.5)',
                       ],
                     }}
                     transition={{
                       duration: 2,
                       repeat: Infinity,
                     }}
                   >
                     The Future of AI is Here
                   </motion.span>
                 </motion.div>
               </motion.div>
             )}

            {/* Scene 1: Tagline */}
             {currentScene === 1 && (
               <motion.div
                 initial={{ opacity: 0, x: -100 }}
                 animate={{ opacity: 1, x: 0 }}
                 exit={{ opacity: 0, x: 100 }}
                 transition={{ duration: 0.8 }}
                 className="flex flex-col items-center justify-center min-h-screen relative py-8 sm:py-12"
               >
                 {/* Dynamic Background Rings - Mobile Optimized */}
                 {[0, 1, 2].map((i) => (
                   <motion.div
                     key={i}
                     className="absolute rounded-full border opacity-20"
                     style={{
                       borderColor: `hsl(${120 + i * 30}, 100%, 50%)`,
                       width: `${150 + i * 75}px`,
                       height: `${150 + i * 75}px`,
                       borderWidth: '1px',
                     }}
                     animate={{
                       scale: [1, 1.1, 1],
                       rotate: [0, 360],
                       opacity: [0.2, 0.4, 0.2],
                     }}
                     transition={{
                       duration: 8 + i * 2,
                       repeat: Infinity,
                       delay: i * 0.5,
                     }}
                   />
                 ))}
                 
                 {/* Mobile-specific smaller rings */}
                 <div className="sm:hidden">
                   {[0, 1].map((i) => (
                     <motion.div
                       key={`mobile-${i}`}
                       className="absolute rounded-full border opacity-15"
                       style={{
                         borderColor: `hsl(${180 + i * 20}, 100%, 50%)`,
                         width: `${100 + i * 50}px`,
                         height: `${100 + i * 50}px`,
                         borderWidth: '0.5px',
                       }}
                       animate={{
                         scale: [1, 1.2, 1],
                         rotate: [360, 0],
                         opacity: [0.1, 0.3, 0.1],
                       }}
                       transition={{
                         duration: 6 + i,
                         repeat: Infinity,
                         delay: i * 0.3,
                       }}
                     />
                   ))}
                 </div>

                 <motion.div className="text-center z-10">
                   <motion.h2 
                   className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold mb-6 sm:mb-8 md:mb-12 px-4"
                   initial={{ y: 50, opacity: 0 }}
                   animate={{ y: 0, opacity: 1 }}
                   transition={{ delay: 0.3, duration: 0.8 }}
                 >
                     <span className="text-white">When </span>
                     <motion.span
                       className="inline-block"
                       style={{
                         color: 'hsl(195, 100%, 50%)',
                         textShadow: '0 0 30px hsl(195, 100%, 50%, 0.8)',
                       }}
                       animate={{
                         textShadow: [
                           '0 0 30px hsl(195, 100%, 50%, 0.8)',
                           '0 0 60px hsl(195, 100%, 50%, 1)',
                           '0 0 30px hsl(195, 100%, 50%, 0.8)',
                         ],
                         scale: [1, 1.05, 1],
                       }}
                       transition={{
                         duration: 2,
                         repeat: Infinity,
                       }}
                     >
                       Perplexity
                     </motion.span>
                   </motion.h2>
                   
                   <motion.h2 
                     className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold px-4"
                     initial={{ y: 50, opacity: 0 }}
                     animate={{ y: 0, opacity: 1 }}
                     transition={{ delay: 0.6, duration: 0.8 }}
                   >
                     <span className="text-white">meets </span>
                     <motion.span
                       className="inline-block"
                       style={{
                         color: 'hsl(180, 100%, 50%)',
                         textShadow: '0 0 30px hsl(180, 100%, 50%, 0.8)',
                       }}
                       animate={{
                         textShadow: [
                           '0 0 30px hsl(180, 100%, 50%, 0.8)',
                           '0 0 60px hsl(180, 100%, 50%, 1)',
                           '0 0 30px hsl(180, 100%, 50%, 0.8)',
                         ],
                         scale: [1, 1.05, 1],
                       }}
                       transition={{
                         duration: 2,
                         repeat: Infinity,
                         delay: 0.5,
                       }}
                     >
                       Decentralization
                     </motion.span>
                   </motion.h2>
                 </motion.div>
               </motion.div>
             )}

            {/* Scene 2: Features */}
             {currentScene === 2 && (
               <motion.div
                 initial={{ opacity: 0, y: 100 }}
                 animate={{ opacity: 1, y: 0 }}
                 exit={{ opacity: 0, y: -100 }}
                 transition={{ duration: 0.8 }}
                 className="flex flex-col items-center justify-center min-h-screen py-8 sm:py-12"
               >
                 <motion.h2 
                   className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-8 sm:mb-12 md:mb-16 text-center px-4"
                   initial={{ opacity: 0, y: -30 }}
                   animate={{ opacity: 1, y: 0 }}
                   transition={{ delay: 0.2, duration: 0.8 }}
                 >
                   Powered by Innovation
                 </motion.h2>

                 <div className="grid grid-cols-1 gap-3 sm:gap-4 md:gap-6 lg:gap-8 w-full max-w-sm sm:max-w-lg md:max-w-2xl lg:max-w-3xl mx-auto px-3 sm:px-4">
                   {[
                     { 
                       icon: '🧠', 
                       title: 'Neural Processing', 
                       desc: 'Advanced AI Intelligence with quantum-enhanced algorithms', 
                       color: 'hsl(120, 100%, 50%)',
                       features: ['Deep Learning', 'Pattern Recognition', 'Predictive Analytics']
                     },
                     { 
                       icon: '⛓️', 
                       title: 'Blockchain Verified', 
                       desc: 'Decentralized security with immutable transaction records', 
                       color: 'hsl(195, 100%, 50%)',
                       features: ['Smart Contracts', 'Consensus Protocol', 'Distributed Ledger']
                     },
                     { 
                       icon: '🌐', 
                       title: 'Global Network', 
                       desc: 'Worldwide accessibility with edge computing infrastructure', 
                       color: 'hsl(180, 100%, 50%)',
                       features: ['Edge Computing', 'Low Latency', 'Global Reach']
                     },
                   ].map((item, index) => (
                     <motion.div
                       key={index}
                       initial={{ opacity: 0, x: index % 2 === 0 ? -100 : 100, rotateY: 45 }}
                       animate={{ opacity: 1, x: 0, rotateY: 0 }}
                       transition={{ delay: index * 0.4, duration: 0.8, type: 'spring' }}
                       className="relative p-3 sm:p-4 md:p-6 lg:p-8 rounded-lg sm:rounded-xl md:rounded-2xl border border-white/20 backdrop-blur-md overflow-hidden group w-full"
                       style={{
                         background: `linear-gradient(135deg, ${item.color}15, ${item.color}05)`,
                         boxShadow: `0 8px 32px ${item.color}30`,
                       }}
                       whileHover={{
                         scale: 1.02,
                         boxShadow: `0 12px 40px ${item.color}40`,
                       }}
                     >
                       {/* Animated Border */}
                       <motion.div
                         className="absolute inset-0 rounded-2xl"
                         style={{
                           background: `linear-gradient(45deg, ${item.color}40, transparent, ${item.color}40)`,
                           backgroundSize: '200% 200%',
                         }}
                         animate={{
                           backgroundPosition: ['0% 0%', '100% 100%', '0% 0%'],
                         }}
                         transition={{
                           duration: 3,
                           repeat: Infinity,
                           delay: index * 0.5,
                         }}
                       />

                       <div className="relative z-10 flex flex-col items-center sm:items-start space-y-3 sm:space-y-0 sm:flex-row sm:space-x-3 md:space-x-4 lg:space-x-6">
                         <motion.div 
                           className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl flex-shrink-0"
                           animate={{
                             scale: [1, 1.1, 1],
                             rotate: [0, 5, -5, 0],
                           }}
                           transition={{
                             duration: 4,
                             repeat: Infinity,
                             delay: index * 0.7,
                           }}
                         >
                           {item.icon}
                         </motion.div>
                         
                         <div className="flex-1">
                           <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold text-white mb-2 text-center sm:text-left">{item.title}</h3>
                           <p className="text-white/80 mb-2 sm:mb-3 md:mb-4 text-xs sm:text-sm md:text-base lg:text-lg text-center sm:text-left leading-relaxed">{item.desc}</p>
                           
                           <div className="flex flex-wrap gap-1.5 sm:gap-2 justify-center sm:justify-start">
                             {item.features.map((feature, fIndex) => (
                               <motion.span
                                 key={fIndex}
                                 className="px-2 py-0.5 sm:px-3 sm:py-1 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap"
                                 style={{
                                   background: `${item.color}20`,
                                   color: item.color,
                                   border: `1px solid ${item.color}40`,
                                 }}
                                 initial={{ opacity: 0, scale: 0 }}
                                 animate={{ opacity: 1, scale: 1 }}
                                 transition={{ delay: index * 0.4 + fIndex * 0.1 + 0.5, duration: 0.3 }}
                               >
                                 {feature}
                               </motion.span>
                             ))}
                           </div>
                         </div>
                       </div>
                     </motion.div>
                   ))}
                 </div>
               </motion.div>
             )}

            {/* Scene 3: Final Loading */}
             {currentScene === 3 && (
               <motion.div
                 initial={{ opacity: 0, scale: 0.9 }}
                 animate={{ opacity: 1, scale: 1 }}
                 transition={{ duration: 0.8 }}
                 className="flex flex-col items-center justify-center min-h-screen py-8 sm:py-12"
               >
                 <motion.div
                   className="text-lg sm:text-xl md:text-2xl lg:text-3xl text-white mb-8 sm:mb-10 md:mb-12 font-light px-4 text-center"
                   animate={{
                     textShadow: [
                       '0 0 20px hsl(120, 100%, 50%, 0.5)',
                       '0 0 40px hsl(120, 100%, 50%, 0.8)',
                       '0 0 20px hsl(120, 100%, 50%, 0.5)',
                     ],
                   }}
                   transition={{
                     duration: 2,
                     repeat: Infinity,
                   }}
                 >
                   System Ready • Welcome to the Future
                 </motion.div>
                 
                 {/* Final Animation */}
                 <motion.div
                   className="relative"
                   animate={{
                     scale: [1, 1.1, 1],
                   }}
                   transition={{
                     duration: 2,
                     repeat: Infinity,
                   }}
                 >
                   {/* Expanding Rings */}
                   {[0, 1, 2, 3].map((i) => (
                     <motion.div
                       key={i}
                       className="absolute rounded-full border-2"
                       style={{
                         borderColor: `hsl(${120 + i * 20}, 100%, 50%)`,
                         width: 100 + i * 50 + 'px',
                         height: 100 + i * 50 + 'px',
                         left: '50%',
                         top: '50%',
                         transform: 'translate(-50%, -50%)',
                       }}
                       animate={{
                         scale: [1, 2, 1],
                         opacity: [0.8, 0, 0.8],
                         rotate: [0, 180, 360],
                       }}
                       transition={{
                         duration: 3,
                         repeat: Infinity,
                         delay: i * 0.3,
                       }}
                     />
                   ))}
                   
                   {/* Center Logo */}
                   <motion.div
                     className="relative z-10 w-20 h-20 sm:w-24 sm:h-24 md:w-28 md:h-28 rounded-full flex items-center justify-center overflow-hidden"
                     style={{
                       background: 'linear-gradient(45deg, hsl(120, 100%, 50%), hsl(180, 100%, 50%))',
                       boxShadow: '0 0 40px hsl(120, 100%, 50%, 0.6)',
                     }}
                     initial={{ scale: 0.3, opacity: 0 }}
                     animate={{
                       scale: [0.3, 1.2, 1, 1.5, 1],
                       opacity: [0, 1, 1, 1, 1],
                       boxShadow: [
                         '0 0 40px hsl(120, 100%, 50%, 0.6)',
                         '0 0 80px hsl(120, 100%, 50%, 1)',
                         '0 0 40px hsl(120, 100%, 50%, 0.6)',
                       ],
                     }}
                     transition={{
                       scale: { duration: 2.5, ease: "easeOut" },
                       opacity: { duration: 1.5 },
                       boxShadow: { duration: 2, repeat: Infinity },
                     }}
                   >
                     <motion.img
                       src="/cortigpt-4.png"
                       alt="CortiGPT"
                       className="w-full h-full object-contain p-2"
                       initial={{ scale: 0.8 }}
                       animate={{
                         scale: [0.8, 1.1, 1, 1.2, 1],
                       }}
                       transition={{
                         duration: 2.5,
                         ease: "easeOut",
                         delay: 0.3,
                       }}
                     />
                   </motion.div>
                   
                   {/* Orbiting 2D Planet Elements */}
                   {[0, 1, 2, 3, 4, 5].map((i) => (
                     <motion.div
                       key={i}
                       className="absolute rounded-full"
                       style={{
                         width: 8 + (i % 3) * 4 + 'px',
                         height: 8 + (i % 3) * 4 + 'px',
                         background: `linear-gradient(45deg, hsl(${120 + i * 30}, 100%, 50%), hsl(${180 + i * 20}, 100%, 50%))`,
                         boxShadow: `0 0 8px hsl(${120 + i * 30}, 100%, 50%, 0.8)`,
                         left: '50%',
                         top: '50%',
                         transform: 'translate(-50%, -50%)',
                       }}
                       animate={{
                         x: [
                           Math.cos((i * 60) * Math.PI / 180) * (60 + i * 15),
                           Math.cos((i * 60 + 360) * Math.PI / 180) * (60 + i * 15)
                         ],
                         y: [
                           Math.sin((i * 60) * Math.PI / 180) * (60 + i * 15),
                           Math.sin((i * 60 + 360) * Math.PI / 180) * (60 + i * 15)
                         ],
                         scale: [1, 1.2, 1],
                         opacity: [0.6, 1, 0.6],
                       }}
                       transition={{
                         x: { duration: 8 + i * 2, repeat: Infinity, ease: 'linear' },
                         y: { duration: 8 + i * 2, repeat: Infinity, ease: 'linear' },
                         scale: { duration: 2, repeat: Infinity, delay: i * 0.3 },
                         opacity: { duration: 2, repeat: Infinity, delay: i * 0.3 },
                       }}
                     />
                   ))}
                   
                   {/* Additional Orbiting Rings */}
                   {[0, 1, 2].map((i) => (
                     <motion.div
                       key={`ring-${i}`}
                       className="absolute rounded-full border border-dashed opacity-30"
                       style={{
                         borderColor: `hsl(${120 + i * 40}, 100%, 50%)`,
                         width: 80 + i * 40 + 'px',
                         height: 80 + i * 40 + 'px',
                         left: '50%',
                         top: '50%',
                         transform: 'translate(-50%, -50%)',
                       }}
                       animate={{
                         rotate: [0, 360],
                         scale: [1, 1.1, 1],
                         opacity: [0.2, 0.4, 0.2],
                       }}
                       transition={{
                         rotate: { duration: 12 + i * 4, repeat: Infinity, ease: 'linear' },
                         scale: { duration: 4, repeat: Infinity, delay: i * 0.5 },
                         opacity: { duration: 4, repeat: Infinity, delay: i * 0.5 },
                       }}
                     />
                   ))}
                 </motion.div>
               </motion.div>
             )}
          </div>

           {/* Persistent Loading Indicator - Mobile Responsive */}
           <motion.div 
             className="fixed bottom-4 sm:bottom-6 md:bottom-8 left-1/2 transform -translate-x-1/2 z-50 px-4"
             initial={{ opacity: 0, y: 50 }}
             animate={{ opacity: 1, y: 0 }}
             transition={{ delay: 0.5, duration: 0.8 }}
           >
             <div className="flex flex-col items-center space-y-3 sm:space-y-4">
               {/* Circular Progress - Responsive Size */}
               <div className="relative w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24">
                 {/* Background Circle */}
                 <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                   <circle
                     cx="50"
                     cy="50"
                     r="45"
                     stroke="hsl(120, 100%, 50%, 0.2)"
                     strokeWidth="3"
                     fill="none"
                   />
                   {/* Progress Circle */}
                   <motion.circle
                     cx="50"
                     cy="50"
                     r="45"
                     stroke="hsl(120, 100%, 50%)"
                     strokeWidth="3"
                     fill="none"
                     strokeLinecap="round"
                     strokeDasharray={283}
                     initial={{ strokeDashoffset: 283 }}
                     animate={{ strokeDashoffset: 283 - (283 * loadingProgress) / 100 }}
                     transition={{ duration: 0.1 }}
                     style={{
                       filter: 'drop-shadow(0 0 8px hsl(120, 100%, 50%, 0.8))',
                     }}
                   />
                 </svg>
                 
                 {/* Percentage Text - Responsive Size */}
                 <div className="absolute inset-0 flex items-center justify-center">
                   <motion.span 
                     className="text-sm sm:text-base md:text-lg lg:text-xl font-bold text-white"
                     animate={{
                       textShadow: [
                         '0 0 10px hsl(120, 100%, 50%, 0.5)',
                         '0 0 20px hsl(120, 100%, 50%, 0.8)',
                         '0 0 10px hsl(120, 100%, 50%, 0.5)',
                       ],
                     }}
                     transition={{
                       duration: 2,
                       repeat: Infinity,
                     }}
                   >
                     {Math.round(loadingProgress)}%
                   </motion.span>
                 </div>
               </div>
               
               {/* Loading Text - Mobile Optimized */}
               <motion.div 
                 className="text-center max-w-xs sm:max-w-sm"
                 animate={{
                   opacity: [0.7, 1, 0.7],
                 }}
                 transition={{
                   duration: 2,
                   repeat: Infinity,
                 }}
               >
                 <div className="text-xs sm:text-sm text-white/80 font-medium px-2 leading-tight">{loadingText}</div>
                 
                 {/* Loading Dots Animation - Responsive */}
                 <div className="flex justify-center space-x-1 mt-1.5 sm:mt-2">
                   {[0, 1, 2].map((i) => (
                     <motion.div
                       key={i}
                       className="w-1 h-1 sm:w-1.5 sm:h-1.5 rounded-full"
                       style={{ backgroundColor: 'hsl(120, 100%, 50%)' }}
                       animate={{
                         scale: [1, 1.5, 1],
                         opacity: [0.5, 1, 0.5],
                       }}
                       transition={{
                         duration: 1,
                         repeat: Infinity,
                         delay: i * 0.2,
                       }}
                     />
                   ))}
                 </div>
               </motion.div>
             </div>
           </motion.div>
 
         </motion.div>
       )}
     </AnimatePresence>
   );
 }