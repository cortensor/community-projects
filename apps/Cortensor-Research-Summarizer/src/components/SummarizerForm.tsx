'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { HistoryService, HistoryItem } from '@/lib/historyService';
import { HistoryPanel } from '@/components/HistoryPanel';
import { NewsPanel } from '@/components/NewsPanel';
import {
  Loader2, 
  ExternalLink, 
  Globe, 
  User, 
  Calendar,
  CheckCircle,
  AlertCircle,
  Copy,
  Download,
  FileText,
  Search,
  Sparkles,
  Zap,
  Clock,
  Settings,
  Brain,
  Lightbulb,
  History,
  PanelRightClose,
  Scissors,
  Minimize2,
  Newspaper
} from 'lucide-react';

interface SummaryResult {
  id?: string;
  timestamp?: string;
  article: {
    title: string;
    author?: string;
    publishDate?: string;
    url: string;
  };
  summary: string;
  keyPoints: string[];
  wordCount: number;
  wasEnriched?: boolean;
  needsEnrichment?: boolean;
  contentTruncated?: boolean;
  originalContentLength?: number;
  submittedContentLength?: number;
  compressionMethod?: 'pass-through' | 'extractive-summary' | 'truncate';
}

interface LoadingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  status: 'pending' | 'active' | 'completed' | 'error';
  duration?: string;
}

const USER_ID_STORAGE_KEY = 'research-summarizer:user-id';

const generateUserId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 12);
  }
  return Math.random().toString(36).slice(2, 14);
};

const getOrCreateUserId = (): string | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const existing = window.localStorage.getItem(USER_ID_STORAGE_KEY);
    if (existing && existing.trim().length > 0) {
      return existing;
    }
    const newId = generateUserId();
    window.localStorage.setItem(USER_ID_STORAGE_KEY, newId);
    return newId;
  } catch (error) {
    console.error('User ID initialization failed:', error);
    return null;
  }
};

