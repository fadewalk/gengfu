import { useApi } from "@/shared/lib/hooks/useApi";
import { useCallback, useEffect, useState } from "react";

export type ReportStatus = "pending" | "completed" | "failed";

export interface AsyncReport {
  id: string;
  name: string;
  status: ReportStatus;
  filter_cel: string | null;
  incident_ids: string[] | null;
  result: any | null;
  error: string | null;
  created_at: string | null;
  completed_at: string | null;
  created_by: string | null;
}

interface UseAsyncReportOptions {
  reportId?: string;
  pollInterval?: number;
}

export const useAsyncReport = (options: UseAsyncReportOptions = {}) => {
  const { reportId, pollInterval = 2000 } = options;
  const api = useApi();
  const [report, setReport] = useState<AsyncReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!reportId) return;
    try {
      const data = await api.get(`/incidents/reports/${reportId}`);
      setReport(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch report");
      return null;
    }
  }, [api, reportId]);

  useEffect(() => {
    if (!reportId) return;

    setIsLoading(true);
    fetchReport().finally(() => setIsLoading(false));

    // Poll for status if still pending
    const interval = setInterval(async () => {
      const data = await fetchReport();
      if (data && data.status !== "pending") {
        clearInterval(interval);
      }
    }, pollInterval);

    return () => clearInterval(interval);
  }, [reportId, pollInterval, fetchReport]);

  return {
    report,
    isLoading,
    error,
    refetch: fetchReport,
  };
};

interface UseReportHistoryOptions {
  limit?: number;
  offset?: number;
}

export const useReportHistory = (options: UseReportHistoryOptions = {}) => {
  const { limit = 20, offset = 0 } = options;
  const api = useApi();
  const [reports, setReports] = useState<AsyncReport[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get(
        `/incidents/reports?limit=${limit}&offset=${offset}`
      );
      setReports(data.items || []);
      setTotal(data.count || 0);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch report history"
      );
    } finally {
      setIsLoading(false);
    }
  }, [api, limit, offset]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return {
    reports,
    total,
    isLoading,
    error,
    refetch: fetchHistory,
  };
};

export const createAsyncReport = async (
  api: any,
  params: {
    filterCel?: string;
    incidentIds?: string[];
    templateType?: string;
  }
): Promise<{ report_id: string; status: string }> => {
  const { filterCel, incidentIds, templateType = "comprehensive" } = params;
  return await api.post(`/incidents/reports`, {
    cel: filterCel,
    incident_ids: incidentIds,
    template_type: templateType,
  });
};
