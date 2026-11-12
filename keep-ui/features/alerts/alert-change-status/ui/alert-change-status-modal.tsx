import { Button, Title, Subtitle, Switch } from "@tremor/react";
import Modal from "@/components/ui/Modal";
import { useState, useEffect } from "react";
import { AlertDto, Status } from "@/entities/alerts/model";
import { toast } from "react-toastify";
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  PauseIcon,
  CircleStackIcon,
} from "@heroicons/react/24/outline";
import { useAlerts } from "@/entities/alerts/model/useAlerts";
import { useApi } from "@/shared/lib/hooks/useApi";
import { Select, showErrorToast, Tooltip } from "@/shared/ui";

import { useRevalidateMultiple } from "@/shared/lib/state-utils";
import { useI18n } from "@/i18n/hooks/useI18n";
import dynamic from "next/dynamic";
const ReactQuill = dynamic(() => import("react-quill-new"), { ssr: false,
  loading: () => <div className="p-4 text-gray-500 italic">Loading editor...</div>
 });


const statusIcons = {
  [Status.Firing]: <ExclamationCircleIcon className="w-5 h-5 text-red-500 mr-2" />,
  [Status.Resolved]: <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2" />,
  [Status.Acknowledged]: <PauseIcon className="w-5 h-5 text-gray-500 mr-2" />,
  [Status.Suppressed]: <CircleStackIcon className="w-5 h-5 text-gray-500 mr-2" />,
  [Status.Pending]: <CircleStackIcon className="w-5 h-5 text-gray-500 mr-2" />,
};

interface Props {
  alert: AlertDto | AlertDto[] | null | undefined;
  handleClose: () => void;
  presetName: string;
}

