import { SWRConfiguration } from "swr";
import { ProvidersResponse } from "@/shared/api/providers";
import useSWRImmutable from "swr/immutable";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useProviders = (
  options: SWRConfiguration = { revalidateOnFocus: false },
  queryParams?: Record<string, string>
) => {
  const api = useApi();

  const searchParams = queryParams
    ? new URLSearchParams(queryParams).toString()
    : "";
  const url = api.isReady() ? `/providers${searchParams ? `?${searchParams}` : ""}` : null;

  return useSWRImmutable<ProvidersResponse>(
    url,
    (url) => api.get(url),
    options
  );
};
