"use client";
import { Component, ErrorInfo, ReactNode } from 'react';
import { AppError } from '@/errors/AppError';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to monitoring service
    if (error instanceof AppError) {
      console.error('Application error:', {
        ...error.toJSON(),
        componentStack: errorInfo.componentStack,
      });
    } else {
      console.error('Unexpected error:', {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
      });
    }

    // Call custom error handler
    this.props.onError?.(error, errorInfo);

    // Send to monitoring in production
    if (process.env.NODE_ENV === 'production') {
      this.sendToMonitoring(error, errorInfo);
    }
  }

  private sendToMonitoring(error: Error, errorInfo: ErrorInfo) {
    // Integration with Sentry, DataDog, etc.
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      return <DefaultErrorFallback error={this.state.error} onReset={this.handleReset} />;
    }

    return this.props.children;
  }
}

function DefaultErrorFallback({ error, onReset }: { error: Error; onReset: () => void }) {
  const isAppError = error instanceof AppError;

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      <div className="max-w-md w-full bg-red-50/10 backdrop-blur-md border border-red-500/20 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-red-300 mb-2">
          {isAppError ? 'Something went wrong' : 'Unexpected error'}
        </h2>
        
        <p className="text-sm text-red-200 mb-4">
          {error.message}
        </p>

        {isAppError && (error as AppError).code && (
          <p className="text-xs text-red-400 font-mono mb-4">
            Error Code: {(error as AppError).code}
          </p>
        )}

        <div className="flex gap-2">
          <button
            onClick={onReset}
            className="px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700"
          >
            Try Again
          </button>
          
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-white/10 backdrop-blur-sm text-white rounded-xl hover:bg-white/20 border border-white/20"
          >
            Refresh Page
          </button>
        </div>
      </div>
    </div>
  );
}