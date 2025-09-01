import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Shield, 
  TrendingUp, 
  Clock, 
  AlertTriangle,
  CheckCircle,
  Zap,
  Users,
  BarChart3
} from 'lucide-react';
import { ClaimInput } from '@/components/dashboard/ClaimInput';
import { useAppStore } from '@/store/useAppStore';
import { format } from 'date-fns';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

export default function Dashboard() {
  const { factChecks, currentAnalysis } = useAppStore();
  
  const currentFactCheck = currentAnalysis 
    ? factChecks.find(f => f.id === currentAnalysis)
    : null;

  const completedChecks = factChecks.filter(f => f.status === 'completed');
  const analyzingChecks = factChecks.filter(f => f.status === 'analyzing');
  const credibleChecks = completedChecks.filter(f => f.credibilityScore && f.credibilityScore >= 0.7);
  const suspiciousChecks = completedChecks.filter(f => f.credibilityScore && f.credibilityScore < 0.4);

  const avgCredibilityScore = completedChecks.length > 0
    ? completedChecks.reduce((sum, check) => sum + (check.credibilityScore || 0), 0) / completedChecks.length
    : 0;

  return (
    <div className="min-h-screen p-6 space-y-8 cyber-grid">
      {/* Header */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-2"
      >
        <motion.div variants={item}>
          <h1 className="text-4xl font-bold gradient-text mb-2">
            TruthLens Dashboard
          </h1>
          <p className="text-lg text-muted-foreground">
            AI-powered fact-checking through decentralized consensus
          </p>
        </motion.div>
      </motion.div>

      {/* Stats Overview */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        <motion.div variants={item}>
          <Card className="card-cyber">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Checks</p>
                  <p className="text-3xl font-bold text-primary">{factChecks.length}</p>
                </div>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <Shield className="w-6 h-6 text-primary" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <TrendingUp className="w-3 h-3 text-green-500 mr-1" />
                <span className="text-green-500">+12%</span>
                <span className="text-muted-foreground ml-1">vs last week</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className="card-cyber">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Credible Claims</p>
                  <p className="text-3xl font-bold text-accent">{credibleChecks.length}</p>
                </div>
                <div className="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-accent" />
                </div>
              </div>
              <div className="mt-4">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Avg. Score</span>
                  <span className="font-medium">{(avgCredibilityScore * 100).toFixed(1)}%</span>
                </div>
                <Progress value={avgCredibilityScore * 100} className="h-2" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className="card-cyber">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Processing</p>
                  <p className="text-3xl font-bold text-yellow-500">{analyzingChecks.length}</p>
                </div>
                <div className="w-12 h-12 bg-yellow-500/10 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-yellow-500" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <Zap className="w-3 h-3 text-yellow-500 mr-1" />
                <span className="text-muted-foreground">AI miners active</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className="card-cyber">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Suspicious</p>
                  <p className="text-3xl font-bold text-destructive">{suspiciousChecks.length}</p>
                </div>
                <div className="w-12 h-12 bg-destructive/10 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-destructive" />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <span className="text-muted-foreground">Requires attention</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Claim Input */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="xl:col-span-2"
        >
          <ClaimInput />
        </motion.div>

        {/* Current Analysis & Recent Activity */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-6"
        >
          {/* Current Analysis */}
          {currentFactCheck && (
            <Card className="card-cyber">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  Current Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Claim</p>
                  <p className="font-medium">{currentFactCheck.claim.substring(0, 100)}...</p>
                </div>
                
                <div className="flex items-center justify-between">
                  <Badge className={`status-${
                    currentFactCheck.status === 'completed' ? 'secure' : 
                    currentFactCheck.status === 'analyzing' ? 'warning' : 'danger'
                  }`}>
                    {currentFactCheck.status}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {format(currentFactCheck.checkedAt, 'MMM d, h:mm a')}
                  </span>
                </div>

                {currentFactCheck.credibilityScore !== undefined && (
                  <div>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Credibility Score</span>
                      <span className="font-medium">
                        {(currentFactCheck.credibilityScore * 100).toFixed(1)}%
                      </span>
                    </div>
                    <Progress 
                      value={currentFactCheck.credibilityScore * 100} 
                      className="h-2"
                    />
                  </div>
                )}

                {currentFactCheck.analysis && (
                  <div className="pt-4 border-t border-border/40">
                    <p className="text-sm text-muted-foreground mb-2">AI Consensus</p>
                    <p className="text-sm">{currentFactCheck.analysis.consensus}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Recent Activity */}
          <Card className="card-cyber">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary" />
                Recent Activity
              </CardTitle>
              <CardDescription>
                Latest fact-checking results
              </CardDescription>
            </CardHeader>
            <CardContent>
              {completedChecks.slice(0, 5).length > 0 ? (
                <div className="space-y-4">
                  {completedChecks.slice(0, 5).map((check) => (
                    <div key={check.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        check.credibilityScore && check.credibilityScore >= 0.7 ? 'bg-accent' :
                        check.credibilityScore && check.credibilityScore >= 0.4 ? 'bg-yellow-500' :
                        'bg-destructive'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate mb-1">
                          {check.claim.substring(0, 60)}...
                        </p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{format(check.checkedAt, 'MMM d, h:mm a')}</span>
                          {check.credibilityScore && (
                            <Badge variant="outline" className="text-xs">
                              {(check.credibilityScore * 100).toFixed(0)}% credible
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Users className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">
                    No completed analyses yet
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}