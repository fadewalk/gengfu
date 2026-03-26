import { SWRConfiguration } from "swr";
import useSWRImmutable from "swr/immutable";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useTenantConfiguration = (options: SWRConfiguration = {}) => {
  const api = useApi();

  return useSWRImmutable<{ [key: string]: string }>(
    api.isReady() ? `/settings/tenant/configuration` : null,
    async (url) => {
      // Use raw fetch to avoid triggering signout on 401.
      // This endpoint requires read:settings permission; if the user lacks it,
      // we gracefully return an empty config rather than logging them out.
      try {
        const baseUrl = api.getApiBaseUrl();
        const headers = api.getHeaders();
        const response = await fetch(baseUrl + url, {
          headers: headers as Record<string, string>,
        });
        if (!response.ok) return {};
        const contentType = response.headers.get("content-type");
        if (contentType?.includes("application/json")) {
          return await response.json();
        }
        return {};
      } catch {
        return {};
      }
    },
    options
  );
};
