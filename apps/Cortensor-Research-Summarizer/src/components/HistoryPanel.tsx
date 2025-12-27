'use client'

import React, { useState, useEffect } from 'react';
import { HistoryService, HistoryItem } from '@/lib/historyService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  History, 
  Search, 
  Trash2, 
  ExternalLink, 
  User, 
  FileText,
  RotateCcw,
  AlertCircle,
  Clock
} from 'lucide-react';

interface HistoryPanelProps {
  onLoadHistoryItem: (item: HistoryItem) => void;
  onHistoryChange?: () => void; // Callback when history changes
  className?: string;
}

export function HistoryPanel({ onLoadHistoryItem, onHistoryChange, className }: HistoryPanelProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredHistory, setFilteredHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (searchQuery.trim()) {
      setFilteredHistory(HistoryService.searchHistory(searchQuery.trim()));
    } else {
      setFilteredHistory(history);
    }
  }, [searchQuery, history]);

  const loadHistory = () => {
    setIsLoading(true);
    try {
      const items = HistoryService.getHistory();
      setHistory(items);
      setFilteredHistory(items);
    } catch (error) {
      console.error('Error loading history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteItem = (id: string, event: React.MouseEvent) => {
    event.stopPropagation();
    HistoryService.deleteHistoryItem(id);
    loadHistory();
    onHistoryChange?.(); // Notify parent of change
  };

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear all history? This action cannot be undone.')) {
      HistoryService.clearHistory();
      loadHistory();
      onHistoryChange?.(); // Notify parent of change
    }
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (diffDays === 1) {
      return `Yesterday at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const formatUrl = (url: string) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname;
    } catch {
      return url;
    }
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <History className="h-5 w-5" />
            <span>Recent Summaries</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center items-center h-32">
          <div className="text-center text-muted-foreground">
            <RotateCcw className="h-6 w-6 mx-auto mb-2 animate-spin" />
            <p>Loading history...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <History className="h-5 w-5" />
              <span>Recent Summaries</span>
              <Badge variant="secondary" className="ml-2">
                {filteredHistory.length}
              </Badge>
            </CardTitle>
            <CardDescription>
              Your article summarization history
            </CardDescription>
          </div>
          {history.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearHistory}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Clear All
            </Button>
          )}
        </div>
        
        {history.length > 0 && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search summaries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        )}
      </CardHeader>

      <CardContent>
        {filteredHistory.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {history.length === 0 ? (
              <>
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-medium mb-2">No summaries yet</h3>
                <p className="text-sm">Start by summarizing your first article above</p>
              </>
            ) : (
              <>
                <AlertCircle className="h-8 w-8 mx-auto mb-3 opacity-50" />
                <p>
                  No summaries found matching &ldquo;
                  {searchQuery}
                  &rdquo;
                </p>
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setSearchQuery('')}
                  className="mt-2"
                >
                  Clear search
                </Button>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {filteredHistory.map((item, index) => (
              <div key={item.id}>
                <div
                  onClick={() => onLoadHistoryItem(item)}
                  className="group cursor-pointer p-4 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="font-medium text-sm leading-tight line-clamp-1 group-hover:text-primary">
                          {item.title}
                        </h4>
                        {item.wasEnriched && (
                          <Badge variant="default" className="text-xs px-1.5 py-0.5">
                            Enhanced
                          </Badge>
                        )}
                      </div>
                      
                      <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                        {item.previewText}
                      </p>
                      
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <ExternalLink className="h-3 w-3" />
                          <span className="truncate max-w-32">{formatUrl(item.url)}</span>
                        </div>
                        {item.author && (
                          <div className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            <span className="truncate max-w-24">{item.author}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          <span>{formatDate(item.timestamp)}</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">
                          {item.wordCount} words
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {item.keyPoints.length} insights
                        </Badge>
                      </div>
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => handleDeleteItem(item.id, e)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity ml-2 h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {index < filteredHistory.length - 1 && <Separator className="my-2" />}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}