import { motion } from "framer-motion";

export const ParticleField = () => {
  const particles = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 3 + 1,
    duration: Math.random() * 20 + 10,
    delay: Math.random() * 5,
  }));

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          className="absolute rounded-full bg-primary/30"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: particle.size,
            height: particle.size,
          }}
          animate={{
            y: [-20, 20, -20],
            opacity: [0.2, 0.6, 0.2],
          }}
          transition={{
            duration: particle.duration,
            repeat: Infinity,
            delay: particle.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
};

export const GlowOrb = ({ className = "" }: { className?: string }) => (
  <motion.div
    className={`absolute rounded-full bg-primary/20 blur-3xl ${className}`}
    animate={{
      scale: [1, 1.2, 1],
      opacity: [0.3, 0.5, 0.3],
    }}
    transition={{
      duration: 8,
      repeat: Infinity,
      ease: "easeInOut",
    }}
  />
);

export const ScanLine = () => (
  <motion.div
    className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary to-transparent"
    initial={{ top: 0, opacity: 0 }}
    animate={{
      top: ["0%", "100%"],
      opacity: [0, 1, 1, 0],
    }}
    transition={{
      duration: 4,
      repeat: Infinity,
      ease: "linear",
    }}
  />
);

export const GridBackground = () => (
  <div className="absolute inset-0 cyber-grid opacity-30" />
);

export const HexagonPattern = () => {
  const hexagons = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 40 + 20,
    rotation: Math.random() * 360,
    delay: Math.random() * 5,
  }));

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-10">
      {hexagons.map((hex) => (
        <motion.div
          key={hex.id}
          className="absolute border border-primary/50"
          style={{
            left: `${hex.x}%`,
            top: `${hex.y}%`,
            width: hex.size,
            height: hex.size,
            clipPath: "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)",
            transform: `rotate(${hex.rotation}deg)`,
          }}
          animate={{
            opacity: [0.1, 0.3, 0.1],
            rotate: [hex.rotation, hex.rotation + 60, hex.rotation],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            delay: hex.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
};

export const PulseRing = ({ className = "" }: { className?: string }) => (
  <div className={`relative ${className}`}>
    <motion.div
      className="absolute inset-0 rounded-full border-2 border-primary"
      animate={{
        scale: [1, 1.5],
        opacity: [0.8, 0],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeOut",
      }}
    />
    <motion.div
      className="absolute inset-0 rounded-full border-2 border-primary"
      animate={{
        scale: [1, 1.5],
        opacity: [0.8, 0],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeOut",
        delay: 0.5,
      }}
    />
  </div>
);
