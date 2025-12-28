import { motion } from "framer-motion";
import { useState } from "react";
import { 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Eye, 
  FileSearch,
  ArrowRight,
  Cpu,
  Hash,
  User
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Dispute {
  id: string;
  taskId: string;
  status: "pending" | "active" | "resolved" | "slashed";
  challenger: string;
  miner: string;
  similarity: number;
  bondAmount: string;
  timestamp: string;
  model: string;
}

const mockDisputes: Dispute[] = [
  {
    id: "DSP-0x7a3f",
    taskId: "TASK-8291",
    status: "active",
    challenger: "0x742d...8f21",
    miner: "0x9a1c...3e45",
    similarity: 0.73,
    bondAmount: "500 COR",
    timestamp: "2 min ago",
    model: "gemini-2.5-flash",
  },
  {
    id: "DSP-0x2b9e",
    taskId: "TASK-8289",
    status: "pending",
    challenger: "0x3f8e...2a91",
    miner: "0x1d7c...9b32",
    similarity: 0.89,
    bondAmount: "250 COR",
    timestamp: "5 min ago",
    model: "llama-3.3-70b",
  },
  {
    id: "DSP-0x5c4d",
    taskId: "TASK-8285",
    status: "resolved",
    challenger: "0x8e2f...7c19",
    miner: "0x4b3a...1d67",
    similarity: 0.91,
    bondAmount: "1000 COR",
    timestamp: "12 min ago",
    model: "gpt-5-mini",
  },
  {
    id: "DSP-0x1a8b",
    taskId: "TASK-8280",
    status: "slashed",
    challenger: "0x6d4c...3f82",
    miner: "0x2e9a...5c71",
    similarity: 0.45,
    bondAmount: "750 COR",
    timestamp: "18 min ago",
    model: "qwen-2.5-72b",
  },
];

const StatusBadge = ({ status }: { status: Dispute["status"] }) => {
  const variants = {
    pending: { variant: "warning" as const, icon: Clock, label: "Pending Review" },
    active: { variant: "dispute" as const, icon: AlertTriangle, label: "Active Trial" },
    resolved: { variant: "success" as const, icon: CheckCircle2, label: "Resolved" },
    slashed: { variant: "destructive" as const, icon: AlertTriangle, label: "Miner Slashed" },
  };

  const { variant, icon: Icon, label } = variants[status];

  return (
    <Badge variant={variant} className="gap-1.5">
      <Icon className="w-3 h-3" />
      {label}
    </Badge>
  );
};

const SimilarityMeter = ({ value }: { value: number }) => {
  const percentage = value * 100;
  const colorClass = value < 0.8 ? "bg-destructive" : value < 0.95 ? "bg-warning" : "bg-success";
  const textClass = value < 0.8 ? "text-destructive" : value < 0.95 ? "text-warning" : "text-success";
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">Similarity Score</span>
        <span className={`font-mono ${textClass}`}>{percentage.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${colorClass} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </div>
    </div>
  );
};

const DisputeCard = ({ dispute, index }: { dispute: Dispute; index: number }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  const cardVariant = dispute.status === "active" || dispute.status === "slashed" 
    ? "dispute" as const
    : dispute.status === "resolved" 
    ? "verdict" as const
    : "cyber" as const;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
    >
      <Card 
        variant={cardVariant}
        className="overflow-hidden cursor-pointer card-hover"
      >
        {/* Scan line effect on hover */}
        {isHovered && (
          <motion.div
            className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-primary to-transparent"
            initial={{ top: 0 }}
            animate={{ top: "100%" }}
            transition={{ duration: 1, repeat: Infinity }}
          />
        )}
        
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg font-mono flex items-center gap-2">
                <Hash className="w-4 h-4 text-primary" />
                {dispute.id}
              </CardTitle>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Cpu className="w-3 h-3" />
                <span>{dispute.model}</span>
                <span className="text-border">•</span>
                <span>{dispute.timestamp}</span>
              </div>
            </div>
            <StatusBadge status={dispute.status} />
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Parties */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <User className="w-3 h-3" />
                Challenger
              </div>
              <div className="font-mono text-sm text-primary">{dispute.challenger}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                Miner
              </div>
              <div className="font-mono text-sm">{dispute.miner}</div>
            </div>
          </div>
          
          {/* Similarity Meter */}
          <SimilarityMeter value={dispute.similarity} />
          
          {/* Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <div className="space-y-0.5">
              <div className="text-xs text-muted-foreground">Bond Staked</div>
              <div className="font-mono text-sm text-accent font-semibold">{dispute.bondAmount}</div>
            </div>
            <Button variant="ghost" size="sm" className="gap-1 text-primary">
              <Eye className="w-4 h-4" />
              Inspect
              <ArrowRight className="w-3 h-3" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const DisputeFeed = () => {
  const [activeTab, setActiveTab] = useState(0);
  const tabs = ["All Cases", "Active Trials", "Pending", "Resolved", "Slashed"];
  
  return (
    <section className="py-20 relative">
      <div className="container mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <Badge variant="cyber" className="mb-4">
            <FileSearch className="w-3 h-3 mr-1" />
            Live Feed
          </Badge>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Active <span className="text-primary">Dispute</span> Queue
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Real-time stream of AI inference challenges awaiting validator consensus
          </p>
        </motion.div>

        {/* Filter Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex flex-wrap justify-center gap-2 mb-8"
        >
          {tabs.map((tab, index) => (
            <Button
              key={tab}
              variant={index === activeTab ? "cyber" : "ghost"}
              size="sm"
              onClick={() => setActiveTab(index)}
            >
              {tab}
              {index === 1 && (
                <span className="ml-2 px-2 py-0.5 text-xs bg-destructive/20 text-destructive rounded-full">
                  12
                </span>
              )}
            </Button>
          ))}
        </motion.div>

        {/* Dispute Cards Grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {mockDisputes.map((dispute, index) => (
            <DisputeCard key={dispute.id} dispute={dispute} index={index} />
          ))}
        </div>

        {/* Load More */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mt-8"
        >
          <Button variant="outline" className="gap-2">
            Load More Cases
            <ArrowRight className="w-4 h-4" />
          </Button>
        </motion.div>
      </div>
    </section>
  );
};
