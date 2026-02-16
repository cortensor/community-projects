import { Link, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Upload,
  History,
  Settings,
  BarChart3,
  Shield,
  ChevronLeft,
  ChevronRight,
  FileImage,
  FileVideo,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

const navigationItems = [
  {
    title: 'Analyze',
    href: '/dashboard',
    icon: Upload,
    description: 'Fact-check claims'
  },
  {
    title: 'Results',
    href: '/dashboard/analyze',
    icon: BarChart3,
    description: 'View results'
  },
  {
    title: 'History',
    href: '/history',
    icon: History,
    description: 'Past analyses'
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Preferences'
  }
];

export function Sidebar() {
  const location = useLocation();
  const { sidebarCollapsed, setSidebarCollapsed, factChecks } = useAppStore();

  const recentChecks = factChecks.slice(0, 3);
  const pendingAnalyses = factChecks.filter(f => f.status === 'analyzing').length;

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <motion.aside
      initial={false}
      animate={{
        width: sidebarCollapsed ? 80 : 280
      }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="relative flex flex-col border-r border-border/40 bg-card/50 backdrop-blur"
    >
      {/* Toggle Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={toggleSidebar}
        className={cn(
          "absolute -right-4 top-6 z-10 h-8 w-8 rounded-full border border-border bg-background shadow-md hover:shadow-lg transition-shadow",
          sidebarCollapsed && "rotate-180"
        )}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      {/* Header */}
      <div className="p-6 pb-4">
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-6 w-6 text-primary" />
                <h2 className="text-lg font-semibold gradient-text">TruthLens</h2>
              </div>
              <p className="text-sm text-muted-foreground">
                AI-powered fact verification
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {sidebarCollapsed && (
          <div className="flex justify-center">
            <Shield className="h-6 w-6 text-primary" />
          </div>
        )}
      </div>

      <Separator className="mx-6" />

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigationItems.map((item) => {
          const isActive = location.pathname === item.href || 
            (item.href === '/dashboard' && location.pathname.startsWith('/dashboard'));
          
          return (
            <Link key={item.href} to={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3 h-12 transition-all duration-200",
                  sidebarCollapsed && "justify-center px-0",
                  isActive && "bg-primary/10 text-primary hover:bg-primary/15 shadow-sm"
                )}
              >
                <item.icon className={cn("h-5 w-5", isActive && "text-primary")} />
                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      className="flex flex-col items-start"
                    >
                      <span className="font-medium">{item.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {item.description}
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>
                {item.title === 'Analysis' && pendingAnalyses > 0 && (
                  <Badge variant="secondary" className="ml-auto h-5 w-5 p-0 text-xs">
                    {pendingAnalyses}
                  </Badge>
                )}
              </Button>
            </Link>
          );
        })}
      </nav>

      {/* Recent Checks */}
      <AnimatePresence>
        {!sidebarCollapsed && recentChecks.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="p-4 border-t border-border/40"
          >
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">
              Recent Checks
            </h3>
            <div className="space-y-2">
              {recentChecks.map((check) => (
                <div
                  key={check.id}
                  className="flex items-center gap-2 p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{check.claim.substring(0, 40)}...</p>
                    <div className="flex items-center gap-1">
                      {check.status === 'completed' ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : check.status === 'analyzing' ? (
                        <AlertCircle className="h-3 w-3 text-yellow-500 animate-pulse" />
                      ) : null}
                      <span className="text-xs text-muted-foreground">
                        {check.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}