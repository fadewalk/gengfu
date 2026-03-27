"use client";

import React, { Component, ReactNode } from "react";
import { KeepLoader } from "../KeepLoader/KeepLoader";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Error boundary to catch getModel() errors from @monaco-editor/react's
 * internal DiffEditor/Editor effects and recover by re-mounting the editor.
 */
export class MonacoEditorErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // getModel() and create() errors from @monaco-editor/react are non-fatal;
    // re-mounting the editor recovers.
    if (error.message.includes("getModel") || error.message.includes("create")) {
      console.warn(
        "[MonacoEditorErrorBoundary] Caught editor error, re-mounting:",
        error.message
      );
    } else {
      console.error("[MonacoEditorErrorBoundary]", error, info);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return <KeepLoader loadingText="Recovering editor..." />;
    }
    return this.props.children;
  }
}
