import useSWR from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useConfig } from "@/utils/hooks/useConfig";

interface AIStatus {
  ai_available: boolean;
  source: "environment" | "database" | "none";
}

/**
 * Check if AI features are available by combining:
 * 1. Environment variable check (OPEN_AI_API_KEY_SET from server config)
 * 2. Database AI model configs (via /ai/status API)
 */
export function useAIEnabled() {
  const { data: config } = useConfig();
  const api = useApi();

  const { data, error, isLoading } = useSWR<AIStatus>(
    api.isReady() ? "/ai/status" : null,
    (url: string) => api.get(url),
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
      onErrorRetry: (err, _key, _config, revalidate, { retryCount }) => {
        if (err?.status >= 400 && err?.status < 500) return;
        if (retryCount >= 3) return;
        revalidate({ retryCount });
      },
    }
  );

  const envKeySet = config?.OPEN_AI_API_KEY_SET ?? false;
  const dbAI = data?.ai_available ?? false;

  return {
    enabled: envKeySet || dbAI,
    isLoading: isLoading && !envKeySet, // If env key is set, we don't need to wait for API
    source: data?.source ?? (envKeySet ? "environment" : "none"),
    error,
  };
}
