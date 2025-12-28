import { motion } from "framer-motion";
import { Scale, Shield, Zap, Eye, Gavel, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ParticleField, GlowOrb, HexagonPattern } from "@/components/effects/AnimatedEffects";

export const HeroSection = () => {
  const floatingIcons = [
    { Icon: Shield, delay: 0, x: "10%", y: "20%" },
    { Icon: Gavel, delay: 0.5, x: "85%", y: "30%" },
    { Icon: Eye, delay: 1, x: "15%", y: "70%" },
    { Icon: Activity, delay: 1.5, x: "80%", y: "75%" },
  ];

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      <ParticleField />
      <HexagonPattern />
      <GlowOrb className="w-96 h-96 -top-48 -left-48" />
      <GlowOrb className="w-[500px] h-[500px] -bottom-64 -right-64 bg-[hsl(270,80%,60%)]/20" />
      
      {floatingIcons.map(({ Icon, delay, x, y }, index) => (
        <motion.div
          key={index}
          className="absolute hidden lg:block"
          style={{ left: x, top: y }}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 0.2, scale: 1 }}
          transition={{ delay: delay + 1, duration: 1 }}
        >
          <motion.div
            animate={{ y: [-10, 10, -10] }}
            transition={{ duration: 5 + index, repeat: Infinity, ease: "easeInOut" }}
          >
            <Icon className="w-12 h-12 text-primary/30" />
          </motion.div>
        </motion.div>
      ))}

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, staggerChildren: 0.15 }}
        className="relative z-10 container mx-auto px-6 text-center"
      >
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-8"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/5 backdrop-blur-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
            </span>
            <span className="text-sm font-mono text-muted-foreground">
              Network Status: <span className="text-success">Operational</span>
            </span>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.15 }}
          className="mb-6"
        >
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight">
            <span className="block text-foreground">THE</span>
            <span className="block mt-2 bg-gradient-to-r from-primary via-[hsl(270,80%,60%)] to-primary bg-clip-text text-transparent neon-text">
              CORTENSOR
            </span>
            <span className="block mt-2 text-foreground">JUDGE</span>
          </h1>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="flex justify-center mb-8"
        >
          <motion.div
            className="relative"
            animate={{ rotateY: [0, 360] }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          >
            <Scale className="w-20 h-20 text-accent" />
          </motion.div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.45 }}
          className="text-lg md:text-xl text-muted-foreground max-w-3xl mx-auto mb-10 leading-relaxed"
        >
          Decentralized dispute resolution for AI agents. Challenge outputs, 
          initiate trials via validator consensus, and settle justice on-chain.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Button variant="cyber" size="xl" className="group">
            <Zap className="w-5 h-5 transition-transform group-hover:scale-110" />
            <span>Enter Courtroom</span>
          </Button>
          <Button variant="outline" size="xl">
            <Eye className="w-5 h-5" />
            <span>View Active Cases</span>
          </Button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.75 }}
          className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto"
        >
          {[
            { label: "Active Disputes", value: "127", trend: "+12%" },
            { label: "Verdicts Delivered", value: "8,429", trend: "99.2% acc" },
            { label: "COR Staked", value: "2.4M", trend: "$4.2M" },
            { label: "Network Validators", value: "342", trend: "Online" },
          ].map((stat, index) => (
            <motion.div
              key={index}
              className="p-4 rounded-xl border border-border/50 bg-card/30 backdrop-blur-sm"
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="text-2xl md:text-3xl font-bold font-mono text-primary">
                {stat.value}
              </div>
              <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
              <div className="text-xs text-success font-mono mt-1">{stat.trend}</div>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
    </section>
  );
};
