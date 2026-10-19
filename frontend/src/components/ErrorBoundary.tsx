import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Optional label shown in the console/report so we know which subtree failed. */
  label?: string;
}

/**
 * Top-level React error boundary.
 *
 * Without this, any uncaught render error (e.g. an undefined setter passed as a
 * prop) unmounts the whole tree and the user sees a blank white page with no
 * way to recover. Here we keep the failure contained and give the user a
 * reload button plus the actual message so it can be reported.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Keep the full component stack in the console for debugging. The UI only
    // shows the short message to avoid dumping internals to end users.
    console.error(
      `[ErrorBoundary${this.props.label ? `: ${this.props.label}` : ''}] Uncaught render error`,
      error,
      errorInfo.componentStack,
    );
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen w-full flex-col items-center justify-center gap-4 bg-[#09090b] p-6 text-center text-slate-200">
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-rose-500/40 bg-rose-500/10">
          <span className="text-2xl leading-none text-rose-400">!</span>
        </div>

        <div className="space-y-1.5">
          <h1 className="font-['Outfit',_sans-serif] text-lg font-bold text-white">
            Terjadi kesalahan tak terduga
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-slate-400">
            Antarmuka berhenti karena sebuah error. Coba muat ulang halaman. Kalau masalah ini
            muncul terus, salin pesan di bawah saat melapor.
          </p>
        </div>

        {this.state.error?.message && (
          <pre className="max-h-40 max-w-lg overflow-auto rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-left font-mono text-[11px] leading-relaxed text-rose-300">
            {this.state.error.message}
          </pre>
        )}

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={this.handleReload}
            className="rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-4 py-2 text-xs font-bold text-emerald-300 transition-colors hover:bg-emerald-500/25"
          >
            Muat Ulang Halaman
          </button>
          <button
            type="button"
            onClick={this.handleReset}
            className="rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-2 text-xs font-semibold text-slate-300 transition-colors hover:bg-slate-800"
          >
            Coba Lagi
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
