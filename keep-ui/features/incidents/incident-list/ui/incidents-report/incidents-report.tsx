import React, { useMemo } from "react";
import { IncidentData, ReportTemplateType } from "./models";
import { IncidentSeverityMetric } from "./incident-severity-metric";
import { PieChart } from "./pie-chart";
import { useI18n } from "@/i18n/hooks/useI18n";
import { Card, Title, Text, Badge } from "@tremor/react";
import {
  DocumentChartBarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowTrendingUpIcon,
  LightBulbIcon,
  ShieldExclamationIcon,
  MagnifyingGlassCircleIcon,
} from "@heroicons/react/24/outline";

interface IncidentsReportProps {
  incidentsReportData: IncidentData;
  filterCel?: string;
  generatedAt?: Date;
  templateType?: ReportTemplateType;
}

export const IncidentsReport: React.FC<IncidentsReportProps> = ({
  incidentsReportData,
  filterCel,
  generatedAt,
  templateType = "comprehensive",
}) => {
  const { t } = useI18n();

  // 计算事件统计
  const incidentStats = useMemo(() => {
    const severityMetrics = incidentsReportData?.severity_metrics || {};
    const total = Object.values(severityMetrics).reduce(
      (sum, items) => sum + (items?.length || 0),
      0
    );
    return { total };
  }, [incidentsReportData]);

  function convertSeconds(secondsValue: number): string {
    const result = [];

    const secondsInMinute = 60;
    const secondsInHour = 60 * secondsInMinute;
    const secondsInDay = 24 * secondsInHour;
    const secondsInWeek = 7 * secondsInDay;
    const secondsInMonth = 30 * secondsInDay;

    const months = Math.floor(secondsValue / secondsInMonth);
    secondsValue %= secondsInMonth;

    const weeks = Math.floor(secondsValue / secondsInWeek);
    secondsValue %= secondsInWeek;

    const days = Math.floor(secondsValue / secondsInDay);
    secondsValue %= secondsInDay;

    const hours = Math.floor(secondsValue / secondsInHour);
    secondsValue %= secondsInHour;

    const minutes = Math.floor(secondsValue / secondsInMinute);
    const seconds = secondsValue % secondsInMinute;

    if (months > 0) result.push(`${months} ${t("common.time.months")}`);
    if (weeks > 0) result.push(`${weeks} ${t("common.time.weeks")}`);
    if (days > 0) result.push(`${days} ${t("common.time.days")}`);
    if (hours > 0) result.push(`${hours} ${t("common.time.hours")}`);
    if (minutes > 0) result.push(`${minutes} ${t("common.time.minutes")}`);
    if (seconds > 0) result.push(`${seconds} ${t("common.time.seconds")}`);

    return result.join(" ");
  }

  function renderReportHeader(): React.JSX.Element {
    return (
      <div className="bg-gradient-to-r from-slate-50 to-orange-50 rounded-lg p-4 mb-6 border border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <DocumentChartBarIcon className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <Title className="text-xl text-slate-800">
                {t("incidents.report.title")}
              </Title>
              <Text className="text-slate-500 text-sm">
                {generatedAt && (
                  <span className="flex items-center gap-1">
                    <ClockIcon className="w-3 h-3" />
                    {generatedAt.toLocaleString()}
                  </span>
                )}
              </Text>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <Text className="text-sm text-slate-500">
                {t("incidents.report.totalIncidents")}
              </Text>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-slate-800">
                  {incidentStats.total}
                </span>
                <Badge color="orange" size="sm">
                  {t("incidents.report.incidents")}
                </Badge>
              </div>
            </div>
          </div>
        </div>
        {filterCel && (
          <div className="mt-3 pt-3 border-t border-slate-200">
            <Text className="text-xs text-slate-500">
              {t("incidents.report.filterCondition")}:{" "}
              <code className="bg-slate-100 px-1 py-0.5 rounded text-orange-600 font-mono text-xs">
                {filterCel}
              </code>
            </Text>
          </div>
        )}
      </div>
    );
  }

  function renderTimeMetric(
    metricName: string,
    metricValueInSeconds: number | undefined,
    icon: React.ElementType
  ): React.JSX.Element {
    return (
      <div className="flex items-center gap-3 py-2">
        <div className={`p-2 rounded-lg bg-gradient-to-br`}>
          {React.createElement(icon, {
            className: "w-5 h-5 text-orange-600",
          })}
        </div>
        <div>
          <Text className="text-sm text-slate-500">{metricName}</Text>
          <Text className="font-semibold text-slate-800">
            {metricValueInSeconds ? convertSeconds(metricValueInSeconds) : "-"}
          </Text>
        </div>
      </div>
    );
  }

  function renderTimeMetrics(): React.JSX.Element {
    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ArrowTrendingUpIcon className="w-5 h-5 text-orange-600" />
          <Title className="text-lg">
            {t("incidents.report.incidentMetrics")}
          </Title>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {renderTimeMetric(
            t("incidents.report.mTTD"),
            incidentsReportData?.mean_time_to_detect_seconds,
            ExclamationTriangleIcon
          )}
          {renderTimeMetric(
            t("incidents.report.mTTR"),
            incidentsReportData?.mean_time_to_resolve_seconds,
            CheckCircleIcon
          )}
          {incidentsReportData?.incident_durations &&
            renderTimeMetric(
              t("incidents.report.shortestDuration"),
              incidentsReportData?.incident_durations
                ?.shortest_duration_seconds,
              ClockIcon
            )}
          {incidentsReportData?.incident_durations &&
            renderTimeMetric(
              t("incidents.report.longestDuration"),
              incidentsReportData?.incident_durations?.longest_duration_seconds,
              ClockIcon
            )}
        </div>
      </Card>
    );
  }

  function renderMainReasons(): React.JSX.Element {
    const reasons = Object.entries(
      incidentsReportData?.most_frequent_reasons || {}
    );
    if (reasons.length === 0) return <></>;

    // 计算最大计数用于进度条宽度
    const maxCount = Math.max(...reasons.map(([, ids]) => ids.length), 1);

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ExclamationTriangleIcon className="w-5 h-5 text-orange-600" />
          <Title className="text-lg">
            {t("incidents.report.mostCommonReasons")}
          </Title>
        </div>
        <div className="space-y-3">
          {reasons.slice(0, 6).map(([reason, incidentIds]) => {
            const count = incidentIds.length;
            const widthPercent = (count / maxCount) * 100;
            return (
              <div key={reason} className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-1">
                  <Badge
                    color="orange"
                    size="sm"
                    className="font-bold min-w-[28px] justify-center"
                  >
                    {count}
                  </Badge>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <Text className="text-slate-700 text-sm">{reason}</Text>
                      <Text className="text-xs text-slate-400">
                        {count} {t("incidents.report.incidents")}
                      </Text>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-orange-400 to-orange-500 rounded-full transition-all duration-500"
                        style={{ width: `${widthPercent}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    );
  }

  function renderAffectedServices(): React.JSX.Element {
    const services = Object.entries(
      incidentsReportData?.services_affected_metrics || {}
    );
    if (services.length === 0) return <></>;

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <DocumentChartBarIcon className="w-5 h-5 text-orange-600" />
          <Title className="text-lg">
            {t("incidents.report.affectedServices")}
          </Title>
        </div>
        <div className="flex flex-wrap gap-2">
          {services.map(([service, count]) => (
            <Badge key={service} color="slate" size="sm" className="px-3 py-1">
              {service}: {count}
            </Badge>
          ))}
        </div>
      </Card>
    );
  }

  function renderRecurringIncidents(): React.JSX.Element {
    const recurring = incidentsReportData?.recurring_incidents || [];
    if (recurring.length === 0) return <></>;

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ArrowTrendingUpIcon className="w-5 h-5 text-orange-600" />
          <Title className="text-lg">
            {t("incidents.report.recurringIncidents")}
          </Title>
        </div>
        <div className="space-y-2">
          {recurring.map((incident) => (
            <div
              key={incident.incident_id || ""}
              className="flex items-center justify-between p-2 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Badge color="yellow" size="sm">
                  {incident.occurrence_count}x
                </Badge>
                <Text className="text-sm text-slate-700">
                  {incident.incident_name}
                </Text>
              </div>
              <Text className="text-xs text-slate-400 font-mono">
                {incident.incident_id?.slice(0, 8) || ""}...
              </Text>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  /** Render AI trend analysis section */
  function renderTrendAnalysis(): React.JSX.Element {
    const analysis = incidentsReportData?.trend_analysis;
    if (!analysis) return <></>;

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ArrowTrendingUpIcon className="w-5 h-5 text-green-600" />
          <Title className="text-lg">
            {t("incidents.report.trendAnalysis")}
          </Title>
        </div>
        <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-line">
          {analysis}
        </div>
      </Card>
    );
  }

  /** Render AI root cause analysis section */
  function renderRootCauseAnalysis(): React.JSX.Element {
    const analysis = incidentsReportData?.root_cause_analysis;
    if (!analysis) return <></>;

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <MagnifyingGlassCircleIcon className="w-5 h-5 text-orange-600" />
          <Title className="text-lg">
            {t("incidents.report.rootCauseAnalysis")}
          </Title>
        </div>
        <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-line">
          {analysis}
        </div>
      </Card>
    );
  }

  /** Render AI recommendations section */
  function renderRecommendations(): React.JSX.Element {
    const recommendations = incidentsReportData?.recommendations;
    if (!recommendations || recommendations.length === 0) return <></>;

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <LightBulbIcon className="w-5 h-5 text-amber-500" />
          <Title className="text-lg">
            {t("incidents.report.recommendations")}
          </Title>
        </div>
        <ol className="space-y-3">
          {recommendations.map((rec, idx) => (
            <li key={idx} className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-semibold">
                {idx + 1}
              </span>
              <Text className="text-sm text-slate-700 leading-relaxed">
                {rec}
              </Text>
            </li>
          ))}
        </ol>
      </Card>
    );
  }

  /** Render AI risk assessment section */
  function renderRiskAssessment(): React.JSX.Element {
    const assessment = incidentsReportData?.risk_assessment;
    if (!assessment) return <></>;

    return (
      <Card className="bg-white border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ShieldExclamationIcon className="w-5 h-5 text-red-600" />
          <Title className="text-lg">
            {t("incidents.report.riskAssessment")}
          </Title>
        </div>
        <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-line">
          {assessment}
        </div>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-6 py-4 bg-slate-50 min-h-full">
      {renderReportHeader()}
      {renderTimeMetrics()}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {incidentsReportData?.severity_metrics && (
          <IncidentSeverityMetric
            severityMetrics={incidentsReportData.severity_metrics}
          />
        )}
        {incidentsReportData?.most_frequent_reasons && renderMainReasons()}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {incidentsReportData?.services_affected_metrics &&
          renderAffectedServices()}
        {incidentsReportData?.recurring_incidents && renderRecurringIncidents()}
      </div>
      {/* AI-enhanced analysis sections */}
      {(templateType === "comprehensive" || templateType === "trend") &&
        renderTrendAnalysis()}
      {(templateType === "comprehensive" || templateType === "root_cause") &&
        renderRootCauseAnalysis()}
      {(templateType === "comprehensive" || templateType === "root_cause" || templateType === "deep") &&
        renderRecommendations()}
      {(templateType === "comprehensive" || templateType === "deep") &&
        renderRiskAssessment()}
    </div>
  );
};