export function AlertChangeStatusModal({
  alert,
  handleClose,
  presetName,
}: Props) {
  const api = useApi();
  const { t } = useI18n();
  const [disposeOnNewAlert, setDisposeOnNewAlert] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState<Status | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const revalidateMultiple = useRevalidateMultiple();
  const { alertsMutator } = useAlerts();
  const presetsMutator = () => revalidateMultiple(["/preset"]);
  const [noteContent, setNoteContent] = useState<string>("");

  if (!alert) return null;

  const statusOptions = Object.values(Status)
    .filter((status) => {
      if (!Array.isArray(alert)) {
        return status !== alert.status; // Exclude current status for single alert
      }
      return true; // For batch, show all statuses
    })
    .map((status) => ({
      value: status,
      label: (
        <div className="flex items-center">
          {statusIcons[status]}
          <span>{status.charAt(0).toUpperCase() + status.slice(1)}</span>
        </div>
      ),
    }));

  const clearAndClose = () => {
    setSelectedStatus(null);
    setNoteContent("");
    setDisposeOnNewAlert(true);
    handleClose();
  };

  const handleChangeStatus = async () => {
    if (!selectedStatus) {
      showErrorToast(new Error(t("alerts.changeStatus.selectStatusError")));
      return;
    }
    if (Array.isArray(alert)) {
      showErrorToast(new Error(t("alerts.changeStatus.batchHandlerError")));
      return;
    }
    setIsSubmitting(true);
    try {
      await api.post(
        `/alerts/enrich?dispose_on_new_alert=${disposeOnNewAlert}`,
        {
          enrichments: {
            status: selectedStatus,
            ...(selectedStatus !== Status.Suppressed && {
              dismissed: false,
              dismissUntil: "",
            }),
            ...(noteContent && noteContent.trim() !== "" && {
              note: noteContent,
            }),
          },
          fingerprint: alert.fingerprint,
        }
      );

      toast.success(t("alerts.changeStatus.successSingle"));
      clearAndClose();
      await alertsMutator();
      await presetsMutator();
    } catch (error) {
      showErrorToast(error, t("alerts.changeStatus.failedSingle"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChangeStatusBatch = async () => {
    if (!selectedStatus) {
      showErrorToast(new Error(t("alerts.changeStatus.selectStatusError")));
      return;
    }
    let fingerprints = new Set<string>();
    if (Array.isArray(alert)) {
      alert.forEach((a) => fingerprints.add(a.fingerprint));
    }
    setIsSubmitting(true);
    try {
      await api.post(
        `/alerts/batch_enrich?dispose_on_new_alert=${disposeOnNewAlert}`,
        {
          enrichments: {
            status: selectedStatus,
            ...(selectedStatus !== Status.Suppressed && {
              dismissed: false,
              dismissUntil: "",
            }),
            ...(noteContent && noteContent.trim() !== "" && {
              note: noteContent,
            }),
          },
          fingerprints: Array.from(fingerprints),
        }
      );

      toast.success(t("alerts.changeStatus.successMultiple"));
      clearAndClose();
      await alertsMutator();
      await presetsMutator();
    } catch (error) {
      showErrorToast(error, t("alerts.changeStatus.failedMultiple"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!Array.isArray(alert)) {
    return (
      <Modal onClose={handleClose} isOpen={!!alert} className="!max-w-none !w-auto inline-block whitespace-nowrap overflow-visible">
        <Title className="text-lg font-semibold">{t("alerts.changeStatus.title")}</Title>
        <div className="border-t border-gray-200 my-4" />
        <div className="flex mt-2.5 inline-flex items-center">
          <Subtitle
            className="flex items-center bold"
          >
            {t("alerts.changeStatus.newStatus")}
          </Subtitle>
          <Select
            options={statusOptions}
            value={statusOptions.find(
              (option) => option.value === selectedStatus
            )}
            onChange={(option) => setSelectedStatus(option?.value || null)}
            placeholder={t("alerts.changeStatus.selectNewStatus")}
            className="ml-2"
            styles={{
              control: (base) => ({
                ...base,
                width: "max-content",
                minWidth: "180px",
              }),
            }}
          />
          <Button
            variant={disposeOnNewAlert ? "primary" : "secondary"}
            className="ml-4"
            size="xs"
            onClick={() => setDisposeOnNewAlert(!disposeOnNewAlert)}
            tooltip={disposeOnNewAlert ? t("alerts.changeStatus.disposeTooltip") : t("alerts.changeStatus.keepTooltip")}
          >
            {disposeOnNewAlert ? t("alerts.changeStatus.disposeOnNewAlerts") : t("alerts.changeStatus.keepOnNewAlerts")}
          </Button>
        </div>
        <div className="mt-4">
          <Subtitle >{t("alerts.actions.addNote")}</Subtitle>
          <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
            <ReactQuill
              value={noteContent}
              onChange={(value: string) => setNoteContent(value)}
              theme="snow"
              placeholder={t("alerts.changeStatus.addNotePlaceholder")}
            />
          </div>
        </div>
        <div className="flex justify-end mt-4 gap-2">
          <Button
            onClick={handleClose}
            color="orange"
            variant="secondary"
            disabled={isSubmitting}
          >
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleChangeStatus}
            color="orange"
            loading={isSubmitting}
            disabled={isSubmitting}
          >
            {t("alerts.actions.changeStatus")}
          </Button>
        </div>
      </Modal>
    );
  } else {
    return (
      <Modal onClose={handleClose} isOpen={!!alert} className="!max-w-none !w-auto inline-block whitespace-nowrap overflow-visible">
        <Title className="text-lg font-semibold">{t("alerts.changeStatus.batchTitle", { count: Array.isArray(alert) ? alert.length : 1 })}</Title>
        <div className="border-t border-gray-200 my-4" />
        <div className="flex mt-2.5 inline-flex items-center">
          <Subtitle
            className="flex items-center bold"
          >
            {t("alerts.changeStatus.newStatus")}
          </Subtitle>
          <Select
            options={statusOptions}
            value={statusOptions.find(
              (option) => option.value === selectedStatus
            )}
            onChange={(option) => setSelectedStatus(option?.value || null)}
            placeholder={t("alerts.changeStatus.selectNewStatus")}
            className="ml-2"
            styles={{
              control: (base) => ({
                ...base,
                width: "max-content",
                minWidth: "180px",
              }),
            }}
          />
          <Button
            variant={disposeOnNewAlert ? "primary" : "secondary"}
            className="ml-4"
            size="xs"
            onClick={() => setDisposeOnNewAlert(!disposeOnNewAlert)}
            tooltip={disposeOnNewAlert ? t("alerts.changeStatus.disposeTooltip") : t("alerts.changeStatus.keepTooltip")}
          >
            {disposeOnNewAlert ? t("alerts.changeStatus.disposeOnNewAlerts") : t("alerts.changeStatus.keepOnNewAlerts")}
          </Button>
        </div>
        <div className="mt-4">
          <Subtitle >{t("alerts.actions.addNote")}</Subtitle>
          <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
            <ReactQuill
              value={noteContent}
              onChange={(value: string) => setNoteContent(value)}
              theme="snow"
              placeholder={t("alerts.changeStatus.addNotePlaceholder")}
            />
          </div>
        </div>
        <div className="flex justify-end mt-4 gap-2">
          <Button
            onClick={handleClose}
            color="blue"
            variant="secondary"
            disabled={isSubmitting}
          >
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleChangeStatusBatch}
            color="blue"
            loading={isSubmitting}
            disabled={isSubmitting}
          >
            {t("alerts.actions.changeStatus")}
          </Button>
        </div>
      </Modal>
    )

  }
}
