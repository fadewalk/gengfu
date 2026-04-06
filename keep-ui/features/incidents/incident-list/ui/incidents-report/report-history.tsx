"use client";

import React, { useCallback } from "react";
import {
  Badge,
  Button,
  Card,
  Subtitle,
  Title,
  Metric,
  Text,
  Flex,
  Col,
} from "@tremor/react";
import {
  DocumentChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import {
  useReportHistory,
  useAsyncReport,
  AsyncReport,
} from "./use-async-report";
import { useI18n } from "@/i18n/hooks/useI18n";
import { KeepLoader } from "@/shared/ui";
import { IncidentsReport } from "./incidents-report";
import { IncidentData } from "./models";

function ReportStatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const statusConfig = {
    pending: {
      color: "yellow",
      icon: ClockIcon,
      label: t("incidents.report.status.pending"),
    },
    completed: {
      color: "green",
      icon: CheckCircleIcon,
      label: t("incidents.report.status.completed"),
    },
    failed: {
      color: "red",
      icon: XCircleIcon,
      label: t("incidents.report.status.failed"),
    },
  };
  const config =
    statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <Badge color={config.color as any} icon={Icon}>
      {config.label}
    </Badge>
  );
}

function ReportCard({
  report,
  onView,
  isSelected,
}: {
  report: AsyncReport;
  onView: () => void;
  isSelected: boolean;
}) {
  const { t } = useI18n();

  return (
    <Card
      className={`cursor-pointer hover:shadow-md transition-shadow ${
        isSelected ? "ring-2 ring-orange-400" : ""
      }`}
      onClick={onView}
    >
      <Flex alignItems="start" justifyContent="between">
        <div className="flex-1">
          <Text className="font-medium">{report.name}</Text>
          <Text className="text-gray-500 text-sm mt-1">
            {report.created_at
              ? new Date(report.created_at).toLocaleString()
              : "-"}
          </Text>
          {report.created_by && (
            <Text className="text-gray-400 text-xs mt-1">
              {report.created_by}
            </Text>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <ReportStatusBadge status={report.status} />
          {report.filter_cel && (
            <Text className="text-xs text-gray-400 truncate max-w-32">
              CEL: {report.filter_cel}
            </Text>
          )}
          {report.incident_ids && report.incident_ids.length > 0 && (
            <Text className="text-xs text-gray-400">
              {report.incident_ids.length} {t("incidents.report.incidents")}
            </Text>
          )}
        </div>
      </Flex>
    </Card>
  );
}

function ReportDetail({
  reportId,
  onClose,
}: {
  reportId: string;
  onClose: () => void;
}) {
  const { report, isLoading, error } = useAsyncReport({ reportId });
  const { t } = useI18n();

  if (isLoading && !report) {
    return (
      <div className="flex items-center justify-center h-64">
        <KeepLoader />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <Text className="text-red-500">{error}</Text>
      </div>
    );
  }

  if (report?.status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <XCircleIcon className="w-12 h-12 text-red-500" />
        <Text className="text-red-500">
          {t("incidents.report.status.failed")}
        </Text>
        <Text className="text-gray-500 text-sm">{report.error}</Text>
        <Button variant="secondary" onClick={onClose}>
          {t("common.close")}
        </Button>
      </div>
    );
  }

  if (report?.status === "pending") {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <ArrowPathIcon className="w-12 h-12 text-yellow-500 animate-spin" />
        <Text>{t("incidents.report.generating")}</Text>
        <Button variant="secondary" onClick={onClose}>
          {t("common.close")}
        </Button>
      </div>
    );
  }

  if (report?.result) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 overflow-auto">
          <IncidentsReport
            incidentsReportData={report.result as IncidentData}
            generatedAt={
              report.created_at ? new Date(report.created_at) : undefined
            }
          />
        </div>
        <div className="flex justify-end p-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
        </div>
      </div>
    );
  }

  return null;
}

export function ReportHistory() {
  const { t } = useI18n();
  const { reports, isLoading, error, refetch } = useReportHistory();
  const [selectedReportId, setSelectedReportId] = React.useState<string | null>(
    null
  );

  const handleViewReport = useCallback((reportId: string) => {
    setSelectedReportId(reportId);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedReportId(null);
  }, []);

  if (selectedReportId) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <Title>{t("incidents.report.viewReport")}</Title>
          <Button variant="secondary" onClick={handleCloseDetail}>
            {t("incidents.report.backToList")}
          </Button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          <ReportDetail
            reportId={selectedReportId}
            onClose={handleCloseDetail}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <Title>{t("incidents.report.history")}</Title>
          <Subtitle className="text-gray-500">
            {reports.length} {t("incidents.report.reports")}
          </Subtitle>
        </div>
        <Button
          variant="secondary"
          icon={ArrowPathIcon}
          onClick={() => refetch()}
        >
          {t("common.refresh")}
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {isLoading && reports.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <KeepLoader />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-64">
            <Text className="text-red-500">{error}</Text>
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <DocumentChartBarIcon className="w-12 h-12 text-gray-400" />
            <Text className="text-gray-500">
              {t("incidents.report.noReports")}
            </Text>
          </div>
        ) : (
          <div className="space-y-3">
            {reports.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                onView={() => handleViewReport(report.id)}
                isSelected={selectedReportId === report.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
