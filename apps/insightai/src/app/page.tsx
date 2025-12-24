"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface ResearchResult {
  query: string;
  summary: string;
  bulletPoints: string[];
  sources: string[];
  sessionId?: string;
  taskId?: string;
  timestamp: Date;
  verified: boolean;
  isDemo?: boolean;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleResearch = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, url: url || undefined }),
      });

      if (!response.ok) {
        throw new Error("Research request failed");
      }

      const data = await response.json();
      setResult({
        query,
        summary: data.summary,
        bulletPoints: data.bulletPoints,
        sources: data.sources,
        sessionId: data.sessionId,
        taskId: data.taskId,
        timestamp: new Date(),
        verified: data.verified,
        isDemo: data.isDemo,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-4 md:p-8 lg:p-12">
      {/* Header */}
      <header className="text-center mb-12 animate-[fade-in_0.5s_ease-out]">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center glow">
            <span className="text-2xl">🔍</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold gradient-text">
            InsightAI
          </h1>
        </div>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
          AI Research Agent powered by{" "}
          <a
            href="https://cortensor.network"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            Cortensor
          </a>
          's decentralized inference network
        </p>
        <div className="flex items-center justify-center gap-2 mt-4">
          <Badge variant="secondary">Decentralized AI</Badge>
          <Badge variant="secondary">Verifiable</Badge>
          <Badge variant="secondary">Trusted</Badge>
        </div>
      </header>

      {/* Research Input */}
      <div className="max-w-3xl mx-auto mb-8 animate-[slide-up_0.5s_ease-out]">
        <Card className="glass border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>📝</span> Research Query
            </CardTitle>
            <CardDescription>
              Ask any research question or provide a URL to analyze
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="e.g., What are the latest developments in decentralized AI inference? Summarize key trends and innovations..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              className="bg-background/50 border-border/50 focus:border-primary resize-none"
            />
            <Input
              placeholder="Optional: Add a URL to research (e.g., https://docs.cortensor.network)"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="bg-background/50 border-border/50 focus:border-primary"
            />
            <Button
              onClick={handleResearch}
              disabled={isLoading || !query.trim()}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold py-6 text-lg"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⚡</span> Researching...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <span>🚀</span> Start Research
                </span>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Error Display */}
      {error && (
        <div className="max-w-3xl mx-auto mb-8 animate-[fade-in_0.3s_ease-out]">
          <Card className="border-destructive/50 bg-destructive/10">
            <CardContent className="p-4">
              <p className="text-destructive flex items-center gap-2">
                <span>❌</span> {error}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div className="max-w-3xl mx-auto animate-[slide-up_0.5s_ease-out]">
          <Card className="glass border-primary/30 glow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <span>📊</span> Research Results
                </CardTitle>
                {result.isDemo ? (
                  <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                    🎮 Demo Mode
                  </Badge>
                ) : result.verified && (
                  <Badge className="bg-primary/20 text-primary border-primary/30">
                    ✓ Verified via Cortensor
                  </Badge>
                )}
              </div>
              <CardDescription>
                Query: "{result.query}"
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Summary */}
              {result.summary && (
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                    <span>💡</span> Summary
                  </h3>
                  <p className="text-foreground leading-relaxed">
                    {result.summary}
                  </p>
                </div>
              )}

              {/* Key Points */}
              {result.bulletPoints.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                    <span>📌</span> Key Findings
                  </h3>
                  <ul className="space-y-2">
                    {result.bulletPoints.map((point, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-3 p-3 rounded-lg bg-secondary/30"
                      >
                        <span className="text-primary font-bold">{index + 1}.</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Sources */}
              {result.sources.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                    <span>🔗</span> Sources
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {result.sources.map((source, index) => (
                      <a
                        key={index}
                        href={source}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-accent hover:underline"
                      >
                        {source}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Verification */}
              {result.sessionId && (
                <div className="pt-4 border-t border-border/50">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>Session: {result.sessionId}</span>
                    <a
                      href={`https://dashboard-testnet0.cortensor.network/session/${result.sessionId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-1"
                    >
                      View on Cortensor Dashboard →
                    </a>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Powered by */}
          <div className="text-center mt-8 text-sm text-muted-foreground">
            <p>
              Powered by{" "}
              <a
                href="https://cortensor.network"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Cortensor
              </a>
              {" "}decentralized inference • Built for Hackathon #3
            </p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !isLoading && (
        <div className="max-w-3xl mx-auto text-center py-12 animate-[fade-in_0.5s_ease-out]">
          <div className="text-6xl mb-4">🧠</div>
          <h2 className="text-xl font-semibold mb-2">Ready to Research</h2>
          <p className="text-muted-foreground">
            Enter your research question above and let InsightAI analyze it using
            decentralized AI inference for trusted, verifiable insights.
          </p>
        </div>
      )}
    </main>
  );
}
