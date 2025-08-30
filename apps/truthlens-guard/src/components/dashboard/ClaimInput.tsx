import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Zap, Shield, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useAppStore, FactCheck } from '@/store/useAppStore';
import { truthLensApi } from '@/services/api';
import { toast } from 'sonner';

export const ClaimInput: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'text' | 'url'>('text');
  const [textClaim, setTextClaim] = useState('');
  const [urlClaim, setUrlClaim] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [backendStatus, setBackendStatus] = useState<{
    connected: boolean;
    miners: number;
    lastCheck: string | null;
  } | null>(null);
  
  const { addFactCheck, setCurrentAnalysis, updateFactCheck } = useAppStore();

  // Check backend status on component mount
  React.useEffect(() => {
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    try {
      const status = await truthLensApi.getStatus();
      setBackendStatus({
        connected: status.cortensorConnected,
        miners: status.availableMiners,
        lastCheck: status.lastHealthCheck
      });
    } catch (error) {
      console.error('Failed to check backend status:', error);
      setBackendStatus({
        connected: false,
        miners: 0,
        lastCheck: null
      });
    }
  };

  const handleAnalyze = async () => {
    const claim = activeTab === 'text' ? textClaim : urlClaim;
    
    if (!claim.trim()) {
      toast.error('Please enter a claim to analyze');
      return;
    }

    if (claim.length < 10) {
      toast.error('Please enter a more detailed claim (at least 10 characters)');
      return;
    }

    setIsAnalyzing(true);

    // Create new fact check entry
    const factCheck: FactCheck = {
      id: Date.now().toString(),
      claim: claim.trim(),
      type: activeTab === 'url' ? 'url' : 'text',
      source: activeTab === 'url' ? urlClaim : undefined,
      checkedAt: new Date(),
      status: 'analyzing'
    };

    addFactCheck(factCheck);
    setCurrentAnalysis(factCheck.id);

    try {
      // Call the real TruthLens API
      const analysisResult = await truthLensApi.analyzeClaim({
        claim: claim.trim(),
        type: activeTab,
        options: {
          minMiners: 3,
          timeout: 30000
        }
      });

      // Update the fact check with real results
      updateFactCheck(factCheck.id, {
        status: 'completed',
        credibilityScore: analysisResult.credibilityScore,
        analysis: {
          isCredible: analysisResult.isCredible,
          confidence: analysisResult.confidence,
          consensus: analysisResult.consensus,
          supportingSources: analysisResult.supportingSources,
          minerResponses: analysisResult.minerResponses
        }
      });

      // Clear input
      if (activeTab === 'text') {
        setTextClaim('');
      } else {
        setUrlClaim('');
      }

      toast.success(
        analysisResult.isCredible 
          ? '✅ Analysis complete! Claim appears credible.' 
          : '⚠️ Analysis complete! Claim requires verification.'
      );

    } catch (error) {
      console.error('Analysis failed:', error);
      
      // Update fact check with error status
      updateFactCheck(factCheck.id, {
        status: 'error'
      });

      const errorMessage = error instanceof Error ? error.message : 'Analysis failed';
      toast.error(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <Card className="card-cyber p-8">
        {/* Backend Status Indicator */}
        <div className="flex justify-between items-center mb-6">
          <div className="text-center flex-1">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-primary mb-4"
            >
              <Shield className="w-10 h-10 text-background" />
            </motion.div>
            
            <h2 className="text-2xl font-bold gradient-text mb-2">
              TruthLens AI Analyzer
            </h2>
            <p className="text-muted-foreground">
              Verify claims using decentralized AI consensus
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              {backendStatus?.connected ? (
                <Wifi className="w-4 h-4 text-green-500" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <Badge 
                variant={backendStatus?.connected ? "default" : "destructive"}
                className="text-xs"
              >
                {backendStatus?.connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            
            {backendStatus?.connected && (
              <div className="text-xs text-muted-foreground">
                {backendStatus.miners} miners available
              </div>
            )}
            
            <Button
              variant="ghost"
              size="sm"
              onClick={checkBackendStatus}
              className="text-xs"
            >
              Refresh Status
            </Button>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'text' | 'url')}>
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="text" className="flex items-center gap-2">
              <Search className="w-4 h-4" />
              Text Claim
            </TabsTrigger>
            <TabsTrigger value="url" className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              URL Analysis
            </TabsTrigger>
          </TabsList>

          <TabsContent value="text" className="space-y-4">
            <Textarea
              placeholder="Enter a claim, headline, or statement to fact-check... (e.g., 'Climate change is caused by human activities' or 'A new study shows that coffee reduces heart disease risk')"
              value={textClaim}
              onChange={(e) => setTextClaim(e.target.value)}
              className="min-h-[120px] bg-muted/50 border-border/50 focus:border-primary/50"
              maxLength={1000}
            />
            <div className="text-sm text-muted-foreground text-right">
              {textClaim.length}/1000 characters
            </div>
          </TabsContent>

          <TabsContent value="url" className="space-y-4">
            <Input
              placeholder="https://example.com/article-to-verify"
              value={urlClaim}
              onChange={(e) => setUrlClaim(e.target.value)}
              className="bg-muted/50 border-border/50 focus:border-primary/50"
            />
            <p className="text-sm text-muted-foreground">
              Analyze articles, social media posts, or news content from any URL
            </p>
          </TabsContent>
        </Tabs>

        <div className="flex justify-center mt-8">
          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !backendStatus?.connected}
            className="btn-cyber px-8 py-3 text-lg min-w-[200px]"
            size="lg"
          >
            {isAnalyzing ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="flex items-center gap-2"
              >
                <Zap className="w-5 h-5" />
                Analyzing...
              </motion.div>
            ) : (
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                {backendStatus?.connected ? 'Verify with AI' : 'Backend Offline'}
              </div>
            )}
          </Button>
        </div>

        {!backendStatus?.connected && (
          <div className="mt-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center gap-2 text-destructive mb-2">
              <WifiOff className="w-4 h-4" />
              <span className="font-medium">Backend Connection Failed</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Unable to connect to the TruthLens backend API. Please ensure the backend server is running on port 3001.
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              Run: <code className="bg-muted px-1 rounded">npm run dev</code> in the backend directory
            </p>
          </div>
        )}

        {isAnalyzing && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 p-6 bg-muted/30 rounded-lg border border-primary/20"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
              <span className="text-sm font-medium text-primary">
                AI Miners Processing via Cortensor Network...
              </span>
            </div>
            
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <div className="w-1 h-1 bg-accent rounded-full animate-pulse" />
                Distributing query to decentralized miners
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1 h-1 bg-accent rounded-full animate-pulse" />
                Cross-referencing with trusted sources
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1 h-1 bg-accent rounded-full animate-pulse" />
                Building consensus from multiple AI agents
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1 h-1 bg-accent rounded-full animate-pulse" />
                Aggregating results and calculating credibility score
              </div>
            </div>
          </motion.div>
        )}
      </Card>
    </div>
  );
};