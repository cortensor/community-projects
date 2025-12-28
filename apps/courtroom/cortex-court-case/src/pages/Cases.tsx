import { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { 
  FileSearch, 
  Search,
  Filter,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Download
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { mockDisputes, type Dispute } from "@/data/mockData";

const StatusBadge = ({ status }: { status: Dispute["status"] }) => {
  const config = {
    pending: { className: "bg-warning/10 text-warning border-warning/20", icon: Clock, label: "Pending" },
    active: { className: "bg-primary/10 text-primary border-primary/20", icon: AlertTriangle, label: "Active" },
    resolved: { className: "bg-success/10 text-success border-success/20", icon: CheckCircle2, label: "Resolved" },
    slashed: { className: "bg-destructive/10 text-destructive border-destructive/20", icon: AlertTriangle, label: "Slashed" },
  };
  const { className, icon: Icon, label } = config[status];
  return (
    <Badge variant="outline" className={className}>
      <Icon className="w-3 h-3 mr-1" />
      {label}
    </Badge>
  );
};

const Cases = () => {
  const [filter, setFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("newest");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredDisputes = mockDisputes
    .filter(d => {
      const matchesFilter = filter === "all" || d.status === filter;
      const matchesSearch = searchQuery === "" || 
        d.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.model.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.taskId.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    })
    .sort((a, b) => {
      if (sortBy === "newest") return b.createdAt.getTime() - a.createdAt.getTime();
      if (sortBy === "oldest") return a.createdAt.getTime() - b.createdAt.getTime();
      if (sortBy === "similarity-high") return b.similarity - a.similarity;
      if (sortBy === "similarity-low") return a.similarity - b.similarity;
      return 0;
    });

  const statusCounts = {
    all: mockDisputes.length,
    active: mockDisputes.filter(d => d.status === "active").length,
    pending: mockDisputes.filter(d => d.status === "pending").length,
    resolved: mockDisputes.filter(d => d.status === "resolved").length,
    slashed: mockDisputes.filter(d => d.status === "slashed").length,
  };

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
                <FileSearch className="w-8 h-8 text-primary" />
                Cases
              </h1>
              <p className="text-muted-foreground mt-1">Browse and search all dispute cases</p>
            </div>
            <Button variant="outline" className="gap-2">
              <Download className="w-4 h-4" />
              Export Data
            </Button>
          </div>
        </motion.div>

        {/* Status Tabs */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex flex-wrap gap-2 mb-6"
        >
          {Object.entries(statusCounts).map(([key, count]) => (
            <Button
              key={key}
              variant={filter === key ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(key)}
              className="capitalize"
            >
              {key}
              <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                filter === key ? "bg-primary-foreground/20" : "bg-muted"
              }`}>
                {count}
              </span>
            </Button>
          ))}
        </motion.div>

        {/* Filters */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-4 mb-6"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by ID, model, or task..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-full sm:w-48">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Newest First</SelectItem>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="similarity-high">Similarity (High)</SelectItem>
              <SelectItem value="similarity-low">Similarity (Low)</SelectItem>
            </SelectContent>
          </Select>
        </motion.div>

        {/* Cases List */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          {filteredDisputes.map((dispute, index) => (
            <motion.div
              key={dispute.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * index }}
            >
              <Card className="hover:shadow-card transition-shadow">
                <CardContent className="p-5">
                  <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <p className="font-mono font-semibold">{dispute.id}</p>
                        <StatusBadge status={dispute.status} />
                      </div>
                      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                        <span>Task: {dispute.taskId}</span>
                        <span>Model: {dispute.model}</span>
                        <span>{dispute.timestamp}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Similarity</p>
                        <p className={`font-mono font-semibold ${
                          dispute.similarity < 0.8 ? "text-destructive" : 
                          dispute.similarity < 0.95 ? "text-warning" : "text-success"
                        }`}>
                          {(dispute.similarity * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Bond</p>
                        <p className="font-mono font-semibold text-primary">{dispute.bondAmount}</p>
                      </div>
                      <Link to={`/cases/${dispute.id}`}>
                        <Button variant="outline" size="sm">
                          <ArrowRight className="w-4 h-4" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {filteredDisputes.length === 0 && (
          <div className="text-center py-12">
            <FileSearch className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">No cases found matching your criteria</p>
          </div>
        )}

        {/* Pagination placeholder */}
        <div className="flex justify-center mt-8">
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled>Previous</Button>
            <Button variant="outline" size="sm">1</Button>
            <Button variant="default" size="sm">2</Button>
            <Button variant="outline" size="sm">3</Button>
            <Button variant="outline" size="sm">Next</Button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Cases;