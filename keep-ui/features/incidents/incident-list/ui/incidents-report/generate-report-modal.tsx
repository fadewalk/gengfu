import React, { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui";
import Modal from "@/components/ui/Modal";
import { KeepLoader } from "@/shared/ui";
import { Title } from "@tremor/react";
import { useReactToPrint } from "react-to-print";
import { useReportData } from "./use-report-data";
import { IncidentData } from "./models";
import { IncidentsReport } from "./incidents-report";
import {
  PrinterIcon,
  ClockIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { useI18n } from "@/i18n/hooks/useI18n";
import { useApi } from "@/shared/lib/hooks/useApi";
import { createAsyncReport } from "./use-async-report";

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
  asyncMode = false,
  onClose,
  onNavigateToHistory,
}) => {
  const { data, isLoading } = useReportData({
    filterCel,
    incidentIds: selectedIncidentIds,
  });
  const { t } = useI18n();
  const api = useApi();
  const [isCreating, setIsCreating] = useState(false);
  const [createdReportId, setCreatedReportId] = useState<string | null>(null);

  const contentRef = useRef<HTMLDivElement>(null);
  const reactToPrintFn = useReactToPrint({
    contentRef,
    documentTitle: "Incidents Report",
  });

  const handlePrint = useCallback(() => reactToPrintFn(), [reactToPrintFn]);

  const handleCreateAsyncReport = useCallback(async () => {
    setIsCreating(true);
    try {
      const result = await createAsyncReport(api, {
        filterCel,
        incidentIds: selectedIncidentIds,
      });
      setCreatedReportId(result.report_id);
    } catch (error) {
      console.error("Failed to create async report:", error);
    } finally {
      setIsCreating(false);
    }
  }, [api, filterCel, selectedIncidentIds]);

  // Async mode with report created notification
  if (asyncMode) {
    return (
      <Modal
        title={t("incidents.report.title")}
        className="min-w-[500px]"
        isOpen={true}
        onClose={onClose}
      >
        <div className="flex flex-col items-center justify-center gap-6 py-8">
          {isCreating ? (
            <>
              <KeepLoader />
              <p className="text-gray-500">{t("incidents.report.creating")}</p>
            </>
          ) : createdReportId ? (
            <>
              <ClockIcon className="w-16 h-16 text-yellow-500" />
              <div className="text-center">
                <Title className="text-lg mb-2">
                  {t("incidents.report.submitted")}
                </Title>
                <p className="text-gray-500 text-sm mb-4">
                  {t("incidents.report.submittedDesc")}
                </p>
              </div>
              <div className="flex gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    onClose();
                    onNavigateToHistory?.();
                  }}
                >
                  {t("incidents.report.viewHistory")}
                </Button>
                <Button variant="primary" onClick={onClose}>
                  {t("common.close")}
                </Button>
              </div>
            </>
          ) : (
            <>
              <ClockIcon className="w-16 h-16 text-blue-500" />
              <div className="text-center">
                <Title className="text-lg mb-2">
                  {t("incidents.report.asyncTitle")}
                </Title>
                <p className="text-gray-500 text-sm mb-4">
                  {t("incidents.report.asyncDesc")}
                </p>
              </div>
              <div className="flex gap-3">
                <Button
                  color="orange"
                  variant="primary"
                  onClick={handleCreateAsyncReport}
                >
                  {t("incidents.report.generateAsync")}
                </Button>
                <Button variant="secondary" onClick={onClose}>
                  {t("common.cancel")}
                </Button>
              </div>
            </>
          )}
        </div>
      </Modal>
    );
  }

  // Sync mode (original behavior)
  return (
    <Modal
      title={t("incidents.report.title")}
      className="min-w-[80vw] h-[80vh]"
      isOpen={true}
      onClose={onClose}
    >
      <div className="w-full h-full">
        {isLoading && <KeepLoader />}
        {!isLoading && (
          <div className="flex flex-col w-full h-full">
            <div className="flex-1 overflow-auto">
              <div ref={contentRef}>
                <IncidentsReport
                  incidentsReportData={data as IncidentData}
                  filterCel={filterCel}
                  generatedAt={new Date()}
                />
              </div>
            </div>
            <div className="flex justify-end p-6 border-teal-100 border-t">
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
          </div>
        )}
      </div>
    </Modal>
  );
};
