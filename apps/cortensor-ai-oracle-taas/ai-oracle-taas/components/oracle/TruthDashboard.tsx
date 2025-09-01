"use client"

import { motion } from "framer-motion"
import { TrendingUp, Users, Zap, Shield, Globe, Clock, CheckCircle, AlertTriangle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

const networkStats = [
  {
    icon: Shield,
    label: "Truth Accuracy",
    value: "99.2%",
    change: "+0.3%",
    color: "text-primary",
  },
  {
    icon: Users,
    label: "Active Miners",
    value: "52",
    change: "+4",
    color: "text-accent",
  },
  {
    icon: Clock,
    label: "Avg Response Time",
    value: "2.3s",
    change: "-0.2s",
    color: "text-primary",
  },
  {
    icon: TrendingUp,
    label: "Queries Today",
    value: "1,247",
    change: "+18%",
    color: "text-accent",
  },
]

const recentQueries = [
  {
    id: "1",
    query: "What is the current population of Tokyo?",
    status: "verified",
    confidence: 94,
    time: "2 min ago",
  },
  {
    id: "2",
    query: "Explain quantum computing principles",
    status: "verified",
    confidence: 89,
    time: "5 min ago",
  },
  {
    id: "3",
    query: "What will be the weather tomorrow in NYC?",
    status: "disputed",
    confidence: 67,
    time: "8 min ago",
  },
  {
    id: "4",
    query: "Calculate the square root of 144",
    status: "verified",
    confidence: 100,
    time: "12 min ago",
  },
]

const topMiners = [
  { id: "miner-1", reputation: 4.9, queries: 1247, accuracy: 98.5 },
  { id: "miner-2", reputation: 4.8, queries: 1156, accuracy: 97.8 },
  { id: "miner-3", reputation: 4.7, queries: 1089, accuracy: 97.2 },
  { id: "miner-4", reputation: 4.6, queries: 987, accuracy: 96.9 },
]

export function TruthDashboard() {
  return (
    <div className="space-y-8 bg-gradient-to-r from-blue-500 via-fuchsia-500 to-pink-500 p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
        <h2 className="text-3xl font-bold text-white mb-2">Network Dashboard</h2>
        <p className="text-white/70">Real-time insights into the Cortensor truth verification network</p>
      </motion.div>

      {/* Network Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {networkStats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: index * 0.1 }}
          >
            <Card className="bg-white/5 backdrop-blur-sm border-white/10 hover:border-white/20 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white/70">{stat.label}</p>
                    <p className="text-2xl font-bold text-white">{stat.value}</p>
                    <p
                      className={`text-sm bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400`}
                    >
                      {stat.change}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-white/5">
                    <stat.icon className="w-6 h-6 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Queries */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <Card className="bg-white/5 backdrop-blur-sm border-white/10">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Zap className="w-5 h-5 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
                Recent Queries
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {recentQueries.map((query, index) => (
                <motion.div
                  key={query.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start gap-3 p-3 bg-white/5 rounded-lg border border-white/10"
                >
                  <div className="flex-shrink-0 mt-1">
                    {query.status === "verified" ? (
                      <CheckCircle className="w-4 h-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate">{query.query}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge className="text-xs bg-white/10 text-white border-white/10">
                        {query.confidence}% confidence
                      </Badge>
                      <span className="text-xs text-white/60">{query.time}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Top Miners */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          <Card className="bg-white/5 backdrop-blur-sm border-white/10">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Globe className="w-5 h-5 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
                Top Miners
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {topMiners.map((miner, index) => (
                <motion.div
                  key={miner.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-white/10 rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-300 via-fuchsia-300 to-pink-300">
                        #{index + 1}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">Miner {index + 1}</p>
                      <p className="text-xs text-white/70">{miner.queries} queries</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1">
                      <span className="text-sm font-medium text-white">⭐ {miner.reputation}</span>
                    </div>
                    <div className="text-xs text-white/70">{miner.accuracy}% accuracy</div>
                  </div>
                </motion.div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Network Health */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.6 }}
      >
        <Card className="bg-white/5 backdrop-blur-sm border-white/10">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
              Network Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Consensus Rate</span>
                  <span className="text-white">94%</span>
                </div>
                <Progress value={94} className="h-2" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Network Uptime</span>
                  <span className="text-white">99.9%</span>
                </div>
                <Progress value={99.9} className="h-2" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Miner Availability</span>
                  <span className="text-white">87%</span>
                </div>
                <Progress value={87} className="h-2" />
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
