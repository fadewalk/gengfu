import { useApi } from "@/shared/lib/hooks/useApi";
import { IncidentData } from "./models";
import { useEffect, useState } from "react";

interface UseReportDataOptions {
  filterCel?: string;
  incidentIds?: string[];
}

export const useReportData = (options: UseReportDataOptions = {}) => {
  const { filterCel, incidentIds } = options;
  const api = useApi();
  const [data, setData] = useState<IncidentData | null>();

  useEffect(() => {
    if (api.isReady()) {
      setData(null);
      if (incidentIds && incidentIds.length > 0) {
        // Use POST with incident_ids for selected incidents
        api
          .post(`/incidents/report`, { incident_ids: incidentIds })
          .then((data) => setData(data));
      } else {
        // Use GET with CEL filter
        let requestUrl = `/incidents/report`;
        if (filterCel) {
          requestUrl += `?cel=${filterCel}`;
        }
        api.get(requestUrl).then((data) => setData(data));
      }
    }
  }, [api, api.isReady(), filterCel, incidentIds]);

  return {
    data,
    isLoading: !data,
  };
};
