import { useApi } from "@/shared/lib/hooks/useApi";
import { IncidentData, ReportTemplateType } from "./models";
import { useEffect, useState } from "react";

interface UseReportDataOptions {
  filterCel?: string;
  incidentIds?: string[];
  templateType?: ReportTemplateType;
}

export const useReportData = (options: UseReportDataOptions = {}) => {
  const { filterCel, incidentIds, templateType = "comprehensive" } = options;
  const api = useApi();
  const [data, setData] = useState<IncidentData | null>();

  useEffect(() => {
    if (api.isReady()) {
      setData(null);
      if (incidentIds && incidentIds.length > 0) {
        // Use POST with incident_ids and template_type
        api
          .post(`/incidents/report`, {
            incident_ids: incidentIds,
            template_type: templateType,
          })
          .then((data) => setData(data));
      } else {
        // Use GET with CEL filter (sync endpoint doesn't take template_type in query)
        let requestUrl = `/incidents/report`;
        if (filterCel) {
          requestUrl += `?cel=${filterCel}`;
        }
        api.get(requestUrl).then((data) => setData(data));
      }
    }
  }, [api, api.isReady(), filterCel, incidentIds, templateType]);

  return {
    data,
    isLoading: !data,
  };
};
