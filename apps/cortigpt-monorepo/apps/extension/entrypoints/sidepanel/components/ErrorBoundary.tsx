import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Extension Error:', error, errorInfo);
    
    // Store error in localStorage for debugging
    const errors = JSON.parse(localStorage.getItem('extension_errors') || '[]');
    errors.push({ 
      error: error.message, 
      stack: error.stack, 
      timestamp: new Date().toISOString() 
    });
    localStorage.setItem('extension_errors', JSON.stringify(errors.slice(-10))); // Keep last 10
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-background neural-bg p-6">
          {/* Error Icon with Glow Effect */}
          <div className="flex justify-center items-center w-20 h-20 rounded-full bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-500/30 shadow-glow-red mb-6">
            <AlertTriangle className="w-10 h-10 text-red-500" />
          </div>

          {/* Error Title */}
          <h1 className="text-2xl font-bold text-foreground mb-2 text-center">
            Oops! Something went wrong
          </h1>

          {/* Error Description */}
          <p className="text-muted-foreground text-center mb-8 max-w-md">
            We encountered an unexpected error. Don't worry, your data is safe and we're working to fix this.
          </p>

          {/* Error Details (Collapsible) */}
          {this.state.error && (
            <details className="w-full max-w-md mb-6">
              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground transition-colors mb-2">
                Show error details
              </summary>
              <div className="p-3 bg-muted/50 rounded-lg border border-border/50">
                <p className="text-xs font-mono text-red-500 break-words">
                  {this.state.error.message}
                </p>
              </div>
            </details>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md">
            <button
              onClick={this.handleReload}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary to-primary/80 text-primary-foreground font-semibold rounded-lg hover:from-primary/90 hover:to-primary/70 transition-all duration-200 shadow-glow-primary hover:shadow-glow-primary/80"
            >
              <RefreshCw className="w-4 h-4" />
              Reload Extension
            </button>
            
            <button
              onClick={this.handleGoHome}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-muted text-foreground font-semibold rounded-lg hover:bg-muted/80 transition-all duration-200 border border-border/50"
            >
              <Home className="w-4 h-4" />
              Try Again
            </button>
          </div>

          {/* Help Text */}
          <p className="text-xs text-muted-foreground text-center mt-6 max-w-md">
            If this problem persists, please check the browser console for more details or contact support.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
