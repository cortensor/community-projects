import { motion } from "framer-motion";
import { 
  Activity, 
  TrendingUp, 
  TrendingDown,
  Users,
  Cpu,
  Coins,
  Shield,
  Gavel,
  BarChart3,
  Clock
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  trend?: "up" | "down" | "neutral";
  icon: React.ElementType;
  delay?: number;
}

const StatCard = ({ title, value, change, trend, icon: Icon, delay = 0 }: StatCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay }}
    whileHover={{ scale: 1.02 }}
  >
    <Card variant="cyber" className="h-full">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold font-mono text-foreground">{value}</p>
            {change && (
              <div className="flex items-center gap-1 text-sm">
                {trend === "up" && <TrendingUp className="w-4 h-4 text-success" />}
                {trend === "down" && <TrendingDown className="w-4 h-4 text-destructive" />}
                <span className={trend === "up" ? "text-success" : trend === "down" ? "text-destructive" : "text-muted-foreground"}>
                  {change}
                </span>
              </div>
            )}
          </div>
          <div className="p-3 rounded-xl bg-primary/10 border border-primary/20">
            <Icon className="w-6 h-6 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  </motion.div>
);

const ActivityBar = ({ height, delay }: { height: number; delay: number }) => (
  <motion.div
    className="w-full bg-muted rounded-t-sm overflow-hidden"
    initial={{ scaleY: 0 }}
    whileInView={{ scaleY: 1 }}
    viewport={{ once: true }}
    transition={{ delay, duration: 0.5, ease: "easeOut" }}
    style={{ transformOrigin: "bottom", height: `${height}%` }}
  >
    <div className="w-full h-full bg-gradient-to-t from-primary/80 to-primary/40" />
  </motion.div>
);

const NetworkActivityChart = () => {
  const bars = [45, 72, 58, 85, 42, 95, 68, 78, 55, 88, 62, 75, 48, 82, 91, 55, 70, 65, 88, 52];
  
  return (
    <Card variant="cyber">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            Network Activity (24h)
          </CardTitle>
          <Badge variant="success" className="font-mono">
            <Activity className="w-3 h-3 mr-1" />
            Live
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-1 h-32 pt-4">
          {bars.map((height, index) => (
            <ActivityBar key={index} height={height} delay={index * 0.03} />
          ))}
        </div>
        <div className="flex justify-between mt-2 text-xs text-muted-foreground font-mono">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>Now</span>
        </div>
      </CardContent>
    </Card>
  );
};

const TopValidators = () => {
  const validators = [
    { rank: 1, address: "0x742d...8f21", disputes: 847, accuracy: 99.4, stake: "125K" },
    { rank: 2, address: "0x9a1c...3e45", disputes: 721, accuracy: 98.9, stake: "98K" },
    { rank: 3, address: "0x3f8e...2a91", disputes: 654, accuracy: 98.7, stake: "87K" },
  ];

  return (
    <Card variant="cyber">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="w-5 h-5 text-accent" />
          Top Validators
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {validators.map((v, index) => (
            <motion.div
              key={v.rank}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-4 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${v.rank === 1 ? 'bg-accent/20 text-accent' : 'bg-muted text-muted-foreground'}`}>
                #{v.rank}
              </div>
              <div className="flex-1">
                <div className="font-mono text-sm">{v.address}</div>
                <div className="text-xs text-muted-foreground">{v.disputes} disputes</div>
              </div>
              <div className="text-right">
                <div className="font-mono text-sm text-accent">{v.stake} COR</div>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

const RecentVerdicts = () => {
  const verdicts = [
    { id: "VRD-8291", result: "slashed", amount: "-500 COR", time: "2m ago" },
    { id: "VRD-8290", result: "cleared", amount: "+50 COR", time: "5m ago" },
    { id: "VRD-8289", result: "slashed", amount: "-750 COR", time: "8m ago" },
  ];

  return (
    <Card variant="cyber">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Gavel className="w-5 h-5 text-primary" />
          Recent Verdicts
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {verdicts.map((v, index) => (
            <motion.div
              key={v.id}
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className={`flex items-center justify-between p-3 rounded-lg border ${v.result === "slashed" ? 'bg-destructive/5 border-destructive/30' : 'bg-success/5 border-success/30'}`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${v.result === "slashed" ? 'bg-destructive' : 'bg-success'}`} />
                <div className="font-mono text-sm">{v.id}</div>
              </div>
              <div className="text-right">
                <div className={`font-mono text-sm font-semibold ${v.result === "slashed" ? 'text-destructive' : 'text-success'}`}>{v.amount}</div>
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" />{v.time}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export const StatsDashboard = () => {
  const stats = [
    { title: "Total Disputes", value: "12,847", change: "+127 today", trend: "up" as const, icon: Gavel },
    { title: "Active Validators", value: "342", change: "+8 online", trend: "up" as const, icon: Users },
    { title: "Network Miners", value: "1,247", change: "-3 this hour", trend: "down" as const, icon: Cpu },
    { title: "COR Staked", value: "2.4M", change: "$4.2M TVL", trend: "neutral" as const, icon: Coins },
  ];

  return (
    <section className="py-20 relative">
      <div className="container mx-auto px-6">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-12">
          <Badge variant="cyber" className="mb-4"><Activity className="w-3 h-3 mr-1" />Network Stats</Badge>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Justice <span className="text-primary">Network</span> Overview</h2>
        </motion.div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {stats.map((stat, index) => (<StatCard key={stat.title} {...stat} delay={index * 0.1} />))}
        </div>
        <div className="mb-8"><NetworkActivityChart /></div>
        <div className="grid lg:grid-cols-2 gap-4"><TopValidators /><RecentVerdicts /></div>
      </div>
    </section>
  );
};
