import { motion } from "framer-motion";
import { useState } from "react";
import { 
  Brain, 
  GitBranch, 
  CheckCircle2, 
  XCircle,
  ChevronRight,
  Code,
  FileText,
  Fingerprint,
  Layers,
  ArrowLeftRight,
  Zap
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface LogicStep {
  id: number;
  type: "input" | "reasoning" | "validation" | "output";
  content: string;
  confidence: number;
  timestamp: string;
  isAnomaly?: boolean;
}

const mockLogicTrace: LogicStep[] = [
  {
    id: 1,
    type: "input",
    content: "User prompt received: 'Calculate the optimal trading strategy for ETH/USDC pair with 10% max drawdown'",
    confidence: 1.0,
    timestamp: "0ms",
  },
  {
    id: 2,
    type: "reasoning",
    content: "Analyzing market conditions... Fetching 24h volume data, order book depth, and historical volatility patterns",
    confidence: 0.95,
    timestamp: "124ms",
  },
  {
    id: 3,
    type: "reasoning",
    content: "Applying risk management constraints... Max drawdown: 10%, Position sizing: Kelly Criterion adjusted",
    confidence: 0.92,
    timestamp: "267ms",
  },
  {
    id: 4,
    type: "validation",
    content: "Cross-referencing with historical backtests... 847 similar scenarios analyzed",
    confidence: 0.88,
    timestamp: "445ms",
    isAnomaly: true,
  },
  {
    id: 5,
    type: "reasoning",
    content: "Strategy synthesis: DCA entry with trailing stop-loss at 8% below entry, take-profit at +15%",
    confidence: 0.91,
    timestamp: "589ms",
  },
  {
    id: 6,
    type: "output",
    content: "Final recommendation: Entry at $3,420, Stop-loss: $3,146, Take-profit: $3,933, Expected ROI: 12.4%",
    confidence: 0.89,
    timestamp: "623ms",
  },
];

const StepIcon = ({ type }: { type: LogicStep["type"] }) => {
  const icons = {
    input: FileText,
    reasoning: Brain,
    validation: GitBranch,
    output: Zap,
  };
  const Icon = icons[type];
  return <Icon className="w-4 h-4" />;
};

const LogicStepCard = ({ step, index, isExpanded, onToggle }: { 
  step: LogicStep; 
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="relative"
    >
      {/* Connection Line */}
      {index < mockLogicTrace.length - 1 && (
        <div className="absolute left-6 top-12 bottom-0 w-px bg-gradient-to-b from-border to-transparent" />
      )}
      
      <div
        onClick={onToggle}
        className={`
          relative p-4 rounded-xl border cursor-pointer transition-all duration-300
          ${step.isAnomaly 
            ? 'border-destructive/50 bg-destructive/5 hover:bg-destructive/10' 
            : 'border-border/50 bg-card/50 hover:bg-card/80 hover:border-primary/30'
          }
        `}
      >
        {/* Anomaly Warning */}
        {step.isAnomaly && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-2 -right-2"
          >
            <Badge variant="dispute" className="text-xs">
              <XCircle className="w-3 h-3 mr-1" />
              Anomaly Detected
            </Badge>
          </motion.div>
        )}

        <div className="flex items-start gap-4">
          {/* Step Number & Icon */}
          <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center border border-primary/30 bg-primary/10">
            <StepIcon type={step.type} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <Badge variant="outline" className="capitalize">
                {step.type}
              </Badge>
              <span className="text-xs font-mono text-muted-foreground">
                {step.timestamp}
              </span>
            </div>
            
            <p className={`text-sm ${isExpanded ? '' : 'line-clamp-2'}`}>
              {step.content}
            </p>

            {/* Confidence Bar */}
            <div className="mt-3 flex items-center gap-3">
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full ${
                    step.confidence >= 0.9 ? 'bg-success' : 
                    step.confidence >= 0.8 ? 'bg-warning' : 'bg-destructive'
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${step.confidence * 100}%` }}
                  transition={{ delay: index * 0.1 + 0.3, duration: 0.5 }}
                />
              </div>
              <span className="text-xs font-mono text-muted-foreground">
                {(step.confidence * 100).toFixed(0)}%
              </span>
              <ChevronRight 
                className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} 
              />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export const ForensicView = () => {
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  return (
    <section className="py-20 relative bg-gradient-to-b from-transparent via-card/30 to-transparent">
      <div className="container mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <Badge variant="gold" className="mb-4">
            <Code className="w-3 h-3 mr-1" />
            Forensic Analysis
          </Badge>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Chain of <span className="text-accent">Thought</span> Inspector
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Trace the complete logic path from prompt to response. Identify anomalies and validate reasoning integrity.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Logic Trace Timeline */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary" />
                Logic Trace Timeline
              </h3>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowComparison(!showComparison)}
              >
                <ArrowLeftRight className="w-4 h-4 mr-2" />
                Compare Outputs
              </Button>
            </div>

            <div className="space-y-4">
              {mockLogicTrace.map((step, index) => (
                <LogicStepCard
                  key={step.id}
                  step={step}
                  index={index}
                  isExpanded={expandedStep === step.id}
                  onToggle={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                />
              ))}
            </div>
          </div>

          {/* Evidence Summary Panel */}
          <div className="space-y-4">
            <Card variant="cyber" className="sticky top-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Fingerprint className="w-5 h-5 text-primary" />
                  Evidence Bundle
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* PoI Hash */}
                <div className="p-3 rounded-lg bg-muted/50 border border-border/50">
                  <div className="text-xs text-muted-foreground mb-1">Proof of Inference (PoI)</div>
                  <div className="font-mono text-xs text-primary break-all">
                    0x7a3f8b2c1d9e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9
                  </div>
                </div>

                {/* Model Info */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-muted/50 border border-border/50">
                    <div className="text-xs text-muted-foreground mb-1">Model</div>
                    <div className="font-mono text-sm">gemini-2.5-flash</div>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 border border-border/50">
                    <div className="text-xs text-muted-foreground mb-1">Latency</div>
                    <div className="font-mono text-sm">623ms</div>
                  </div>
                </div>

                {/* Validation Status */}
                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground">Validation Checks</div>
                  {[
                    { label: "Semantic Coherence", passed: true },
                    { label: "Factual Accuracy", passed: true },
                    { label: "Logic Consistency", passed: false },
                    { label: "Safety Filters", passed: true },
                  ].map((check, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                    >
                      <span className="text-sm">{check.label}</span>
                      {check.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      ) : (
                        <XCircle className="w-4 h-4 text-destructive" />
                      )}
                    </div>
                  ))}
                </div>

                {/* Actions */}
                <div className="pt-4 space-y-2">
                  <Button variant="challenge" className="w-full">
                    Initiate Challenge
                  </Button>
                  <Button variant="outline" className="w-full">
                    Download Evidence
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
};
