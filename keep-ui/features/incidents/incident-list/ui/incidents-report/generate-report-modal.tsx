import React, { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui";
import Modal from "@/components/ui/Modal";
import { KeepLoader } from "@/shared/ui";
import { useReactToPrint } from "react-to-print";
import { CopilotKit } from "@copilotkit/react-core";
import { useReportData } from "./use-report-data";
import { IncidentData, ReportTemplateType } from "./models";
import { IncidentsReport } from "./incidents-report";
import { ReportTemplateNav } from "./report-template-nav";
import { ReportAIChatPanel } from "./report-ai-chat-panel";
import { useAIEnabled } from "@/utils/hooks/useAI";
import { PrinterIcon, ChatBubbleOvalLeftIcon } from "@heroicons/react/24/outline";
import { useI18n } from "@/i18n/hooks/useI18n";

interface GenerateReportModalProps {
  filterCel?: string;
  selectedIncidentIds?: string[];
  asyncMode?: boolean;
  onClose: () => void;
  onNavigateToHistory?: () => void;
}

export const GenerateReportModal: React.FC<GenerateReportModalProps> = ({
  filterCel,
  selectedIncidentIds,
  onClose,
}) => {
  const [selectedTemplate, setSelectedTemplate] =
    useState<string>("comprehensive");
  const { t } = useI18n();

  return (
    <Modal
      title={t("incidents.report.title")}
      className="min-w-[90vw] h-[85vh]"
      isOpen={true}
      onClose={onClose}
    >
      <div className="flex w-full h-full overflow-hidden">
        {/* Left panel: template navigation */}
        <ReportTemplateNav
          selected={selectedTemplate}
          onSelect={setSelectedTemplate}
        />
        {/* Right panel: report content or AI chat */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedTemplate === "ai_chat" ? (
            <AIChatPanel
              filterCel={filterCel}
              incidentIds={selectedIncidentIds}
            />
          ) : (
            <ReportContentPanel
              filterCel={filterCel}
              incidentIds={selectedIncidentIds}
              templateType={selectedTemplate as ReportTemplateType}
            />
          )}
        </div>
      </div>
    </Modal>
  );
};

/** Report content panel for predefined templates */
function ReportContentPanel({
  filterCel,
  incidentIds,
  templateType,
}: {
  filterCel?: string;
  incidentIds?: string[];
  templateType: ReportTemplateType;
}) {
  const { data, isLoading } = useReportData({
    filterCel,
    incidentIds,
    templateType,
  });
  const { t } = useI18n();
  const contentRef = useRef<HTMLDivElement>(null);
  const reactToPrintFn = useReactToPrint({
    contentRef,
    documentTitle: "Incidents Report",
  });

  const handlePrint = useCallback(() => reactToPrintFn(), [reactToPrintFn]);

  return (
    <div className="flex flex-col w-full h-full">
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <KeepLoader />
          </div>
        )}
        {!isLoading && data && (
          <div ref={contentRef}>
            <IncidentsReport
              incidentsReportData={data as IncidentData}
              filterCel={filterCel}
              generatedAt={new Date()}
              templateType={templateType}
            />
          </div>
        )}
      </div>
      {!isLoading && data && (
        <div className="flex justify-end p-4 border-t border-slate-100">
          <Button
            color="orange"
            variant="primary"
            size="md"
            icon={PrinterIcon}
            onClick={handlePrint}
          >
            {t("incidents.report.print")}
          </Button>
        </div>
      )}
    </div>
  );
}

/** AI chat analysis panel with CopilotKit integration */
function AIChatPanel({
  filterCel,
  incidentIds,
}: {
  filterCel?: string;
  incidentIds?: string[];
}) {
  const { t } = useI18n();
  const isAIEnabled = useAIEnabled();

  if (!isAIEnabled) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-8">
        <ChatBubbleOvalLeftIcon className="w-16 h-16 text-slate-300" />
        <div>
          <h3 className="text-lg font-semibold text-slate-700">
            {t("incidents.report.aiChat.title")}
          </h3>
          <p className="text-sm text-slate-500 mt-2 max-w-md">
            {t("incidents.report.aiChat.notEnabled")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <CopilotKit runtimeUrl="/api/copilotkit" showDevConsole={false}>
      <ReportAIChatPanel
        filterCel={filterCel}
        incidentIds={incidentIds}
      />
    </CopilotKit>
  );
}
