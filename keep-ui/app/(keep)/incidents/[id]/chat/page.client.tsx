"use client";

import { IncidentChat } from "./incident-chat";
import { IncidentDto } from "@/entities/incidents/model";
import { useAIEnabled } from "@/utils/hooks/useAIEnabled";
import { CopilotKit } from "@copilotkit/react-core";

export function IncidentChatClientPage({
  incident,
  mutateIncident,
}: {
  incident: IncidentDto;
  mutateIncident: () => void;
}) {
  const { enabled: isAIEnabled, isLoading } = useAIEnabled();

  // If loading, show nothing briefly
  if (isLoading) {
    return null;
  }

  // If AI is not enabled, return null to collapse the chat section
  if (!isAIEnabled) {
    return null;
  }

  return (
    <CopilotKit showDevConsole={false} runtimeUrl="/api/copilotkit">
      <IncidentChat incident={incident} mutateIncident={mutateIncident} />
    </CopilotKit>
  );
}
