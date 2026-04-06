import React, { useMemo } from "react";
import { SeverityMetrics } from "./models";
import { DonutChart } from "@tremor/react";
import {
  getSeverityBgClassName,
  UISeverity,
} from "@/shared/ui/utils/severity-utils";
import { useI18n } from "@/i18n/hooks/useI18n";
import { Card, Title, Badge } from "@tremor/react";
import { ExclamationCircleIcon } from "@heroicons/react/24/outline";

interface IncidentSeverityMetricProps {
  severityMetrics: SeverityMetrics;
}

export const IncidentSeverityMetric: React.FC<IncidentSeverityMetricProps> = ({
  severityMetrics: severityMetric,
}) => {
  const { t } = useI18n();
  const sortedByValue = useMemo(() => {
    Object.entries(severityMetric);
    return Object.entries(severityMetric)
      .map(([name, value]) => ({ name, value: value.length }))
      .sort((a, b) => b.value - a.value);
  }, [severityMetric]);

  const severityBgColorDictionary = useMemo(
    () =>
      Object.fromEntries(
        Object.values(UISeverity).map((severity) => [
          severity,
          getSeverityBgClassName(severity),
        ])
      ),
    []
  );

  const severityColorsSorted = useMemo(
    () =>
      sortedByValue.map((chartValue) =>
        getSeverityBgClassName(chartValue.name as UISeverity).replace("bg-", "")
      ),
    [sortedByValue]
  );

  function translateSeverity(name: string): string {
    const key = `incidents.severity.${name}` as const;
    const translated = t(key);
    return translated !== key ? translated : name;
  }

  function formatIncidentsCount(count: number): string {
    return count > 1
      ? t("incidents.report.incidentCountPlural", { count })
      : t("incidents.report.incidentCountSingle");
  }

  return (
    <Card className="bg-white border border-slate-100 shadow-sm h-full">
      <div className="flex items-center gap-2 mb-4">
        <ExclamationCircleIcon className="w-5 h-5 text-orange-600" />
        <Title className="text-lg">{t("incidents.report.incidentsSeverity")}</Title>
      </div>
      <div className="flex items-center gap-6">
        <DonutChart
          className="w-36 h-36"
          data={sortedByValue}
          colors={severityColorsSorted}
          variant="pie"
          showAnimation={true}
        />
        <div className="flex-col flex-1 space-y-2">
          {sortedByValue.map((chartValue) => (
            <div key={chartValue.name} className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${severityBgColorDictionary[chartValue.name]}`}
              ></div>
              <span className="font-medium text-slate-700">
                {translateSeverity(chartValue.name)}
              </span>
              <Badge color="slate" size="sm" className="ml-auto">
                {formatIncidentsCount(chartValue.value)}
              </Badge>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};
