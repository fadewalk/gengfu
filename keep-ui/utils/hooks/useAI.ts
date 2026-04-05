import { useWebsocket } from "./usePusher";
import { useCallback, useEffect } from "react";
import { useApi } from "@/shared/lib/hooks/useApi";
import { AIConfig, AILogs, AIStats } from "@/app/(keep)/ai/model";
import useSWR, { SWRConfiguration } from "swr";

export const useAIStats = (
  options: SWRConfiguration = {
    revalidateOnFocus: false,
  }
) => {
  const api = useApi();

  return useSWR<AIStats>(
    api.isReady() ? "/ai/stats" : null,
    (url) => api.get(url),
    {
      ...options,
      onErrorRetry: (error, _key, _config, revalidate, { retryCount }) => {
        // Stop retrying on 4xx errors (e.g. no model configured)
        if (error?.status >= 400 && error?.status < 500) return;
        // Limit retries for 5xx errors
        if (retryCount >= 3) return;
        revalidate({ retryCount });
      },
    }
  );
};

export const usePollAILogs = (mutateAILogs: (logs: AILogs) => void) => {
  const { bind, unbind } = useWebsocket();
  const handleIncoming = useCallback(
    (data: AILogs) => {
      mutateAILogs(data);
    },
    [mutateAILogs]
  );

  useEffect(() => {
    bind("ai-logs-change", handleIncoming);
    return () => {
      unbind("ai-logs-change", handleIncoming);
    };
  }, [bind, unbind, handleIncoming]);
};

type UseAIActionsValue = {
  updateAISettings: (
    algorithm_id: string,
    settings: AIConfig
  ) => Promise<AIStats>;
  triggerCorrelation: () => Promise<CorrelationResult>;
};

export interface CorrelationResult {
  status: string;
  message?: string;
  alerts_analyzed: number;
  incidents_suggested: number;
  incidents_above_threshold?: number;
  incidents_created: number;
  suggestion_id?: string;
  correlated_count?: number;
}

export function useAIActions(): UseAIActionsValue {
  const api = useApi();

  const updateAISettings = async (
    algorithm_id: string,
    settings: AIConfig
  ): Promise<AIStats> => {
    const settingsToUpdate = {
      ...settings,
      settings_proposed_by_algorithm: null,
    };

    const response = await api.put<AIStats>(
      `/ai/${algorithm_id}/settings`,
      settingsToUpdate
    );

    if (!response) {
      throw new Error("Failed to update AI settings");
    }
    return response;
  };

  const triggerCorrelation = async (): Promise<CorrelationResult> => {
    const response = await api.post<CorrelationResult>("/ai/correlate");
    if (!response) {
      throw new Error("Failed to trigger AI correlation");
    }
    return response;
  };

  return {
    updateAISettings,
    triggerCorrelation,
  };
}
