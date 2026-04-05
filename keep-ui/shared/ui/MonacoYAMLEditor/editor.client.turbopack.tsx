"use client";

// NOTE: this file is only used for turbopack, so it uses the CDN version of monaco-editor and pre-built monaco-yaml workers

import { useEffect, useState } from "react";
import { configureMonacoYaml, MonacoYaml } from "monaco-yaml";
import { DiffEditor, Editor, loader } from "@monaco-editor/react";
import { KeepLoader, ErrorComponent } from "@/shared/ui";
import { MonacoYamlEditorProps } from "./MonacoYAMLEditor.types";
import { MonacoEditorErrorBoundary } from "./MonacoEditorErrorBoundary";
const Loader = <KeepLoader loadingText="Loading Code Editor ..." />;

// IDC 离线部署：从本地 /public/monaco-vs/ 加载，无需 CDN
// 此目录需在构建时由 Dockerfile 从 node_modules 复制到 public/
const MONACO_VS_PATH =
  typeof window !== "undefined"
    ? window.location.origin + "/monaco-vs/vs"
    : "/monaco-vs/vs";

loader.config({
  paths: {
    vs: MONACO_VS_PATH,
  },
});

// In the docs, it is stated that there should only be one monaco yaml instance configured at a time
let monacoYamlInstance: MonacoYaml | undefined;

self.MonacoEnvironment = {
  getWorker(_, label) {
    switch (label) {
      case "yaml":
        return new window.Worker(
          window.location.origin + "/monaco-workers/yaml.worker.js"
        );
      case "json":
        return new window.Worker(
          window.location.origin + "/monaco-workers/json.worker.js"
        );
      case "editorWorkerService":
        return new window.Worker(
          window.location.origin + "/monaco-workers/editor.worker.js"
        );
      default:
        throw new Error(`Unknown label ${label}`);
    }
  },
};

/**
 * This is a custom editor component that uses 'monaco-yaml' to provide YAML language support.
 * It is used to edit YAML files.
 */
export function MonacoYAMLEditorTurbopack({
  schemas,
  original,
  modified,
  ...props
}: MonacoYamlEditorProps) {
  const [error, setError] = useState<Error | null>(null);
  const [isMonacoInitialized, setIsMonacoInitialized] = useState(false);

  useEffect(() => {
    if (schemas && isMonacoInitialized) {
      monacoYamlInstance?.update({
        enableSchemaRequest: false,
        schemas,
      });
    }
  }, [schemas, isMonacoInitialized]);

  useEffect(() => {
    loader
      .init()
      .then((monacoInstance) => {
        if (!monacoYamlInstance) {
          monacoYamlInstance = configureMonacoYaml(monacoInstance, {
            hover: true,
            completion: true,
            validate: true,
            format: true,
            enableSchemaRequest: false,
            schemas: schemas ?? undefined,
          });
        }
        setIsMonacoInitialized(true);
      })
      .catch((error: Error) => {
        setError(error);
      });
  }, []);

  if (error) {
    return (
      <ErrorComponent
        error={error}
        defaultMessage={`Error loading Monaco Editor`}
        description="Please refresh the page and try again"
      />
    );
  }

  if (original && modified) {
    // DiffEditor's onMount/onChange signatures differ from Editor's.
    // Passing them through causes getModel() errors because the diff editor
    // instance isn't ready when the callback fires.
    const {
      onMount: _onMount,
      onChange: _onChange,
      ...diffProps
    } = props as MonacoYamlEditorProps & Record<string, unknown>;
    return (
      <MonacoEditorErrorBoundary>
        <DiffEditor
          original={original}
          modified={modified}
          language="yaml"
          loading={Loader}
          {...diffProps}
        />
      </MonacoEditorErrorBoundary>
    );
  }

  return (
    <MonacoEditorErrorBoundary>
      <Editor language="yaml" loading={Loader} {...props} />
    </MonacoEditorErrorBoundary>
  );
}
