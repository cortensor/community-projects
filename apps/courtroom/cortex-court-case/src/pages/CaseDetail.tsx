import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { 
  ArrowLeft,
  Clock,
  AlertTriangle,
  CheckCircle2,
  User,
  Cpu,
  Hash,
  FileText,
  Brain,
  GitBranch,
  Zap,
  Download,
  ExternalLink,
  Copy,
  Check,
  Gavel
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { mockDisputes, type Dispute } from "@/data/mockData";
import { useWallet } from "@/hooks/useWallet";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { toast } from "sonner";

interface LogicStep {
  id: number;
  type: "input" | "reasoning" | "validation" | "output";
  content: string;
  confidence: number;
  timestamp: string;
  isAnomaly?: boolean;
}

const mockLogicTrace: LogicStep[] = [
  { id: 1, type: "input", content: "User prompt received: 'Calculate optimal trading strategy'", confidence: 1.0, timestamp: "0ms" },
  { id: 2, type: "reasoning", content: "Analyzing market conditions... Fetching volume data", confidence: 0.95, timestamp: "124ms" },
  { id: 3, type: "reasoning", content: "Applying risk management constraints", confidence: 0.92, timestamp: "267ms" },
  { id: 4, type: "validation", content: "Cross-referencing with historical backtests", confidence: 0.88, timestamp: "445ms", isAnomaly: true },
  { id: 5, type: "reasoning", content: "Strategy synthesis: DCA entry with trailing stop-loss", confidence: 0.91, timestamp: "589ms" },
  { id: 6, type: "output", content: "Final recommendation generated", confidence: 0.89, timestamp: "623ms" },
];

const StatusBadge = ({ status }: { status: Dispute["status"] }) => {
  const config = {
    pending: { className: "bg-warning/10 text-warning border-warning/20", icon: Clock, label: "Pending Review" },
    active: { className: "bg-primary/10 text-primary border-primary/20", icon: AlertTriangle, label: "Active Trial" },
    resolved: { className: "bg-success/10 text-success border-success/20", icon: CheckCircle2, label: "Resolved" },
    slashed: { className: "bg-destructive/10 text-destructive border-destructive/20", icon: AlertTriangle, label: "Miner Slashed" },
  };
  const { className, icon: Icon, label } = config[status];
  return (
    <Badge variant="outline" className={`${className} text-sm px-3 py-1`}>
      <Icon className="w-4 h-4 mr-1.5" />
      {label}
    </Badge>
  );
};

const StepIcon = ({ type }: { type: LogicStep["type"] }) => {
  const icons = { input: FileText, reasoning: Brain, validation: GitBranch, output: Zap };
  const Icon = icons[type];
  return <Icon className="w-4 h-4" />;
};

const CaseDetail = () => {
  const { id } = useParams();
  const [copied, setCopied] = useState(false);
  const { isConnected, openConnectModal } = useWallet();
  
  const dispute = mockDisputes.find(d => d.id === id);

  if (!dispute) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="container mx-auto px-4 sm:px-6 py-16 text-center">
          <h1 className="text-2xl font-bold mb-4">Case Not Found</h1>
          <p className="text-muted-foreground mb-6">The case you're looking for doesn't exist.</p>
          <Link to="/cases">
            <Button>Back to Cases</Button>
          </Link>
        </main>
        <Footer />
      </div>
    );
  }

  const handleCopyHash = () => {
    navigator.clipboard.writeText("0x7a3f8b2c1d9e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9");
    setCopied(true);
    toast.success("Hash copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleVote = (vote: "uphold" | "dismiss") => {
    if (!isConnected) {
      toast.error("Please connect your wallet to vote");
      return;
    }
    toast.success(`Vote submitted: ${vote === "uphold" ? "Uphold Challenge" : "Dismiss Challenge"}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="container mx-auto px-4 sm:px-6 py-8">
        {/* Back Button */}
        <Link to="/cases" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to Cases
        </Link>

        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold font-mono">{dispute.id}</h1>
                <StatusBadge status={dispute.status} />
              </div>
              <p className="text-muted-foreground">{dispute.description}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="gap-2">
                <Download className="w-4 h-4" />
                Export Evidence
              </Button>
              <Button variant="outline" className="gap-2">
                <ExternalLink className="w-4 h-4" />
                View on Chain
              </Button>
            </div>
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Details Card */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Hash className="w-5 h-5 text-primary" />
                    Case Details
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid sm:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm text-muted-foreground flex items-center gap-1 mb-1">
                          <User className="w-3 h-3" /> Challenger
                        </p>
                        <p className="font-mono text-sm">{`${dispute.challenger.slice(0, 10)}...${dispute.challenger.slice(-8)}`}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground flex items-center gap-1 mb-1">
                          <Cpu className="w-3 h-3" /> Miner
                        </p>
                        <p className="font-mono text-sm">{`${dispute.miner.slice(0, 10)}...${dispute.miner.slice(-8)}`}</p>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Model</p>
                        <Badge variant="secondary">{dispute.model}</Badge>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Task ID</p>
                        <p className="font-mono text-sm">{dispute.taskId}</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-6 border-t border-border">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Similarity Score</span>
                      <span className={`font-mono font-semibold ${
                        dispute.similarity < 0.8 ? "text-destructive" : 
                        dispute.similarity < 0.95 ? "text-warning" : "text-success"
                      }`}>
                        {(dispute.similarity * 100).toFixed(1)}%
                      </span>
                    </div>
                    <Progress 
                      value={dispute.similarity * 100} 
                      className={`h-3 ${
                        dispute.similarity < 0.8 ? "[&>div]:bg-destructive" : 
                        dispute.similarity < 0.95 ? "[&>div]:bg-warning" : "[&>div]:bg-success"
                      }`}
                    />
                    <p className="text-xs text-muted-foreground mt-2">
                      {dispute.similarity < 0.8 ? "Critical: High likelihood of hallucination" :
                       dispute.similarity < 0.95 ? "Warning: Moderate inconsistency detected" :
                       "Acceptable: Within normal variance"}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Logic Trace */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="w-5 h-5 text-primary" />
                    Logic Trace Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {mockLogicTrace.map((step, index) => (
                      <div key={step.id} className="relative">
                        {index < mockLogicTrace.length - 1 && (
                          <div className="absolute left-5 top-10 bottom-0 w-px bg-border" />
                        )}
                        <div className={`p-4 rounded-lg border ${
                          step.isAnomaly ? "border-destructive/30 bg-destructive/5" : "border-border bg-muted/30"
                        }`}>
                          {step.isAnomaly && (
                            <Badge variant="destructive" className="mb-2 text-xs">
                              Anomaly Detected
                            </Badge>
                          )}
                          <div className="flex items-start gap-3">
                            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-primary/10 border border-primary/20">
                              <StepIcon type={step.type} />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <Badge variant="outline" className="capitalize text-xs">{step.type}</Badge>
                                <span className="text-xs font-mono text-muted-foreground">{step.timestamp}</span>
                              </div>
                              <p className="text-sm">{step.content}</p>
                              <div className="mt-2 flex items-center gap-2">
                                <Progress value={step.confidence * 100} className="flex-1 h-1.5" />
                                <span className="text-xs text-muted-foreground">{(step.confidence * 100).toFixed(0)}%</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Evidence Bundle */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Evidence Bundle</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-3 rounded-lg bg-muted">
                    <p className="text-xs text-muted-foreground mb-1">Proof of Inference (PoI)</p>
                    <div className="flex items-center gap-2">
                      <p className="font-mono text-xs text-primary truncate flex-1">
                        0x7a3f8b2c1d9e4f5a...8f9
                      </p>
                      <button onClick={handleCopyHash} className="text-muted-foreground hover:text-foreground">
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-muted">
                      <p className="text-xs text-muted-foreground mb-1">Model</p>
                      <p className="font-mono text-sm">{dispute.model}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-muted">
                      <p className="text-xs text-muted-foreground mb-1">Latency</p>
                      <p className="font-mono text-sm">623ms</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground mb-2">Validation Checks</p>
                    {[
                      { label: "Semantic Coherence", passed: true },
                      { label: "Factual Accuracy", passed: true },
                      { label: "Logic Consistency", passed: false },
                      { label: "Safety Filters", passed: true },
                    ].map((check, index) => (
                      <div key={index} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                        <span className="text-sm">{check.label}</span>
                        {check.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-success" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-destructive" />
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Voting */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Gavel className="w-5 h-5 text-primary" />
                    Cast Your Vote
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Bond: <span className="font-semibold text-primary">{dispute.bondAmount}</span>
                  </p>
                  
                  {isConnected ? (
                    <div className="space-y-2">
                      <Button onClick={() => handleVote("uphold")} className="w-full gap-2" variant="default">
                        <CheckCircle2 className="w-4 h-4" />
                        Uphold Challenge
                      </Button>
                      <Button onClick={() => handleVote("dismiss")} className="w-full gap-2" variant="outline">
                        <AlertTriangle className="w-4 h-4" />
                        Dismiss Challenge
                      </Button>
                    </div>
                  ) : (
                    <Button onClick={openConnectModal} className="w-full">
                      Connect to Vote
                    </Button>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default CaseDetail;