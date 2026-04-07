import { useApi } from "@/shared/lib/hooks/useApi";
import { IncidentData, ReportTemplateType } from "./models";
import { useCallback, useState } from "react";

interface UseReportDataOptions {
  filterCel?: string;
  incidentIds?: string[];
  templateType?: ReportTemplateType;
}

export const useReportData = (options: UseReportDataOptions = {}) => {
  const { filterCel, incidentIds, templateType = "comprehensive" } = options;
  const api = useApi();
  const [data, setData] = useState<IncidentData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(() => {
    if (!api.isReady()) return;
    setIsLoading(true);
    setError(null);
    setData(null);

    const promise =
      incidentIds && incidentIds.length > 0
        ? api.post(`/incidents/report`, {
            incident_ids: incidentIds,
            template_type: templateType,
          })
        : api.get(
            filterCel
              ? `/incidents/report?cel=${filterCel}`
              : `/incidents/report`
          );

    promise
      .then((result) => {
        setData(result);
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err?.message || "Failed to generate report");
        setIsLoading(false);
      });
  }, [api, filterCel, incidentIds, templateType]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    data,
    isLoading,
    error,
    generate,
    reset,
  };
};
