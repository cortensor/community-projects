import { useState } from "react";
import { motion } from "framer-motion";
import { 
  BookOpen, 
  Search,
  ChevronRight,
  Code,
  Shield,
  Gavel,
  Cpu,
  Coins,
  FileText,
  ExternalLink,
  Copy,
  Check
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { toast } from "sonner";

const Docs = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const sections = [
    {
      id: "getting-started",
      title: "Getting Started",
      icon: BookOpen,
      items: [
        { title: "Introduction to Cortensor Judge", href: "#intro" },
        { title: "How Dispute Resolution Works", href: "#how-it-works" },
        { title: "Understanding Validators", href: "#validators" },
        { title: "COR Token Economics", href: "#tokenomics" },
      ]
    },
    {
      id: "api",
      title: "API Reference",
      icon: Code,
      items: [
        { title: "Authentication", href: "#auth" },
        { title: "Disputes Endpoint", href: "#disputes-api" },
        { title: "Validators Endpoint", href: "#validators-api" },
        { title: "Webhooks", href: "#webhooks" },
      ]
    },
    {
      id: "security",
      title: "Security",
      icon: Shield,
      items: [
        { title: "Smart Contract Audits", href: "#audits" },
        { title: "Bug Bounty Program", href: "#bug-bounty" },
        { title: "Best Practices", href: "#best-practices" },
      ]
    },
  ];

  const faqs = [
    {
      question: "What is Cortensor Judge?",
      answer: "Cortensor Judge is a decentralized dispute resolution system for AI inference networks. It allows users to challenge AI outputs, subjects them to validation via validator consensus, and settles rewards/slashing on-chain using COR tokens."
    },
    {
      question: "How do I become a validator?",
      answer: "To become a validator, you need to stake a minimum of 10,000 COR tokens and meet the hardware requirements for running a validation node. Connect your wallet and apply through the Validators page."
    },
    {
      question: "What happens when I initiate a challenge?",
      answer: "When you initiate a challenge, you stake COR tokens as a bond. The disputed output is then reviewed by multiple validators who compare it against expected outputs using cosine similarity. If the challenge is successful, you receive rewards; if not, your bond may be slashed."
    },
    {
      question: "How is similarity score calculated?",
      answer: "Similarity scores are calculated using cosine similarity between vector embeddings of multiple miner outputs. Scores below 95% trigger a challenge flag, and scores below 80% typically result in miner slashing."
    },
    {
      question: "What are the staking requirements?",
      answer: "Challengers must stake a minimum bond of 100 COR per dispute. Validators require a minimum stake of 10,000 COR. Higher stakes provide higher rewards but also higher risk of slashing."
    },
  ];

  const codeExample = `// Initialize Cortensor Judge Client
import { CortensorJudge } from '@cortensor/judge-sdk';

const judge = new CortensorJudge({
  apiKey: 'your-api-key',
  network: 'mainnet'
});

// Initiate a challenge
const challenge = await judge.initiateChallenge({
  taskId: 'TASK-8291',
  reason: 'Inconsistent output detected',
  bond: 500 // COR tokens
});

console.log('Challenge ID:', challenge.id);`;

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    toast.success("Code copied to clipboard");
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="container mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-primary" />
            Documentation
          </h1>
          <p className="text-muted-foreground mt-1">Learn how to use Cortensor Judge</p>
        </motion.div>

        {/* Search */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <div className="relative max-w-xl">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search documentation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-1"
          >
            <div className="sticky top-24 space-y-6">
              {sections.map((section) => (
                <div key={section.id}>
                  <h3 className="font-semibold text-sm text-foreground flex items-center gap-2 mb-3">
                    <section.icon className="w-4 h-4 text-primary" />
                    {section.title}
                  </h3>
                  <ul className="space-y-2">
                    {section.items.map((item) => (
                      <li key={item.href}>
                        <a 
                          href={item.href}
                          className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-1"
                        >
                          <ChevronRight className="w-3 h-3" />
                          {item.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Main Content */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="lg:col-span-3 space-y-8"
          >
            {/* Overview Cards */}
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { icon: Gavel, title: "Dispute Resolution", desc: "Learn how to challenge AI outputs" },
                { icon: Shield, title: "Become a Validator", desc: "Stake COR and validate disputes" },
                { icon: Cpu, title: "Integration Guide", desc: "Connect your AI systems" },
                { icon: Coins, title: "Token Economics", desc: "Understand COR tokenomics" },
              ].map((card, index) => (
                <Card key={index} className="hover:shadow-card transition-shadow cursor-pointer">
                  <CardContent className="p-5">
                    <div className="flex items-start gap-4">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <card.icon className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{card.title}</h3>
                        <p className="text-sm text-muted-foreground">{card.desc}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Quick Start */}
            <Card id="intro">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="w-5 h-5 text-primary" />
                  Quick Start
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  Get started with Cortensor Judge SDK in just a few lines of code.
                </p>
                <div className="relative">
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono">
                    <code>{codeExample}</code>
                  </pre>
                  <button
                    onClick={() => handleCopyCode(codeExample)}
                    className="absolute top-3 right-3 p-2 rounded-md bg-background/80 hover:bg-background transition-colors"
                  >
                    {copiedCode === codeExample ? (
                      <Check className="w-4 h-4 text-success" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
                <div className="mt-4 flex items-center gap-4">
                  <Badge variant="outline">npm install @cortensor/judge-sdk</Badge>
                  <a href="#" className="text-sm text-primary hover:underline flex items-center gap-1">
                    View on GitHub
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </CardContent>
            </Card>

            {/* FAQs */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  Frequently Asked Questions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Accordion type="single" collapsible className="w-full">
                  {faqs.map((faq, index) => (
                    <AccordionItem key={index} value={`item-${index}`}>
                      <AccordionTrigger className="text-left">
                        {faq.question}
                      </AccordionTrigger>
                      <AccordionContent className="text-muted-foreground">
                        {faq.answer}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </CardContent>
            </Card>

            {/* Help Card */}
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="p-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="font-semibold mb-1">Need more help?</h3>
                    <p className="text-sm text-muted-foreground">
                      Join our Discord community for support and discussions
                    </p>
                  </div>
                  <a 
                    href="https://discord.com" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    Join Discord
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Docs;