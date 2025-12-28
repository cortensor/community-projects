import { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { 
  Activity, 
  Users, 
  Cpu, 
  Coins,
  Gavel,
  Clock,
  TrendingUp,
  ArrowRight,
  Scale,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Search
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { mockDisputes, networkStats, mockVerdicts, type Dispute } from "@/data/mockData";
import { useWallet } from "@/hooks/useWallet";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { toast } from "sonner";

const StatusBadge = ({ status }: { status: Dispute["status"] }) => {
  const config = {
    pending: { className: "bg-warning/10 text-warning border-warning/20", icon: Clock, label: "Pending" },
    active: { className: "bg-primary/10 text-primary border-primary/20", icon: AlertTriangle, label: "Active" },
    resolved: { className: "bg-success/10 text-success border-success/20", icon: CheckCircle2, label: "Resolved" },
    slashed: { className: "bg-destructive/10 text-destructive border-destructive/20", icon: AlertTriangle, label: "Slashed" },
  };
  const { className, icon: Icon, label } = config[status];
  return (
    <Badge variant="outline" className={className}>
      <Icon className="w-3 h-3 mr-1" />
      {label}
    </Badge>
  );
};

const Courtroom = () => {
  const [filter, setFilter] = useState<"all" | "active" | "pending" | "resolved" | "slashed">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const { isConnected, openConnectModal } = useWallet();

  const filteredDisputes = mockDisputes.filter(d => {
    const matchesFilter = filter === "all" || d.status === filter;
    const matchesSearch = searchQuery === "" || 
      d.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.model.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleInitiateChallenge = () => {
    if (!isConnected) {
      toast.error("Please connect your wallet first");
      return;
    }
    toast.success("Challenge initiated! Awaiting validator consensus...");
  };

  const stats = [
    { label: "Active Disputes", value: networkStats.activeDisputes, icon: Gavel, trend: "+12" },
    { label: "Online Validators", value: networkStats.onlineValidators, icon: Users, trend: "+8" },
    { label: "Network Miners", value: networkStats.totalMiners, icon: Cpu, trend: "-3" },
    { label: "COR Staked", value: `${(networkStats.corStaked / 1000000).toFixed(1)}M`, icon: Coins, trend: "+5%" },
  ];

  const filters = [
    { key: "all", label: "All Cases", count: mockDisputes.length },
    { key: "active", label: "Active", count: mockDisputes.filter(d => d.status === "active").length },
    { key: "pending", label: "Pending", count: mockDisputes.filter(d => d.status === "pending").length },
    { key: "resolved", label: "Resolved", count: mockDisputes.filter(d => d.status === "resolved").length },
    { key: "slashed", label: "Slashed", count: mockDisputes.filter(d => d.status === "slashed").length },
  ];

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
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                <Scale className="w-8 h-8 text-primary" />
                Courtroom
              </h1>
              <p className="text-muted-foreground mt-1">Real-time AI dispute resolution dashboard</p>
            </div>
            {isConnected ? (
              <Button onClick={handleInitiateChallenge} className="gap-2">
                <Gavel className="w-4 h-4" />
                Initiate Challenge
              </Button>
            ) : (
              <Button onClick={openConnectModal} className="gap-2">
                Connect to Challenge
              </Button>
            )}
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
        >
          {stats.map((stat, index) => (
            <Card key={index} className="border-border">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <p className="text-2xl font-bold mt-1">{stat.value}</p>
                    <p className="text-xs text-success flex items-center gap-1 mt-1">
                      <TrendingUp className="w-3 h-3" />
                      {stat.trend}
                    </p>
                  </div>
                  <div className="p-2 rounded-lg bg-primary/10">
                    <stat.icon className="w-5 h-5 text-primary" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </motion.div>

        {/* Filters and Search */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-4 mb-6"
        >
          <div className="flex flex-wrap gap-2">
            {filters.map((f) => (
              <Button
                key={f.key}
                variant={filter === f.key ? "default" : "outline"}
                size="sm"
                onClick={() => setFilter(f.key as typeof filter)}
                className="gap-1"
              >
                {f.label}
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  filter === f.key ? "bg-primary-foreground/20" : "bg-muted"
                }`}>
                  {f.count}
                </span>
              </Button>
            ))}
          </div>
          <div className="relative flex-1 max-w-xs ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search cases..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </motion.div>

        {/* Disputes Grid */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="grid md:grid-cols-2 gap-4"
        >
          {filteredDisputes.map((dispute, index) => (
            <motion.div
              key={dispute.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * index }}
            >
              <Card className="h-full hover:shadow-card transition-shadow card-hover">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <p className="font-mono font-semibold text-foreground">{dispute.id}</p>
                      <p className="text-xs text-muted-foreground">{dispute.model} • {dispute.timestamp}</p>
                    </div>
                    <StatusBadge status={dispute.status} />
                  </div>
                  
                  <p className="text-sm text-muted-foreground mb-4">{dispute.description}</p>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Similarity Score</span>
                      <span className={`font-mono ${
                        dispute.similarity < 0.8 ? "text-destructive" : 
                        dispute.similarity < 0.95 ? "text-warning" : "text-success"
                      }`}>
                        {(dispute.similarity * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${
                          dispute.similarity < 0.8 ? "bg-destructive" : 
                          dispute.similarity < 0.95 ? "bg-warning" : "bg-success"
                        }`}
                        style={{ width: `${dispute.similarity * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                    <div>
                      <p className="text-xs text-muted-foreground">Bond Staked</p>
                      <p className="font-mono font-semibold text-primary">{dispute.bondAmount}</p>
                    </div>
                    <Link to={`/cases/${dispute.id}`}>
                      <Button variant="outline" size="sm" className="gap-1">
                        View Details
                        <ArrowRight className="w-3 h-3" />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {filteredDisputes.length === 0 && (
          <div className="text-center py-12">
            <Shield className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">No cases found matching your criteria</p>
          </div>
        )}

        {/* Recent Verdicts */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-12"
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Gavel className="w-5 h-5 text-primary" />
                Recent Verdicts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockVerdicts.slice(0, 5).map((verdict) => (
                  <div 
                    key={verdict.id}
                    className={`flex items-center justify-between p-3 rounded-lg ${
                      verdict.result === "slashed" ? "bg-destructive/5" : "bg-success/5"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${
                        verdict.result === "slashed" ? "bg-destructive" : "bg-success"
                      }`} />
                      <div>
                        <p className="font-mono text-sm">{verdict.id}</p>
                        <p className="text-xs text-muted-foreground">{verdict.timestamp}</p>
                      </div>
                    </div>
                    <span className={`font-mono font-semibold ${
                      verdict.result === "slashed" ? "text-destructive" : "text-success"
                    }`}>
                      {verdict.amount}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </main>

      <Footer />
    </div>
  );
};

export default Courtroom;