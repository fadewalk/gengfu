"use client";

import { Editor, EditorProps, loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { useEffect, useRef, useState } from "react";
import { MonacoEditorErrorBoundary } from "../MonacoYAMLEditor/MonacoEditorErrorBoundary";

interface MonacoCelProps extends EditorProps {
  onMonacoLoaded?: (monacoInstance: typeof import("monaco-editor")) => void;
  onMonacoLoadFailure?: (error: Error) => void;
}

// Monaco Editor - imported as an npm package instead of loading from the CDN to support air-gapped environments
// https://github.com/suren-atoyan/monaco-react?tab=readme-ov-file#use-monaco-editor-as-an-npm-package
// For @monaco-editor/react 4.7.0-rc.0 / @monaco-editor/loader 1.7.0:
//   pass the monaco module object directly — the function form `monaco: () => import(...)` is a 4.8.x API
loader.config({ monaco });

export function MonacoCelBase(props: MonacoCelProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const onMonacoLoadedRef = useRef<MonacoCelProps["onMonacoLoaded"] | null>(
    null
  );
  onMonacoLoadedRef.current = props.onMonacoLoaded;
  const onMonacoLoadFailureRef = useRef<
    MonacoCelProps["onMonacoLoadFailure"] | null
  >(null);
  onMonacoLoadFailureRef.current = props.onMonacoLoadFailure;

  useEffect(() => {
    loader
      .init()
      .then((monacoInstance) => {
        onMonacoLoadedRef.current?.(monacoInstance);
        setIsLoaded(true);
      })
      .catch((error: Error) => {
        onMonacoLoadFailureRef.current?.(error);
      });
  }, []);

  if (!isLoaded) {
    return null;
  }

  return (
    <MonacoEditorErrorBoundary>
      <Editor {...props} />
    </MonacoEditorErrorBoundary>
  );
}
