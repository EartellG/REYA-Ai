import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export default class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("🛑 Error caught by REYA ErrorBoundary:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    // Optionally reload page or reset app state
    // window.location.reload();
  };

  render() {
    const { hasError, error, errorInfo } = this.state;

    if (hasError) {
      return (
        this.props.fallback || (
          <div className="p-10 text-center text-red-400 bg-gray-900 h-full">
            <h2 className="text-2xl font-bold mb-4">💥 REYA Crashed</h2>
            <p className="mb-2">Something went wrong in the UI.</p>
            {error && <pre className="text-sm">{error.message}</pre>}
            {errorInfo && (
              <details className="text-xs mt-4 whitespace-pre-wrap">
                {errorInfo.componentStack}
              </details>
            )}
            <button
              onClick={this.handleReset}
              className="mt-4 px-4 py-2 bg-red-700 text-white rounded"
            >
              Try Again
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
