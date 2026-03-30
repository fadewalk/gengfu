"use client";
import { useI18n } from "@/i18n/hooks/useI18n";

import { Card, Title, Badge, Button } from "@tremor/react";
import { useAIStats, useAIActions, CorrelationResult } from "utils/hooks/useAI";
import { useEffect, useMemo, useRef, useState } from "react";
import debounce from "lodash.debounce";
import {
  KeepLoader,
  PageSubtitle,
  showErrorToast,
  showSuccessToast,
} from "@/shared/ui";
import { PageTitle } from "@/shared/ui";
import { AIConfig } from "./model";
import {
  IoSparklesOutline,
  IoPlayOutline,
  IoCheckmarkCircleOutline,
  IoAlertCircleOutline,
  IoTrendingUpOutline,
  IoPulseOutline,
} from "react-icons/io5";

// Backend strings → i18n key mapping
function useBackendTranslations(t: (key: string) => string) {
  const algorithmNameMap: Record<string, string> = {
    "LLM Alert Correlation": t("aiPlugins.llmAlertCorrelation"),
  };
  const algorithmDescMap: Record<string, string> = {
    "LLM Alert Correlation": t("aiPlugins.llmCorrelationDesc"),
  };
  const settingNameMap: Record<string, string> = {
    "Enabled": t("aiPlugins.settingEnabled"),
    "Max Alerts Per Batch": t("aiPlugins.settingMaxAlertsPerBatch"),
    "Confidence Threshold": t("aiPlugins.settingConfidenceThreshold"),
    "Auto Create Incidents": t("aiPlugins.settingAutoCreateIncidents"),
    "Include Topology Context": t("aiPlugins.settingIncludeTopologyContext"),
  };
  const settingDescMap: Record<string, string> = {
    "Enable or disable the LLM correlation engine.": t("aiPlugins.settingEnabledDesc"),
    "Maximum number of unassigned alerts to process in a single correlation run.": t("aiPlugins.settingMaxAlertsPerBatchDesc"),
    "Minimum confidence score for AI-suggested incidents. Suggestions below this threshold are discarded.": t("aiPlugins.settingConfidenceThresholdDesc"),
    "Automatically create incidents from high-confidence correlations. When disabled, suggestions are stored for manual review.": t("aiPlugins.settingAutoCreateIncidentsDesc"),
    "Include service topology data when analyzing alerts for better correlation accuracy.": t("aiPlugins.settingIncludeTopologyContextDesc"),
  };

  return {
    translateAlgorithmName: (name: string) => algorithmNameMap[name] ?? name,
    translateAlgorithmDesc: (name: string, desc: string) => algorithmDescMap[name] ?? desc,
    translateSettingName: (name: string) => settingNameMap[name] ?? name,
    translateSettingDesc: (desc: string) => settingDescMap[desc] ?? desc,
  };
}

