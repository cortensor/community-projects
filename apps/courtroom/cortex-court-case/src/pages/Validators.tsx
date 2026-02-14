import { useState } from "react";
import { motion } from "framer-motion";
import { 
  Shield, 
  Search,
  Crown,
  Activity,
  Clock,
  CheckCircle2,
  TrendingUp,
  Users
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { mockValidators, networkStats } from "@/data/mockData";
import { useWallet } from "@/hooks/useWallet";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { toast } from "sonner";

const Validators = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [showOnlineOnly, setShowOnlineOnly] = useState(false);
  const { isConnected, openConnectModal } = useWallet();

  const filteredValidators = mockValidators.filter(v => {
    const matchesSearch = searchQuery === "" || 
      v.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
      v.name?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesOnline = !showOnlineOnly || v.status === "online";
    return matchesSearch && matchesOnline;
  });

  const handleBecomeValidator = () => {
    if (!isConnected) {
      toast.error("Please connect your wallet first");
      return;
    }
    toast.success("Validator application submitted!");
  };

  const stats = [
    { label: "Total Validators", value: networkStats.totalValidators, icon: Users },
    { label: "Online Now", value: networkStats.onlineValidators, icon: Activity },
    { label: "Success Rate", value: `${networkStats.successRate}%`, icon: CheckCircle2 },
    { label: "Avg Resolution", value: networkStats.averageResolutionTime, icon: Clock },
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
                <Shield className="w-8 h-8 text-primary" />
                Validators
              </h1>
              <p className="text-muted-foreground mt-1">View and monitor network validators</p>
            </div>
            {isConnected ? (
              <Button onClick={handleBecomeValidator} className="gap-2">
                <Shield className="w-4 h-4" />
                Become a Validator
              </Button>
            ) : (
              <Button onClick={openConnectModal} className="gap-2">
                Connect to Apply
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
            <Card key={index}>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <stat.icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </motion.div>

        {/* Filters */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-4 mb-6"
        >
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search validators..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button
            variant={showOnlineOnly ? "default" : "outline"}
            onClick={() => setShowOnlineOnly(!showOnlineOnly)}
            className="gap-2"
          >
            <Activity className="w-4 h-4" />
            Online Only
          </Button>
        </motion.div>

        {/* Validators List */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Leaderboard</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {filteredValidators.map((validator, index) => (
                  <motion.div
                    key={validator.address}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 * index }}
                    className="flex items-center gap-4 p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    {/* Rank */}
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold ${
                      validator.rank === 1 ? "bg-accent/20 text-accent" :
                      validator.rank === 2 ? "bg-muted-foreground/20 text-muted-foreground" :
                      validator.rank === 3 ? "bg-warning/20 text-warning" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {validator.rank === 1 && <Crown className="w-5 h-5" />}
                      {validator.rank !== 1 && `#${validator.rank}`}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold truncate">
                          {validator.name || `${validator.address.slice(0, 6)}...${validator.address.slice(-4)}`}
                        </p>
                        <Badge variant={validator.status === "online" ? "default" : "secondary"} className="text-xs">
                          {validator.status === "online" ? (
                            <><span className="w-1.5 h-1.5 rounded-full bg-success mr-1" /> Online</>
                          ) : (
                            <><span className="w-1.5 h-1.5 rounded-full bg-muted-foreground mr-1" /> Offline</>
                          )}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground font-mono truncate">{validator.address}</p>
                    </div>

                    {/* Stats */}
                    <div className="hidden md:flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-sm font-semibold">{validator.disputes}</p>
                        <p className="text-xs text-muted-foreground">Disputes</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-success flex items-center gap-1">
                          <TrendingUp className="w-3 h-3" />
                          {validator.accuracy}%
                        </p>
                        <p className="text-xs text-muted-foreground">Accuracy</p>
                      </div>
                      <div className="text-right w-24">
                        <p className="text-sm font-semibold text-primary">{validator.stake} COR</p>
                        <p className="text-xs text-muted-foreground">Staked</p>
                      </div>
                      <div className="w-24">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground">Uptime</span>
                          <span>{validator.uptime}%</span>
                        </div>
                        <Progress value={validator.uptime} className="h-1.5" />
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {filteredValidators.length === 0 && (
          <div className="text-center py-12">
            <Shield className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">No validators found</p>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
};

export default Validators;