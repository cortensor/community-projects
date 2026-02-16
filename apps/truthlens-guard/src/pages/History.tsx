import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Search, 
  Filter, 
  Download, 
  Eye, 
  Shield,
  Calendar,
  MoreVertical,
  Trash2,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAppStore } from '@/store/useAppStore';
import { format } from 'date-fns';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export default function History() {
  const { factChecks, removeFactCheck } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  const filteredChecks = factChecks
    .filter((check) => {
      const matchesSearch = check.claim.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = filterStatus === 'all' || check.status === filterStatus;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === 'newest') return new Date(b.checkedAt).getTime() - new Date(a.checkedAt).getTime();
      if (sortBy === 'oldest') return new Date(a.checkedAt).getTime() - new Date(b.checkedAt).getTime();
      if (sortBy === 'name') return a.claim.localeCompare(b.claim);
      if (sortBy === 'score') return (b.credibilityScore || 0) - (a.credibilityScore || 0);
      return 0;
    });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'status-secure';
      case 'analyzing': return 'status-warning';
      case 'error': return 'status-danger';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-accent bg-accent/10 border-accent/30';
    if (score >= 0.4) return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
    return 'text-destructive bg-destructive/10 border-destructive/30';
  };

  const handleDeleteCheck = (checkId: string) => {
    removeFactCheck(checkId);
  };

  return (
    <div className="min-h-screen p-6 space-y-6 cyber-grid">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-2"
      >
        <h1 className="text-3xl font-bold gradient-text">Fact-Check History</h1>
        <p className="text-muted-foreground">
          View and manage all your verified claims and analysis results.
        </p>
      </motion.div>

      {/* Filters and Search */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between"
      >
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <div className="relative min-w-[300px]">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search claims..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-muted/30 border-border/50"
            />
          </div>
          
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[140px] bg-muted/30 border-border/50">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="analyzing">Analyzing</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[140px] bg-muted/30 border-border/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Newest First</SelectItem>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="name">Name A-Z</SelectItem>
              <SelectItem value="score">Score High-Low</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Badge variant="outline" className="text-xs border-primary/30">
            {filteredChecks.length} checks
          </Badge>
        </div>
      </motion.div>

      {/* Checks Grid/List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {filteredChecks.length > 0 ? (
          <div className="grid grid-cols-1 gap-4">
            {filteredChecks.map((check, index) => (
              <motion.div
                key={check.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Card className="card-cyber">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 flex-1">
                        {/* Check Icon & Info */}
                        <div className="p-3 rounded-lg bg-primary/10">
                          <Shield className="h-6 w-6 text-primary" />
                        </div>

                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold truncate mb-1">{check.claim}</h3>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {format(new Date(check.checkedAt), 'MMM d, yyyy')}
                            </div>
                            <span className="capitalize">{check.type}</span>
                            {check.source && (
                              <span className="truncate max-w-[200px]">{check.source}</span>
                            )}
                          </div>
                        </div>

                        {/* Status Badge */}
                        <Badge className={`${getStatusColor(check.status)} capitalize font-medium`}>
                          {check.status}
                        </Badge>

                        {/* Credibility Score */}
                        {check.credibilityScore !== undefined && (
                          <div className={`px-3 py-1 rounded-md border text-sm font-semibold ${getScoreColor(check.credibilityScore)}`}>
                            {(check.credibilityScore * 100).toFixed(1)}%
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuItem>
                            <Eye className="mr-2 h-4 w-4" />
                            View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Download className="mr-2 h-4 w-4" />
                            Download Report
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className="text-destructive focus:text-destructive"
                            onClick={() => handleDeleteCheck(check.id)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    {/* Analysis Details */}
                    {check.analysis && check.status === 'completed' && (
                      <div className="mt-4 pt-4 border-t border-border/40">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground mb-1">Verification Result</p>
                            <p className="font-medium">
                              {check.analysis.isCredible ? 'Credible' : 'Suspicious'}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">AI Confidence</p>
                            <p className="font-medium">
                              {(check.analysis.confidence * 100).toFixed(1)}%
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">Sources</p>
                            <div className="flex flex-wrap gap-1">
                              {check.analysis.supportingSources.slice(0, 2).map((source, idx) => (
                                <Badge key={idx} variant="outline" className="text-xs">
                                  {new URL(source.url).hostname}
                                </Badge>
                              ))}
                              {check.analysis.supportingSources.length > 2 && (
                                <Badge variant="outline" className="text-xs">
                                  +{check.analysis.supportingSources.length - 2} more
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        {check.analysis.consensus && (
                          <div className="mt-4 p-3 bg-muted/20 rounded-lg">
                            <p className="text-sm text-muted-foreground mb-1">AI Consensus</p>
                            <p className="text-sm">{check.analysis.consensus}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        ) : (
          <Card className="card-cyber">
            <CardContent className="p-12 text-center">
              <div className="space-y-4">
                <div className="w-16 h-16 mx-auto rounded-full bg-muted/30 flex items-center justify-center">
                  <Search className="h-8 w-8 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">No claims found</h3>
                  <p className="text-muted-foreground">
                    {searchQuery || filterStatus !== 'all' 
                      ? 'Try adjusting your search or filters.'
                      : 'Analyze your first claim to get started with fact-checking.'
                    }
                  </p>
                </div>
                {(!searchQuery && filterStatus === 'all') && (
                  <Button className="btn-cyber">
                    Start Fact-Checking
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </motion.div>

      {/* Summary Stats */}
      {factChecks.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          <Card className="card-cyber p-4 text-center">
            <p className="text-2xl font-bold text-primary">
              {factChecks.filter(f => f.status === 'completed').length}
            </p>
            <p className="text-sm text-muted-foreground">Completed</p>
          </Card>
          
          <Card className="card-cyber p-4 text-center">
            <p className="text-2xl font-bold text-yellow-500">
              {factChecks.filter(f => f.status === 'analyzing').length}
            </p>
            <p className="text-sm text-muted-foreground">Processing</p>
          </Card>
          
          <Card className="card-cyber p-4 text-center">
            <p className="text-2xl font-bold text-accent">
              {factChecks.filter(f => f.credibilityScore && f.credibilityScore >= 0.7).length}
            </p>
            <p className="text-sm text-muted-foreground">Credible</p>
          </Card>
          
          <Card className="card-cyber p-4 text-center">
            <p className="text-2xl font-bold text-destructive">
              {factChecks.filter(f => f.credibilityScore && f.credibilityScore < 0.4).length}
            </p>
            <p className="text-sm text-muted-foreground">Suspicious</p>
          </Card>
        </motion.div>
      )}
    </div>
  );
}