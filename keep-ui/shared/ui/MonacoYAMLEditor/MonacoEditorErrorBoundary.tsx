"use client";

import React, { Component, ReactNode } from "react";
import { KeepLoader } from "../KeepLoader/KeepLoader";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  retryKey: number;
}

const MAX_RETRIES = 5;

/**
 * Error boundary to catch getModel() errors from @monaco-editor/react's
 * internal DiffEditor/Editor effects and recover by re-mounting the editor.
 */
export class MonacoEditorErrorBoundary extends Component<Props, State> {
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private retryCount = 0;

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, retryKey: 0 };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true, retryKey: 0 };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    const isRecoverable =
      error.message.includes("getModel") ||
      error.message.includes("create") ||
      error.message.includes("Cannot read properties of undefined");

    if (isRecoverable && this.retryCount < MAX_RETRIES) {
      this.retryCount++;
      console.warn(
        `[MonacoEditorErrorBoundary] Recoverable editor error (attempt ${this.retryCount}/${MAX_RETRIES}):`,
        error.message
      );
      this.scheduleRetry();
    } else {
      console.error("[MonacoEditorErrorBoundary] Unrecoverable error:", error, info);
    }
  }

  private scheduleRetry = () => {
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.retryTimer = setTimeout(() => {
      this.setState((prev) => ({ hasError: false, retryKey: prev.retryKey + 1 }));
    }, 300);
  };

  componentWillUnmount() {
    if (this.retryTimer) clearTimeout(this.retryTimer);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return <KeepLoader loadingText="Recovering editor..." />;
    }
    // key forces full remount on retry
    return <div key={this.state.retryKey}>{this.props.children}</div>;
  }
}
