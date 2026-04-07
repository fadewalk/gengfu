import React from "react";
import Modal from "@/components/ui/Modal";
import { CopilotKit } from "@copilotkit/react-core";
import { ReportAIChatPanel } from "./report-ai-chat-panel";
import { useAIEnabled } from "@/utils/hooks/useAIEnabled";
import { ChatBubbleOvalLeftIcon } from "@heroicons/react/24/outline";
import { useI18n } from "@/i18n/hooks/useI18n";

interface GenerateReportModalProps {
  filterCel?: string;
  selectedIncidentIds?: string[];
  onClose: () => void;
}

export const GenerateReportModal: React.FC<GenerateReportModalProps> = ({
  filterCel,
  selectedIncidentIds,
  onClose,
}) => {
  const { t } = useI18n();
  const { enabled: isAIEnabled, isLoading: isAILoading } = useAIEnabled();

  if (isAILoading) {
    return (
      <Modal
        title={t("incidents.report.title")}
        className="min-w-[90vw] h-[85vh]"
        isOpen={true}
        onClose={onClose}
      >
        <div className="flex items-center justify-center h-full">
          <div className="text-slate-500 text-sm">
            {t("incidents.report.aiChat.description")}
          </div>
        </div>
      </Modal>
    );
  }

  if (!isAIEnabled) {
    return (
      <Modal
        title={t("incidents.report.title")}
        className="min-w-[90vw] h-[85vh]"
        isOpen={true}
        onClose={onClose}
      >
        <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-8">
          <ChatBubbleOvalLeftIcon className="w-16 h-16 text-slate-300" />
          <div>
            <h3 className="text-lg font-semibold text-slate-700">
              {t("incidents.report.title")}
            </h3>
            <p className="text-sm text-slate-500 mt-2 max-w-md">
              {t("incidents.report.aiChat.notEnabled")}
            </p>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      title={t("incidents.report.title")}
      className="min-w-[90vw] h-[85vh]"
      isOpen={true}
      onClose={onClose}
    >
      <CopilotKit runtimeUrl="/api/copilotkit" showDevConsole={false}>
        <ReportAIChatPanel
          filterCel={filterCel}
          incidentIds={selectedIncidentIds}
        />
      </CopilotKit>
    </Modal>
  );
};
