import { Button } from "@tremor/react";
import { useState } from "react";
import { AlertDto } from "@/entities/alerts/model";
import { PlusIcon, RocketIcon } from "@radix-ui/react-icons";
import { toast } from "react-toastify";
import { useRouter, useSearchParams } from "next/navigation";
import { SilencedDoorbellNotification } from "@/components/icons";
import { AlertAssociateIncidentModal } from "@/features/alerts/alert-associate-to-incident";
import { CreateIncidentWithAIModal } from "@/features/alerts/alert-create-incident-ai";
import { useApi } from "@/shared/lib/hooks/useApi";
import { Table } from "@tanstack/react-table";

import { useRevalidateMultiple } from "@/shared/lib/state-utils";
import { useAIEnabled } from "@/utils/hooks/useAIEnabled";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { ChevronDoubleRightIcon } from "@heroicons/react/24/solid";
import { AlertChangeStatusModal } from "@/features/alerts/alert-change-status/ui/alert-change-status-modal";
import { useTranslations } from "next-intl";

interface Props {
  selectedAlertsFingerprints: string[];
  table: Table<AlertDto>;
  clearRowSelection: () => void;
  setDismissModalAlert?: (alert: AlertDto[] | null) => void;
  mutateAlerts?: () => void;
  setIsIncidentSelectorOpen: (open: boolean) => void;
  isIncidentSelectorOpen: boolean;
  setIsCreateIncidentWithAIOpen: (open: boolean) => void;
  isCreateIncidentWithAIOpen: boolean;
}

export default function AlertActions({
  selectedAlertsFingerprints,
  table,
  clearRowSelection,
  setDismissModalAlert,
  mutateAlerts,
  setIsIncidentSelectorOpen,
  isIncidentSelectorOpen,
  setIsCreateIncidentWithAIOpen,
  isCreateIncidentWithAIOpen,
}: Props) {
  const t = useTranslations("alerts.actions");
  const router = useRouter();
  const api = useApi();
  const { enabled: isAIEnabled } = useAIEnabled();
  const revalidateMultiple = useRevalidateMultiple();
  const presetsMutator = () => revalidateMultiple(["/preset"]);
  const [modalAlert, setModalAlert] = useState<AlertDto | AlertDto[] | null>(null);

  // TODO: refactor
  const searchParams = useSearchParams();
  const createIncidentsFromLastAlerts = searchParams.get(
    "createIncidentsFromLastAlerts"
  );

  const selectedAlerts = table
    .getSelectedRowModel()
    .rows.map((row) => row.original);

  async function addOrUpdatePreset() {
    const newPresetName = prompt(t("enterPresetName"));
    if (newPresetName) {
      const distinctAlertNames = Array.from(
        new Set(selectedAlerts.map((alert) => alert.name))
      );
      const formattedCel = distinctAlertNames.reduce(
        (accumulator, currentValue, currentIndex) => {
          return (
            accumulator +
            (currentIndex > 0 ? " || " : "") +
            `name == "${currentValue}"`
          );
        },
        ""
      );
      const options = [{ value: formattedCel, label: "CEL" }];
      try {
        const response = await api.post(`/preset`, {
          name: newPresetName,
          options: options,
        });
        toast(t("presetCreated", { name: newPresetName }), {
          position: "top-left",
          type: "success",
        });
        presetsMutator();
        clearRowSelection();
        router.replace(`/alerts/${newPresetName}`);
      } catch (error) {
        toast(t("errorCreatingPreset", { name: newPresetName }), {
          position: "top-left",
          type: "error",
        });
      }
    }
  }

  const showIncidentSelector = () => {
    setIsIncidentSelectorOpen(true);
  };
  const hideIncidentSelector = () => {
    setIsIncidentSelectorOpen(false);
  };

  const showCreateIncidentWithAI = () => {
    setIsCreateIncidentWithAIOpen(true);
  };
  const hideCreateIncidentWithAI = () => {
    setIsCreateIncidentWithAIOpen(false);
  };

  const handleSuccessfulAlertsAssociation = () => {
    hideIncidentSelector();
    clearRowSelection();
    if (mutateAlerts) {
      mutateAlerts();
    }
  };

  return (
    <div className="w-full flex gap-2.5 justify-end items-center">
      <Button
        icon={XMarkIcon}
        size="xs"
        color="slate"
        title={t("clearSelection")}
        onClick={clearRowSelection}
      >
        {t("clearSelection")}
      </Button>
      <Button
        icon={ChevronDoubleRightIcon}
        size="xs"
        color="blue"
        title={t("resolveAlert")}
        onClick={() => {
          setModalAlert(selectedAlerts);
        }}
      >
        {t("changeStatusOf", { count: selectedAlertsFingerprints.length })}
      </Button>
      {modalAlert && (
        <AlertChangeStatusModal
          alert={modalAlert}
          presetName="resolve"
          handleClose={() => {
            setModalAlert(null);
            clearRowSelection();
          }}
        />
      )}
      <Button
        icon={SilencedDoorbellNotification}
        size="xs"
        color="red"
        title={t("deleteAlert")}
        onClick={() => {
          setDismissModalAlert?.(selectedAlerts);
          clearRowSelection();
        }}
      >
        {t("dismissAlerts", { count: selectedAlertsFingerprints.length })}
      </Button>
      <Button
        icon={PlusIcon}
        size="xs"
        color="orange"
        onClick={async () => await addOrUpdatePreset()}
        tooltip={t("createPresetTooltip")}
      >
        {t("createPreset")}
      </Button>
      <Button
        icon={PlusIcon}
        size="xs"
        color="orange"
        onClick={showIncidentSelector}
        tooltip={t("associateWithIncidentTooltip")}
      >
        {t("associateWithIncident")}
      </Button>
      <Button
        icon={RocketIcon}
        size="xs"
        color="orange"
        onClick={showCreateIncidentWithAI}
        tooltip={
          isAIEnabled
            ? t("createIncidentsWithAITooltip")
            : t("aiNotConfigured")
        }
        disabled={!isAIEnabled}
      >
        {t("createIncidentsWithAI")}
      </Button>
      <AlertAssociateIncidentModal
        isOpen={isIncidentSelectorOpen}
        alerts={selectedAlerts}
        handleSuccess={handleSuccessfulAlertsAssociation}
        handleClose={hideIncidentSelector}
      />
      <CreateIncidentWithAIModal
        isOpen={isCreateIncidentWithAIOpen}
        alerts={selectedAlerts}
        handleClose={hideCreateIncidentWithAI}
      />
    </div>
  );
}
