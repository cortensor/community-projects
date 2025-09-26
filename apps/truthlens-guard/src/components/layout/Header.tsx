import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Menu, 
  X, 
  Shield, 
  User, 
  Settings, 
  LogOut,
  Sun,
  Moon,
  Upload
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { motion, AnimatePresence } from 'framer-motion';

interface HeaderProps {
  onMenuToggle?: () => void;
  showMobileMenu?: boolean;
}

export function Header({ onMenuToggle, showMobileMenu }: HeaderProps) {
  const navigate = useNavigate();
  const { user, isDarkMode, toggleDarkMode } = useAppStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleMobileMenuToggle = () => {
    setMobileMenuOpen(!mobileMenuOpen);
    onMenuToggle?.();
  };

  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b border-border/40 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-4">
            {showMobileMenu && (
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden"
                onClick={handleMobileMenuToggle}
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
            )}
            
            <Link to="/" className="flex items-center gap-2 transition-opacity hover:opacity-80">
              <div className="relative">
                <Shield className="h-8 w-8 text-primary" />
                <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-accent animate-pulse" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-xl font-bold gradient-text">TruthLens</h1>
                <p className="text-xs text-muted-foreground">AI Detection</p>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <Link 
              to="/dashboard" 
              className="text-sm font-medium text-foreground/80 hover:text-foreground transition-colors"
            >
              Dashboard
            </Link>
            <Link 
              to="/history" 
              className="text-sm font-medium text-foreground/80 hover:text-foreground transition-colors"
            >
              History
            </Link>
            <Link 
              to="/settings" 
              className="text-sm font-medium text-foreground/80 hover:text-foreground transition-colors"
            >
              Settings
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleDarkMode}
              className="h-9 w-9"
            >
              {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>

            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user.avatar} alt={user.name} />
                      <AvatarFallback>{user.name?.charAt(0) || 'U'}</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <div className="flex items-center justify-start gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      {user.name && <p className="font-medium">{user.name}</p>}
                      {user.email && (
                        <p className="w-[200px] truncate text-sm text-muted-foreground">
                          {user.email}
                        </p>
                      )}
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/dashboard')}>
                    <User className="mr-2 h-4 w-4" />
                    Dashboard
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate('/settings')}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <LogOut className="mr-2 h-4 w-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => navigate('/auth')}>
                  Sign In
                </Button>
                <Button size="sm" className="hidden sm:inline-flex">
                  <Upload className="mr-2 h-4 w-4" />
                  Get Started
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-b border-border/40 backdrop-blur supports-[backdrop-filter]:bg-background/60"
          >
            <nav className="container py-4 space-y-2">
              <Link 
                to="/dashboard" 
                className="block px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Dashboard
              </Link>
              <Link 
                to="/history" 
                className="block px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                History
              </Link>
              <Link 
                to="/settings" 
                className="block px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Settings
              </Link>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}