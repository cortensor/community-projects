import { motion } from "framer-motion";
import { 
  Shield, 
  Cpu, 
  Zap, 
  Eye, 
  Lock, 
  ArrowRight,
  CheckCircle2
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface FeatureCardProps {
  icon: React.ElementType;
  title: string;
  description: string;
  features: string[];
  delay: number;
}

const FeatureCard = ({ icon: Icon, title, description, features, delay }: FeatureCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay, duration: 0.6 }}
  >
    <Card variant="cyber" className="h-full group hover:border-primary/40 transition-all duration-500">
      <CardContent className="p-8">
        {/* Icon */}
        <motion.div
          className="w-16 h-16 rounded-2xl mb-6 flex items-center justify-center bg-primary/10 border border-primary/30"
          whileHover={{ scale: 1.1, rotate: 5 }}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <Icon className="w-8 h-8 text-primary" />
        </motion.div>

        {/* Title */}
        <h3 className="text-xl font-bold mb-3">{title}</h3>
        
        {/* Description */}
        <p className="text-muted-foreground mb-6">{description}</p>

        {/* Feature List */}
        <ul className="space-y-3">
          {features.map((feature, index) => (
            <motion.li
              key={index}
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: delay + 0.1 * index }}
              className="flex items-center gap-2 text-sm"
            >
              <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" />
              <span>{feature}</span>
            </motion.li>
          ))}
        </ul>

        {/* Hover Arrow */}
        <div className="mt-6 flex items-center text-primary opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-sm font-medium">Learn more</span>
          <ArrowRight className="w-4 h-4 ml-2" />
        </div>
      </CardContent>
    </Card>
  </motion.div>
);

export const FeaturesSection = () => {
  const features = [
    {
      icon: Shield,
      title: "Validator Consensus",
      description: "Multi-node validation ensures AI outputs meet quality and safety standards through cryptographic proof.",
      features: [
        "Proof of Useful Work (PoUW)",
        "Byzantine fault tolerance",
        "Slashing for malicious actors",
        "Reward distribution"
      ],
    },
    {
      icon: Eye,
      title: "Forensic Analysis",
      description: "Complete transparency with Chain of Thought inspection and logic trace verification for every inference.",
      features: [
        "Step-by-step reasoning",
        "Anomaly detection",
        "Evidence bundling",
        "IPFS storage"
      ],
    },
    {
      icon: Cpu,
      title: "Adversarial Sentinel",
      description: "Automated hallucination detection using vector similarity comparisons across multiple miner outputs.",
      features: [
        "Cosine similarity checks",
        "< 95% triggers challenge",
        "Real-time monitoring",
        "Pinecone integration"
      ],
    },
    {
      icon: Lock,
      title: "On-Chain Settlement",
      description: "Transparent and immutable dispute resolution with COR token staking and automated verdict execution.",
      features: [
        "Smart contract verdicts",
        "Bond staking mechanism",
        "Automated slashing",
        "Reward distribution"
      ],
    },
    {
      icon: Zap,
      title: "Instant Challenges",
      description: "Anyone can challenge suspicious AI outputs by staking COR tokens and initiating a trial process.",
      features: [
        "x402 payment protocol",
        "ERC-8004 identity",
        "Dispute window queue",
        "Priority processing"
      ],
    },
  ];

  return (
    <section className="py-20 relative">
      <div className="container mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <Badge variant="cyber" className="mb-4">
            <Zap className="w-3 h-3 mr-1" />
            Core Features
          </Badge>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Decentralized <span className="text-primary">Justice</span> Infrastructure
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            A complete ecosystem for AI accountability, from challenge initiation to on-chain verdict settlement
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.slice(0, 3).map((feature, index) => (
            <FeatureCard key={index} {...feature} delay={index * 0.15} />
          ))}
        </div>
        
        <div className="grid md:grid-cols-2 gap-6 mt-6 max-w-4xl mx-auto">
          {features.slice(3).map((feature, index) => (
            <FeatureCard key={index + 3} {...feature} delay={(index + 3) * 0.15} />
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <Button variant="cyber" size="lg" className="gap-2">
            <Shield className="w-5 h-5" />
            Become a Validator
            <ArrowRight className="w-4 h-4" />
          </Button>
        </motion.div>
      </div>
    </section>
  );
};
