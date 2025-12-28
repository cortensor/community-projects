import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Scale, Shield, Zap, Eye, ArrowRight, Activity, Users, Gavel, Coins } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { networkStats } from "@/data/mockData";

const Index = () => {
  const stats = [
    { label: "Active Disputes", value: networkStats.activeDisputes, icon: Gavel },
    { label: "Validators Online", value: networkStats.onlineValidators, icon: Users },
    { label: "COR Staked", value: `${(networkStats.corStaked / 1000000).toFixed(1)}M`, icon: Coins },
    { label: "Success Rate", value: `${networkStats.successRate}%`, icon: Activity },
  ];

  const features = [
    { icon: Shield, title: "Validator Consensus", desc: "Multi-node validation with cryptographic proof" },
    { icon: Eye, title: "Forensic Analysis", desc: "Chain of Thought inspection and logic trace" },
    { icon: Zap, title: "Instant Challenges", desc: "Challenge AI outputs by staking COR tokens" },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main>
        {/* Hero Section */}
        <section className="py-20 lg:py-32">
          <div className="container mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Badge variant="outline" className="mb-6 px-4 py-1.5">
                <span className="w-2 h-2 rounded-full bg-success mr-2 animate-pulse" />
                Network Operational
              </Badge>
            </motion.div>

            <motion.h1 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6"
            >
              <span className="text-foreground">The </span>
              <span className="gradient-text">Cortensor</span>
              <span className="text-foreground"> Judge</span>
            </motion.h1>

            <motion.div 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              transition={{ delay: 0.2 }}
              className="flex justify-center mb-8"
            >
              <Scale className="w-16 h-16 text-primary" />
            </motion.div>

            <motion.p 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              transition={{ delay: 0.3 }}
              className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10"
            >
              Decentralized dispute resolution for AI agents. Challenge outputs, 
              initiate trials via validator consensus, and settle justice on-chain.
            </motion.p>

            <motion.div 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              transition={{ delay: 0.4 }}
              className="flex flex-col sm:flex-row gap-4 justify-center"
            >
              <Link to="/courtroom">
                <Button size="lg" className="gap-2 w-full sm:w-auto">
                  <Zap className="w-5 h-5" />
                  Enter Courtroom
                </Button>
              </Link>
              <Link to="/cases">
                <Button variant="outline" size="lg" className="gap-2 w-full sm:w-auto">
                  <Eye className="w-5 h-5" />
                  View Cases
                </Button>
              </Link>
            </motion.div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-16 bg-muted/30">
          <div className="container mx-auto px-4 sm:px-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {stats.map((stat, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className="text-center">
                    <CardContent className="p-6">
                      <stat.icon className="w-8 h-8 text-primary mx-auto mb-3" />
                      <p className="text-3xl font-bold mb-1">{stat.value}</p>
                      <p className="text-sm text-muted-foreground">{stat.label}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-20">
          <div className="container mx-auto px-4 sm:px-6">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-12"
            >
              <h2 className="text-3xl font-bold mb-4">Core Features</h2>
              <p className="text-muted-foreground max-w-xl mx-auto">
                A complete ecosystem for AI accountability
              </p>
            </motion.div>

            <div className="grid md:grid-cols-3 gap-6">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className="h-full hover:shadow-card transition-shadow">
                    <CardContent className="p-6">
                      <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                        <feature.icon className="w-6 h-6 text-primary" />
                      </div>
                      <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                      <p className="text-muted-foreground text-sm">{feature.desc}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mt-12"
            >
              <Link to="/docs">
                <Button variant="outline" className="gap-2">
                  Learn More
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </motion.div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default Index;