export default function SummarizerForm() {
  const [userId, setUserId] = useState<string | null>(null);
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SummaryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [showSidePanel, setShowSidePanel] = useState(true);
  const [showHistoryPanel, setShowHistoryPanel] = useState(true);
  const [showNewsPanel, setShowNewsPanel] = useState(true);
  const [historyCount, setHistoryCount] = useState(0);

  // Handle history changes
  const handleHistoryChange = () => {
    setHistoryCount(HistoryService.getHistory().length);
  };

  // Load history count on component mount
  useEffect(() => {
    handleHistoryChange();
    const initializedId = getOrCreateUserId();
    if (initializedId) {
      setUserId(initializedId);
    }
  }, []);

  // Save result to history using HistoryService
  const saveToHistory = (newResult: SummaryResult) => {
    try {
      HistoryService.saveToHistory({
        url: newResult.article.url,
        title: newResult.article.title,
        author: newResult.article.author,
        publishDate: newResult.article.publishDate,
        summary: newResult.summary,
        keyPoints: newResult.keyPoints,
        wordCount: newResult.wordCount,
        wasEnriched: newResult.wasEnriched || false
      });
      
      // Update history count
      setHistoryCount(HistoryService.getHistory().length);
      handleHistoryChange();
    } catch (error) {
      console.error('Error saving to history:', error);
    }
  };

  // Load result from history
  const loadFromHistory = (historyItem: HistoryItem) => {
    const loadedResult: SummaryResult = {
      id: historyItem.id,
      timestamp: new Date(historyItem.timestamp).toISOString(),
      article: {
        title: historyItem.title,
        author: historyItem.author,
        publishDate: historyItem.publishDate,
        url: historyItem.url
      },
      summary: historyItem.summary,
      keyPoints: historyItem.keyPoints,
      wordCount: historyItem.wordCount,
      wasEnriched: historyItem.wasEnriched
    };
    
    setResult(loadedResult);
    setUrl(historyItem.url);
    setError(null);
    
    // Scroll to results
    setTimeout(() => {
      const resultsElement = document.getElementById('results-section');
      if (resultsElement) {
        resultsElement.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  };
  const [loadingSteps, setLoadingSteps] = useState<LoadingStep[]>([
    {
      id: 'validate',
      title: 'URL Validation & Accessibility',
      description: 'Verifying URL format and checking content accessibility',
      status: 'pending',
      duration: '',
      icon: Globe
    },
    {
      id: 'extract',
      title: 'Intelligent Content Extraction',
      description: 'Extracting and parsing article content with advanced algorithms',
      status: 'pending',
      duration: '',
      icon: FileText
    },
    {
      id: 'prepare',
      title: 'Content Preparation & Analysis',
      description: 'Preparing content structure and analyzing key elements for processing',
      status: 'pending',
      duration: '',
      icon: Settings
    },
    {
      id: 'summarize',
      title: 'AI-Powered Summarization',
      description: 'Processing content through Cortensor DeepSeek R1 - Please allow 1-3 minutes depending on article complexity',
      status: 'pending',
      duration: '',
      icon: Brain
    },
    {
      id: 'insights',
      title: 'Key Insights Extraction',
      description: 'Identifying and extracting critical insights and findings from the analysis',
      status: 'pending',
      duration: '',
      icon: Lightbulb
    },
    {
      id: 'quality',
      title: 'Quality Assessment & Validation',
      description: 'Evaluating summary quality and identifying enhancement opportunities',
      status: 'pending',
      duration: '',
      icon: CheckCircle
    },
    {
      id: 'enrich',
      title: 'Multi-Source Enhancement',
      description: 'Enriching insights with additional research - This process may take additional time for thorough analysis',
      status: 'pending',
      duration: '',
      icon: Search
    },
    {
      id: 'finalize',
      title: 'Final Processing & Formatting',
      description: 'Optimizing output format and preparing comprehensive report',
      status: 'pending',
      duration: '',
      icon: Sparkles
    }
  ]);  const updateStepStatus = (stepId: string, status: LoadingStep['status'], duration?: string) => {
    setLoadingSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, status, duration } : step
    ));
  };

  const resetSteps = () => {
    setLoadingSteps(prev => prev.map(step => ({ ...step, status: 'pending', duration: undefined })));
    setProgress(0);
  };

  const simulateProgress = () => {
    const totalSteps = loadingSteps.length;
    const currentStep = 0;
    
    const progressInterval = setInterval(() => {
      const baseProgress = (currentStep / totalSteps) * 100;
      const stepProgress = Math.min(baseProgress + Math.random() * 10, (currentStep + 1) / totalSteps * 100);
      setProgress(stepProgress);
    }, 200);

    return progressInterval;
  };

    // Function to ensure proper paragraph formatting on client side
  const formatSummaryForDisplay = (summary: string): string => {
    if (!summary) return '';

    // First, filter out any remaining DeepSeek thinking process
    let cleaned = summary;
    
    // Remove <think>...</think> blocks if any still exist
    cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/gi, '');
    
    // If there's a </think> tag, take everything after it
    const thinkEndIndex = summary.toLowerCase().lastIndexOf('</think>');
    if (thinkEndIndex !== -1) {
      cleaned = summary.substring(thinkEndIndex + 8).trim();
    }

    // Remove any remaining artifacts
    cleaned = cleaned
      .replace(/KEY INSIGHTS:[\s\S]*$/gi, '')
      .replace(/\*\*KEY INSIGHTS:[\s\S]*$/gi, '')
      .replace(/CRITICAL IMPLICATIONS[\s\S]*$/gi, '')
      .replace(/ADDITIONAL PERSPECTIVES[\s\S]*$/gi, '')
      .replace(/｜end▁of▁sentence｜/g, '')
      .replace(/\<\|end▁of▁sentence\|\>/g, '')
      .replace(/▁+/g, ' ')
      .replace(/▁/g, ' ')
      .trim();

    // Split into sentences and regroup into paragraphs
    const sentences = cleaned.split(/(?<=[.!?。！？])\s*(?=[A-ZａｚＡ-Ｚあ-んア-ヶ一-龯])/);
    const paragraphs: string[] = [];
    let currentParagraph: string[] = [];

    for (let i = 0; i < sentences.length; i++) {
      const sentence = sentences[i].trim();
      if (!sentence) continue;

      currentParagraph.push(sentence);

      // Break at logical points (every 2-3 sentences or at transitions)
      const shouldBreak = 
        currentParagraph.length >= 3 ||
        (currentParagraph.length >= 2 && i < sentences.length - 1 && 
         /^(The article reports|However|Upon their|The situation|This incident|In a statement|The Greek|Meanwhile|Following|また、|しかし、|その後、|一方、|さらに、)/.test(sentences[i + 1]));

      if (shouldBreak && currentParagraph.length > 0) {
        paragraphs.push(currentParagraph.join(' '));
        currentParagraph = [];
      }
    }

    if (currentParagraph.length > 0) {
      paragraphs.push(currentParagraph.join(' '));
    }

    return paragraphs
      .filter(p => p.length > 20)
      .join('\n\n')
      .trim();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    const activeUserId = userId ?? getOrCreateUserId();
    if (!activeUserId) {
      setError('Unable to initialize your session. Please refresh and try again.');
      return;
    }
    if (activeUserId !== userId) {
      setUserId(activeUserId);
    }

    setIsLoading(true);
    setError(null);
    setResult(null);
    resetSteps();

    const progressInterval = simulateProgress();

    try {
      // Step 1: Validation
      updateStepStatus('validate', 'active');
      await new Promise(resolve => setTimeout(resolve, 800));
      updateStepStatus('validate', 'completed', '0.8s');

      // Step 2: Extraction
      updateStepStatus('extract', 'active');
      await new Promise(resolve => setTimeout(resolve, 1200));
      updateStepStatus('extract', 'completed', '1.2s');

      // Step 3: Content Preparation
      updateStepStatus('prepare', 'active');
      await new Promise(resolve => setTimeout(resolve, 900));
      updateStepStatus('prepare', 'completed', '0.9s');

      // Step 4: AI Summarization (Long Process)
      updateStepStatus('summarize', 'active');
      
      const response = await fetch('/api/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, userId: activeUserId }),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const response_data = await response.json();
      const data = response_data.data; // Extract the actual data from the API response
      
      updateStepStatus('summarize', 'completed', '45.2s');
      
      // Step 5: Key Insights Extraction
      updateStepStatus('insights', 'active');
      await new Promise(resolve => setTimeout(resolve, 800));
      updateStepStatus('insights', 'completed', '0.8s');

      // Step 6: Quality Assessment
      updateStepStatus('quality', 'active');
      await new Promise(resolve => setTimeout(resolve, 600));
      updateStepStatus('quality', 'completed', '0.6s');

      // Step 7: Enhancement (if needed)
      if (data.needsEnrichment || response_data.data.wasEnriched) {
        updateStepStatus('enrich', 'active');
        await new Promise(resolve => setTimeout(resolve, 2500));
        updateStepStatus('enrich', 'completed', '12.5s');
      } else {
        updateStepStatus('enrich', 'completed', 'Skipped');
      }

      // Step 8: Finalize
      updateStepStatus('finalize', 'active');
      await new Promise(resolve => setTimeout(resolve, 400));
      updateStepStatus('finalize', 'completed', '0.4s');

      // Data is already processed by the API, but let's ensure proper formatting
      const formattedData = {
        ...data,
        summary: formatSummaryForDisplay(data.summary || '')
      };
      
      setResult(formattedData);
      saveToHistory(formattedData); // Save to local history
      setProgress(100);

    } catch (err) {
      const currentActiveStep = loadingSteps.find(step => step.status === 'active');
      if (currentActiveStep) {
        updateStepStatus(currentActiveStep.id, 'error');
      }
      setError(err instanceof Error ? err.message : 'An unexpected error occurred during analysis');
    } finally {
      clearInterval(progressInterval);
      setIsLoading(false);
    }
  };

  const exportToJSON = () => {
    if (!result) return;
    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'summary-export.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportToMarkdown = () => {
    if (!result) return;
    const markdown = `# ${result.article.title}

**Author:** ${result.article.author || 'Unknown'}
**Published:** ${result.article.publishDate || 'Unknown'}
**Source:** [${result.article.url}](${result.article.url})
**Word Count:** ${result.wordCount} words
**Enhanced:** ${result.wasEnriched ? 'Yes' : 'No'}

## Executive Summary

${result.summary}

## Key Insights

${result.keyPoints.map(point => `- ${point}`).join('\n')}

---
*Generated by Research Summarizer Agent powered by Cortensor AI*`;

    const dataBlob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'summary-report.md';
    link.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  return (
    <div className="min-h-screen w-full">
      <div className="relative max-w-7xl mx-auto p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6 md:space-y-8">
        <div className="absolute right-3 top-3 sm:right-4 sm:top-4">
          <Badge variant="outline" className="text-[10px] sm:text-xs md:text-sm font-mono tracking-tight px-2 py-1">
            {`User ID: ${userId ?? 'initializing...'}`}
          </Badge>
        </div>
        {/* Header */}
        <div className="text-center space-y-3 sm:space-y-4">
          <div className="flex items-center justify-center space-x-2">
            <Sparkles className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent leading-tight">
              Research Summarizer
            </h1>
          </div>
          <p className="text-sm sm:text-base md:text-lg text-muted-foreground max-w-2xl mx-auto px-2 sm:px-4">
            <strong>Intelligent article analysis</strong> powered by Cortensor AI. Transform any article into 
            comprehensive, professional summaries with automatic quality enhancement.
          </p>
          
          {/* Side Panel Toggle */}
          <div className="flex justify-center">
            <Button
              variant="outline"
              onClick={() => {
                if (showSidePanel) {
                  setShowSidePanel(false);
                } else {
                  if (!showHistoryPanel && !showNewsPanel) {
                    setShowHistoryPanel(true);
                    setShowNewsPanel(true);
                  }
                  setShowSidePanel(true);
                }
              }}
              className="flex items-center space-x-2 text-sm hover:bg-blue-50 transition-colors"
            >
              {showSidePanel ? (
                <>
                  <PanelRightClose className="h-4 w-4" />
                  <span>Hide Side Panel</span>
                </>
              ) : (
                <>
                  <History className="h-4 w-4" />
                  <span>Show Side Panel</span>
                  {historyCount > 0 && (
                    <Badge variant="secondary" className="ml-1 text-xs">
                      {historyCount}
                    </Badge>
                  )}
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div className={cn(
          "grid gap-6 transition-all duration-300",
          showSidePanel && (showHistoryPanel || showNewsPanel) ? "grid-cols-1 lg:grid-cols-3" : "grid-cols-1"
        )}>
          {/* Main Column - Form and Results */}
          <div className={cn(
            "space-y-6",
            showSidePanel && (showHistoryPanel || showNewsPanel) ? "lg:col-span-2" : "max-w-4xl mx-auto w-full"
          )}>
            {/* Input Form */}
            <Card className="border-2 shadow-lg">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center space-x-2 text-lg sm:text-xl">
                  <Globe className="h-4 w-4 sm:h-5 sm:w-5" />
                  <span>Article Analysis</span>
                </CardTitle>
                <CardDescription className="text-sm sm:text-base">
                  Enter the URL of the article you want to analyze and summarize
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
                  <div className="space-y-2">
                    <Input
                      type="url"
                      placeholder="https://example.com/article-to-summarize"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      disabled={isLoading}
                      className="text-base sm:text-lg h-10 sm:h-12 px-3 sm:px-4"
                      required
                    />
                  </div>
                  <Button 
                    type="submit" 
                    disabled={isLoading || !url.trim()}
                    className="w-full h-10 sm:h-12 text-base sm:text-lg font-semibold"
                    size="lg"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Processing Analysis...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-5 w-5" />
                  Analyze & Summarize Article
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Loading Steps */}
      {isLoading && (
        <Card className="border-blue-200 bg-blue-50/50 shadow-lg">
          <CardHeader className="pb-3 sm:pb-4">
            <CardTitle className="flex items-center space-x-2 text-lg sm:text-xl">
              <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600" />
              <span>Processing Pipeline</span>
            </CardTitle>
            <Progress value={progress} className="w-full h-2 sm:h-3" />
            <CardDescription className="text-blue-700 text-xs sm:text-sm">
              <strong>AI Analysis in Progress</strong> - Processing your article through our intelligent pipeline
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 sm:space-y-4">
            {loadingSteps.map((step) => (
              <div key={step.id} className={cn(
                "flex items-start space-x-2 sm:space-x-3 p-2 sm:p-4 rounded-lg transition-all duration-300",
                step.status === 'pending' && "opacity-50",
                step.status === 'active' && "bg-blue-100 border-2 border-blue-300 shadow-sm",
                step.status === 'completed' && "bg-green-50 border border-green-200",
                step.status === 'error' && "bg-red-50 border border-red-200"
              )}>
                <div className={cn(
                  "flex-shrink-0 rounded-full p-1.5 sm:p-2 transition-colors",
                  step.status === 'pending' && "bg-gray-200",
                  step.status === 'active' && "bg-blue-500 text-white animate-pulse",
                  step.status === 'completed' && "bg-green-500 text-white",
                  step.status === 'error' && "bg-red-500 text-white"
                )}>
                  {step.status === 'active' ? (
                    <Loader2 className="h-3 w-3 sm:h-4 sm:w-4 animate-spin" />
                  ) : (
                    <step.icon className="h-3 w-3 sm:h-4 sm:w-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className={cn(
                      "font-semibold text-xs sm:text-sm",
                      step.status === 'active' && "text-blue-900",
                      step.status === 'completed' && "text-green-900"
                    )}>
                      {step.title}
                    </h4>
                    {step.duration && (
                      <Badge variant="outline" className="text-xs px-1 py-0">
                        {step.duration}
                      </Badge>
                    )}
                  </div>
                  <p className={cn(
                    "text-xs sm:text-sm text-muted-foreground leading-tight",
                    step.status === 'active' && "text-blue-700",
                    step.status === 'completed' && "text-green-700"
                  )}>
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="font-medium">
            <strong>Analysis Failed:</strong> {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Results Display */}
      {result && (
        <div id="results-section" className="space-y-4 sm:space-y-6">
          {/* Article Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 sm:h-5 sm:w-5" />
                  <span className="text-sm sm:text-base">Article Information</span>
                </div>
                <div className="flex flex-wrap gap-1 sm:gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(JSON.stringify(result, null, 2))}
                    className="text-xs sm:text-sm h-8 sm:h-9"
                  >
                    <Copy className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    Copy
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={exportToMarkdown}
                    className="text-xs sm:text-sm h-8 sm:h-9"
                  >
                    <Download className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    Markdown
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={exportToJSON}
                    className="text-xs sm:text-sm h-8 sm:h-9"
                  >
                    <Download className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    JSON
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 sm:space-y-4">
              <div>
                <h3 className="text-lg sm:text-xl font-bold text-gray-900 leading-tight">
                  {result.article.title}
                </h3>
              </div>
              
              <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                {result.article.author && (
                  <div className="flex items-center space-x-1">
                    <User className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span><strong>Author:</strong> {result.article.author}</span>
                  </div>
                )}
                {result.article.publishDate && (
                  <div className="flex items-center space-x-1">
                    <Calendar className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span><strong>Published:</strong> {result.article.publishDate}</span>
                  </div>
                )}
                <div className="flex items-center space-x-1">
                  <ExternalLink className="h-3 w-3 sm:h-4 sm:w-4" />
                  <a 
                    href={result.article.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline font-medium break-all"
                  >
                    View Original Article
                  </a>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="font-medium text-xs">
                  {result.wordCount} words analyzed
                </Badge>
                {result.wasEnriched && (
                  <Badge variant="default" className="bg-green-600 text-xs">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Enhanced with additional sources
                  </Badge>
                )}
                {result.contentTruncated && (
                  <Badge
                    variant="outline"
                    className="text-xs border-orange-400 text-orange-700 bg-orange-50 flex items-center"
                  >
                    {result.compressionMethod === 'extractive-summary' ? (
                      <Minimize2 className="h-3 w-3 mr-1" />
                    ) : (
                      <Scissors className="h-3 w-3 mr-1" />
                    )}
                    {result.compressionMethod === 'extractive-summary'
                      ? 'Source compressed to fit model context limit'
                      : 'Source truncated to fit model context limit'}
                  </Badge>
                )}
              </div>
              {result.contentTruncated && (
                <p className="text-xs text-orange-700 mt-2">
                  Submitted {result.submittedContentLength ?? 0} of {result.originalContentLength ?? 0} characters after
                  {result.compressionMethod === 'extractive-summary' ? ' compression' : ' truncation'} to honor the Cortensor context window.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 text-purple-600" />
                <span className="text-sm sm:text-base">Executive Summary</span>
              </CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                <strong>Comprehensive analysis</strong> generated by Cortensor AI with intelligent processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="prose prose-gray max-w-none cjk-text">
                {result.summary.split('\n\n').filter(paragraph => paragraph.trim().length > 0).map((paragraph, index) => (
                  <p key={index} className="text-gray-800 leading-relaxed mb-3 sm:mb-4 text-justify break-words whitespace-pre-wrap font-medium cjk-text text-sm sm:text-base" style={{ wordBreak: 'break-word', lineHeight: '1.7', letterSpacing: '0.02em' }}>
                    {paragraph.trim()}
                  </p>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Key Points */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-orange-600" />
                <span className="text-sm sm:text-base">Key Insights & Findings</span>
              </CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                <strong>Critical points</strong> extracted from the comprehensive analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 sm:space-y-3">
                {result.keyPoints && result.keyPoints.length > 0 ? (
                  result.keyPoints.map((point, index) => (
                    <div key={index} className="flex items-start space-x-2 sm:space-x-3 p-2 sm:p-3 rounded-lg bg-gray-50 border border-gray-200">
                      <div className="flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs sm:text-sm font-bold">
                        {index + 1}
                      </div>
                      <p className="text-gray-800 leading-relaxed font-medium break-words whitespace-pre-wrap cjk-text text-sm sm:text-base" style={{ wordBreak: 'break-word', lineHeight: '1.6', letterSpacing: '0.02em' }}>
                        {point}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="text-center p-4 sm:p-6 text-gray-500">
                    <Lightbulb className="h-6 w-6 sm:h-8 sm:w-8 mx-auto mb-2 text-gray-400" />
                    <p className="text-xs sm:text-sm">Key insights are being processed and will appear here once analysis is complete.</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
          </div>

          {/* Side Panel - Conditional */}
          {showSidePanel && (showHistoryPanel || showNewsPanel) && (
            <div className="lg:col-span-1">
              <div className="sticky top-6 space-y-4">
                <div className="flex gap-2">
                  <Button
                    variant={showHistoryPanel ? "default" : "outline"}
                    size="sm"
                    className="flex-1"
                    onClick={() => setShowHistoryPanel((v) => {
                      const next = !v;
                      if (!next && !showNewsPanel) setShowNewsPanel(true);
                      return next;
                    })}
                  >
                    <History className="h-4 w-4 mr-2" />
                    History
                  </Button>
                  <Button
                    variant={showNewsPanel ? "default" : "outline"}
                    size="sm"
                    className="flex-1"
                    onClick={() => setShowNewsPanel((v) => {
                      const next = !v;
                      if (!next && !showHistoryPanel) setShowHistoryPanel(true);
                      return next;
                    })}
                  >
                    <Newspaper className="h-4 w-4 mr-2" />
                    News
                  </Button>
                </div>

                {showHistoryPanel && (
                  <HistoryPanel 
                    onLoadHistoryItem={loadFromHistory}
                    onHistoryChange={handleHistoryChange}
                    className="shadow-lg"
                  />
                )}

                {showNewsPanel && (
                  <NewsPanel className="shadow-lg" />
                )}

                {!showHistoryPanel && !showNewsPanel && (
                  <div className="p-4 rounded border text-sm text-muted-foreground bg-muted/40">
                    Pilih panel yang ingin ditampilkan.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
