"use client";

import { CopilotKit } from "@copilotkit/react-core";
import {
  WorkflowBuilderWidget,
  WorkflowBuilderWidgetProps,
} from "./workflow-builder-widget";
import { useAIEnabled } from "@/utils/hooks/useAIEnabled";

export function WorkflowBuilderWidgetSafe(props: WorkflowBuilderWidgetProps) {
  const { enabled: isAIEnabled, isLoading } = useAIEnabled();

  // If loading, render without CopilotKit temporarily
  if (isLoading || !isAIEnabled) {
    return <WorkflowBuilderWidget {...props} />;
  }

  return (
    <CopilotKit runtimeUrl="/api/copilotkit" showDevConsole={false} data-testid="copilot-wrapper">
      <WorkflowBuilderWidget {...props} />
    </CopilotKit>
  );
}
