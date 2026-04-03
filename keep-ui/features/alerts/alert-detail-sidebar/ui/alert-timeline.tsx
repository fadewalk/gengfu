import React from "react";
import { Subtitle, Button, Card, Title } from "@tremor/react";
import { Chrono } from "react-chrono";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { AlertDto, AuditEvent } from "@/entities/alerts/model";
import { getInitials } from "@/components/navbar/UserAvatar";
import { DynamicImageProviderIcon } from "@/components/ui";
import { useI18n } from "@/i18n/hooks/useI18n";

const formatTimestamp = (timestamp: Date | string) => {
  const date = timestamp.toString().endsWith("Z")
    ? new Date(timestamp)
    : new Date(timestamp.toString() + "Z");
  return date.toLocaleString();
};

type AlertTimelineProps = {
  alert: AlertDto | null;
  auditData: AuditEvent[];
  isLoading: boolean;
  onRefresh: () => void;
};

export const AlertTimeline: React.FC<AlertTimelineProps> = ({
  alert,
  auditData,
  isLoading,
  onRefresh,
}) => {
  const { t } = useI18n();
  // Default audit event if no audit data is available
  const defaultAuditEvent = alert
    ? [
        {
          user_id: "system",
          action: t("alerts.timeline.alertTriggered"),
          description: t("alerts.timeline.alertReceivedFromProvider"),
          timestamp: alert.lastReceived,
        },
      ]
    : [];

  // Direct mapping from backend ActionType values to i18n keys
  const actionKeyMap: Record<string, string> = {
    "alert was triggered": "alerts.timeline.actionTypes.triggered",
    "alert acknowledged": "alerts.timeline.actionTypes.acknowledged",
    "alert automatically resolved": "alerts.timeline.actionTypes.autoResolved",
    "alert automatically resolved by api": "alerts.timeline.actionTypes.autoResolvedByApi",
    "alert manually resolved": "alerts.timeline.actionTypes.manualResolved",
    "alert status manually changed": "alerts.timeline.actionTypes.statusManualChanged",
    "alert status changed by api": "alerts.timeline.actionTypes.statusChangedByApi",
    "alert status undone": "alerts.timeline.actionTypes.statusUndone",
    "alert enriched by workflow": "alerts.timeline.actionTypes.enrichedByWorkflow",
    "alert enriched by mapping rule": "alerts.timeline.actionTypes.enrichedByMappingRule",
    "alert enriched by extraction rule": "alerts.timeline.actionTypes.enrichedByExtractionRule",
    "alert was deduplicated": "alerts.timeline.actionTypes.deduplicated",
    "alert was assigned with ticket": "alerts.timeline.actionTypes.ticketAssigned",
    "alert was unassigned from ticket": "alerts.timeline.actionTypes.ticketUnassigned",
    "alert ticket was updated": "alerts.timeline.actionTypes.ticketUpdated",
    "alert enrichments disposed": "alerts.timeline.actionTypes.enrichmentsDisposed",
    "alert deleted": "alerts.timeline.actionTypes.deleted",
    "alert enriched": "alerts.timeline.actionTypes.enriched",
    "alert un-enriched": "alerts.timeline.actionTypes.unenriched",
    "a comment was added to the alert": "alerts.timeline.actionTypes.commentAdded",
    "a comment was removed from the alert": "alerts.timeline.actionTypes.commentRemoved",
    "alert is in maintenance window": "alerts.timeline.actionTypes.maintenance",
    "alert has been removed from maintenance window": "alerts.timeline.actionTypes.maintenanceExpired",
    "alert dismissal expired": "alerts.timeline.actionTypes.dismissalExpired",
    "a comment was added to the incident": "alerts.timeline.actionTypes.incidentComment",
    "incident enriched": "alerts.timeline.actionTypes.incidentEnriched",
    "incident status changed": "alerts.timeline.actionTypes.incidentStatusChanged",
    "incident assigned": "alerts.timeline.actionTypes.incidentAssigned",
  };

  const translateAction = (action: string): string => {
    const lowered = action.toLowerCase();
    const key = actionKeyMap[lowered];
    if (!key) return lowered;
    return t(key);
  };

  const auditContent = auditData?.length ? auditData : defaultAuditEvent;
  const content = auditContent.map((entry, index) => (
    <div
      key={index}
      className="flex items-start space-x-4 ml-6"
      style={{ width: "400px" }}
    >
      {entry.user_id.toLowerCase() === "system" ? (
        <DynamicImageProviderIcon
          src="/icons/keep-icon.png"
          alt="Keep Logo"
          width={40}
          height={40}
          providerType="keep"
          className="rounded-full flex-shrink-0"
        />
      ) : (
        <span className="relative inline-flex items-center justify-center w-10 h-10 overflow-hidden bg-orange-400 rounded-full flex-shrink-0">
          <span className="font-medium text-white text-xs">
            {getInitials(entry.user_id)}
          </span>
        </span>
      )}
      <div className="flex flex-col justify-center flex-grow overflow-hidden">
        <Subtitle className="text-sm text-orange-500 font-semibold whitespace-normal overflow-wrap-break-word">
          {translateAction(entry.action)}
        </Subtitle>
        <Subtitle className="text-xs whitespace-normal overflow-wrap-break-word">
          {entry.description.toLowerCase()}
        </Subtitle>
      </div>
    </div>
  ));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <Title>{t("alerts.timeline.title")}</Title>
        <Button
          icon={ArrowPathIcon}
          color="orange"
          size="xs"
          disabled={isLoading}
          loading={isLoading}
          onClick={onRefresh}
          title={t("alerts.timeline.refresh")}
        />
      </div>
      <Card className="max-h-[500px] overflow-y-auto p-0">
        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <p>{t("alerts.timeline.loading")}</p>
          </div>
        ) : (
          <div className="flex-grow">
            <Chrono
              items={
                auditContent.map((entry) => ({
                  title: formatTimestamp(entry.timestamp),
                })) || []
              }
              hideControls
              disableToolbar
              borderLessCards
              slideShow={false}
              mode="VERTICAL"
              theme={{
                primary: "orange",
                secondary: "rgb(255 247 237)",
                titleColor: "orange",
                titleColorActive: "orange",
              }}
              fontSizes={{
                title: ".75rem",
              }}
              cardWidth={400}
              cardHeight="auto"
              classNames={{
                card: "hidden",
                cardMedia: "hidden",
                cardSubTitle: "hidden",
                cardText: "hidden",
                cardTitle: "hidden",
                title: "mb-3",
                contentDetails: "w-full !m-0",
              }}
            >
              {content}
            </Chrono>
          </div>
        )}
      </Card>
    </div>
  );
};