function RangeInputWithLabel({
  setting,
  onDebouncedChange,
  t,
}: {
  setting: any;
  onDebouncedChange: (newValue: number) => void;
  t: (key: string) => string;
}) {
  const [value, setValue] = useState(setting.value);
  // Use ref so the debounced function is created once
  const onChangeRef = useRef(onDebouncedChange);
  onChangeRef.current = onDebouncedChange;

  const debouncedOnChange = useMemo(
    () => debounce((v: number) => onChangeRef.current(v), 1000),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  useEffect(() => {
    return () => {
      debouncedOnChange.cancel();
    };
  }, [debouncedOnChange]);

  return (
    <div className="flex flex-col gap-1 items-end">
      <p className="text-right text-sm text-gray-500">
        {t("aiPlugins.value")}: {typeof value === "number" ? value.toFixed(setting.type === "float" ? 2 : 0) : value}
      </p>
      <input
        type="range"
        title={`${setting.name}: ${value}`}
        className="bg-orange-500 accent-orange-500 [&::-webkit-slider-runnable-track]:bg-gray-100 [&::-webkit-slider-runnable-track]:rounded-full"
        step={(setting.max - setting.min) / 100}
        min={setting.min}
        max={setting.max}
        value={value}
        onChange={(e) => {
          const newValue =
            setting.type === "float"
              ? parseFloat(e.target.value)
              : parseInt(e.target.value, 10);
          setValue(newValue);
          debouncedOnChange(newValue);
        }}
      />
    </div>
  );
}

export function AIPlugins() {
  const { t } = useI18n();
  const { translateAlgorithmName, translateAlgorithmDesc, translateSettingName, translateSettingDesc } = useBackendTranslations(t);
  const {
    data: aistats,
    isLoading,
    mutate: refetchAIStats,
  } = useAIStats({
    refreshInterval: 5000,
  });
  const { updateAISettings, triggerCorrelation } = useAIActions();
  const [isCorrelating, setIsCorrelating] = useState(false);
  const [correlationResult, setCorrelationResult] =
    useState<CorrelationResult | null>(null);

  const handleUpdateAISettings = async (
    algorithm_id: string,
    algorithm_config: AIConfig
  ) => {
    try {
      await updateAISettings(algorithm_id, algorithm_config);
      showSuccessToast(t("common.messages.savedSuccessfully"));
      refetchAIStats();
    } catch (error) {
      showErrorToast(error);
    }
  };

  const handleTriggerCorrelation = async () => {
    setIsCorrelating(true);
    setCorrelationResult(null);
    try {
      const result = await triggerCorrelation();
      setCorrelationResult(result);
      if (result.status === "success") {
        showSuccessToast(
          t("aiPlugins.incidentsCreatedFromAlerts", { incidents: result.incidents_created, alerts: result.alerts_analyzed })
        );
      }
      refetchAIStats();
    } catch (error: any) {
      showErrorToast(error?.message || t("aiPlugins.correlationFailed"));
    } finally {
      setIsCorrelating(false);
    }
  };

  // Find internal LLM config
  const llmConfig = aistats?.algorithm_configs?.find(
    (cfg: any) => cfg.algorithm_id?.includes("LLM")
  );

  // Extract execution history from feedback_logs
  const executionLogs = llmConfig?.feedback_logs
    ? llmConfig.feedback_logs
        .split("\n")
        .filter((line: string) => line.trim())
        .slice(-10)
    : [];

  return (
    <main className="flex flex-col gap-6">
      <header className="flex justify-between items-center">
        <div>
          <PageTitle>
            <IoSparklesOutline className="inline h-7 w-7 mr-2 text-orange-500" />
            {t("aiPlugins.title")}
          </PageTitle>
          <PageSubtitle>{t("aiPlugins.subtitle")}</PageSubtitle>
        </div>
        <Button
          color="orange"
          size="lg"
          icon={IoPlayOutline}
          onClick={handleTriggerCorrelation}
          disabled={isCorrelating}
          className="shrink-0"
        >
          {isCorrelating ? t("aiPlugins.triggering") : t("aiPlugins.triggerCorrelation")}
        </Button>
      </header>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-blue-500">
            <IoAlertCircleOutline className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{aistats?.alerts_count ?? 0}</p>
            <p className="text-sm text-gray-500">{t("aiPlugins.totalAlerts")}</p>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-orange-500">
            <IoPulseOutline className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{aistats?.incidents_count ?? 0}</p>
            <p className="text-sm text-gray-500">{t("aiPlugins.totalIncidents")}</p>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-emerald-500">
            <IoTrendingUpOutline className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">
              {aistats?.first_alert_datetime
                ? new Date(aistats.first_alert_datetime).toLocaleDateString()
                : "—"}
            </p>
            <p className="text-sm text-gray-500">{t("aiPlugins.firstAlertTime")}</p>
          </div>
        </Card>
      </div>

      {/* Correlation Result */}
      {correlationResult && (
        <Card
          className={`p-4 border-l-4 ${
            correlationResult.status === "success"
              ? "border-l-green-500 bg-green-50"
              : "border-l-orange-500 bg-orange-50"
          }`}
        >
          <div className="flex items-start gap-3">
            {correlationResult.status === "success" ? (
              <IoCheckmarkCircleOutline className="h-6 w-6 text-green-600 mt-0.5 shrink-0" />
            ) : (
              <IoAlertCircleOutline className="h-6 w-6 text-orange-600 mt-0.5 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-gray-900">
                {correlationResult.status === "success"
                  ? t("aiPlugins.correlationResult")
                  : t("aiPlugins.correlationFailed")}
              </h4>
              {correlationResult.status === "success" && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                  <div className="text-center">
                    <p className="text-xl font-bold text-gray-800">
                      {correlationResult.alerts_analyzed ?? 0}
                    </p>
                    <p className="text-xs text-gray-500">{t("aiPlugins.alertsAnalyzed")}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-blue-600">
                      {correlationResult.incidents_suggested ?? 0}
                    </p>
                    <p className="text-xs text-gray-500">{t("aiPlugins.incidentsSuggested")}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-orange-600">
                      {correlationResult.incidents_above_threshold ?? correlationResult.incidents_suggested ?? 0}
                    </p>
                    <p className="text-xs text-gray-500">
                      {t("aiPlugins.confidenceThreshold")}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-green-600">
                      {correlationResult.incidents_created ?? 0}
                    </p>
                    <p className="text-xs text-gray-500">{t("aiPlugins.incidentsCreated")}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <KeepLoader loadingText={t("aiPlugins.loading")} />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 p-4">
            {aistats?.algorithm_configs?.map((algorithm_config: any, index: number) => (
              <Card
                key={algorithm_config.algorithm_id ?? index}
                className="p-4 flex flex-col justify-between w-full border-white border-2"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <IoSparklesOutline className="text-orange-500" />
                      {translateAlgorithmName(algorithm_config.algorithm.name)}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {translateAlgorithmDesc(algorithm_config.algorithm.name, algorithm_config.algorithm.description)}
                    </p>
                  </div>
                  {algorithm_config.algorithm_id?.includes("LLM") && (
                    <Badge color="orange" size="xs">
                      {t("aiPlugins.llmCorrelation")}
                    </Badge>
                  )}
                </div>

                {/* Settings */}
                <div className="my-4 p-2 border-y border-gray-200 flex flex-col gap-4">
                  <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    {t("aiPlugins.configuration")}
                  </h4>
                  {algorithm_config.settings.map((setting: any) => (
                    <div
                      key={setting.name}
                      className="flex flex-row items-start gap-2"
                    >
                      {setting.type === "bool" ? (
                        <input
                          type="checkbox"
                          id={`checkbox-${index}-${setting.name}`}
                          name={`checkbox-${index}-${setting.name}`}
                          title={setting.name}
                          checked={setting.value}
                          onChange={(e) => {
                            // Immutable: create new config without mutating SWR cache
                            const updated = {
                              ...algorithm_config,
                              settings: algorithm_config.settings.map((s: any) =>
                                s.name === setting.name
                                  ? { ...s, value: e.target.checked }
                                  : s
                              ),
                            };
                            handleUpdateAISettings(
                              algorithm_config.algorithm_id,
                              updated
                            );
                          }}
                          className="mt-2 bg-orange-500 accent-orange-200"
                        />
                      ) : null}
                      <div className="flex-1">
                        <p className="text-sm font-medium">{translateSettingName(setting.name)}</p>
                        <p className="text-sm text-gray-500">{translateSettingDesc(setting.description)}</p>
                      </div>
                      {setting.type === "float" || setting.type === "int" ? (
                        <div className="flex-1 max-w-xs">
                          <RangeInputWithLabel
                            key={setting.name}
                            setting={setting}
                            t={t}
                            onDebouncedChange={(newValue) => {
                              // Immutable: create new config without mutating SWR cache
                              const updated = {
                                ...algorithm_config,
                                settings: algorithm_config.settings.map((s: any) =>
                                  s.name === setting.name
                                    ? { ...s, value: newValue }
                                    : s
                                ),
                              };
                              handleUpdateAISettings(
                                algorithm_config.algorithm_id,
                                updated
                              );
                            }}
                          />
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>

                {/* Proposed settings */}
                {algorithm_config.settings_proposed_by_algorithm &&
                  JSON.stringify(algorithm_config.settings) !==
                    JSON.stringify(
                      algorithm_config.settings_proposed_by_algorithm
                    ) && (
                    <Card className="m-2 mt-4 p-2">
                      <Title>{t("aiPlugins.newSettingsProposal")}</Title>
                      <p className="text-sm">
                        {t("aiPlugins.proposalDescription")}
                      </p>
                      {algorithm_config.settings_proposed_by_algorithm.map(
                        (proposed_setting: any, idx: number) => (
                          <div key={idx} className="mt-2">
                            <p className="text-sm">
                              {translateSettingName(proposed_setting.name)}:{" "}
                              {String(proposed_setting.value)}
                            </p>
                          </div>
                        )
                      )}
                      <button
                        type="button"
                        className="mt-2 p-2 bg-orange-500 text-white rounded"
                        onClick={() => {
                          // Immutable: replace settings entirely with proposed
                          const updated = {
                            ...algorithm_config,
                            settings: algorithm_config.settings_proposed_by_algorithm.map(
                              (s: any) => ({ ...s })
                            ),
                          };
                          handleUpdateAISettings(
                            algorithm_config.algorithm_id,
                            updated
                          );
                        }}
                      >
                        {t("aiPlugins.applyProposedSettings")}
                      </button>
                    </Card>
                  )}

                {/* Execution History */}
                <div className="mt-4">
                  <h4 className="text-md font-medium flex items-center gap-2">
                    {t("aiPlugins.executionLogs")}
                    {executionLogs.length > 0 && (
                      <Badge color="orange" size="xs">
                        {executionLogs.length}
                      </Badge>
                    )}
                  </h4>
                  <pre className="text-sm bg-gray-100 p-3 rounded mt-2 break-words whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {executionLogs.length > 0
                      ? executionLogs.join("\n")
                      : t("aiPlugins.notExecutedYet")}
                  </pre>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}
