"use client";

import { useState, useCallback } from "react";
import {
  Card,
  TextInput,
  Textarea,
  Button,
  Badge,
  Switch,
} from "@tremor/react";
import {
  TrashIcon,
  PlusIcon,
  PencilIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  SignalIcon,
  CpuChipIcon,
  BeakerIcon,
  ChatBubbleLeftRightIcon,
  LightBulbIcon,
  StarIcon,
} from "@heroicons/react/24/outline";
import Modal from "@/components/ui/Modal";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useI18n } from "@/i18n/hooks/useI18n";
import { showErrorToast, showSuccessToast } from "@/shared/ui";
import useSWR from "swr";
import { PageTitle } from "@/shared/ui/PageTitle";
import { PageSubtitle } from "@/shared/ui/PageSubtitle";
import Loading from "@/app/(keep)/loading";

import { KeepApiError } from "@/shared/api";

// ── Types ────────────────────────────────────────────────────────
interface AIModelConfig {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model_name: string;
  fallback_models: string[];
  is_default: boolean;
  priority: number;
  enabled: boolean;
  extra_config: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  api_key_hint: string;
}

interface AIModelConfigCreate {
  name: string;
  provider: string;
  base_url: string;
  api_key: string;
  model_name: string;
  fallback_models: string[];
  is_default: boolean;
  priority: number;
  enabled: boolean;
  extra_config: Record<string, unknown> | null;
}

// ── Presets ────────────────────────────────────────────────────────
const PRESET_MODELS = [
  { provider: "zhipu", name: "ZhiPu GLM", base_url: "https://open.bigmodel.cn/api/paas/v4", models: ["glm-5.3-flash", "glm-4.6", "glm-4-flash"], icon: CpuChipIcon },
  { provider: "deepseek", name: "DeepSeek", base_url: "https://api.deepseek.com/v1", models: ["deepseek-chat", "deepseek-reasoner"], icon: BeakerIcon },
  { provider: "qwen", name: "Tongyi Qwen", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", models: ["qwen3-max", "qwen-plus"], icon: SignalIcon },
  { provider: "moonshot", name: "Kimi", base_url: "https://api.moonshot.cn/v1", models: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"], icon: ChatBubbleLeftRightIcon },
  { provider: "minimax", name: "MiniMax", base_url: "https://api.minimax.chat/v1", models: ["MiniMax-Text-01"], icon: LightBulbIcon },
  { provider: "openai", name: "OpenAI", base_url: "https://api.openai.com/v1", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], icon: StarIcon },
];
const CUSTOM_PRESET = { provider: "custom", name: "Custom", base_url: "", models: [] as string[], icon: ArrowPathIcon };

// ── Form state ────────────────────────────────────────────────────────
interface ModelFormData {
  name: string;
  provider: string;
  base_url: string;
  api_key: string;
  model_name: string;
  fallback_models: string;
  is_default: boolean;
  enabled: boolean;
  extra_config: string;
}
type TestResult = { state: "idle" | "testing" | "success" | "failed"; message?: string };

const EMPTY_FORM: ModelFormData = {
  name: "",
  provider: "openai_compatible",
  base_url: "",
  api_key: "",
  model_name: "",
  fallback_models: "",
  is_default: false,
  enabled: true,
  extra_config: "",
};

// ── Preset Card ────────────────────────────────────────────────────────
function PresetCard({
  preset,
  isSelected,
  onClick,
}: {
  preset: typeof PRESET_MODELS[number] | typeof CUSTOM_PRESET;
  isSelected: boolean;
  onClick: () => void;
}) {
  const Icon = preset.icon || ArrowPathIcon;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
        isSelected
          ? "border-orange-400 bg-orange-50 text-orange-700"
          : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50"
      }`}
    >
      <Icon className="w-4 h-4" />
      <span>{preset.name}</span>
    </button>
  );
}

// ── Model Form Modal ─────────────────────────────────────────────────
function ModelFormModal({
  isOpen,
  onClose,
  editingModel,
  formData,
  onFieldChange,
  onSave,
  saving,
  onTestConnection,
  testResult,
}: {
  isOpen: boolean;
  onClose: () => void;
  editingModel: AIModelConfig | null;
  formData: ModelFormData;
  onFieldChange: (field: string, value: string | boolean) => void;
  onSave: () => void;
  saving: boolean;
  onTestConnection: () => void;
  testResult: TestResult | null;
}) {
  const { t } = useI18n();
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const isEditing = editingModel !== null;

  const isValid =
    !!formData.name &&
    !!formData.base_url &&
    !!formData.api_key &&
    !!formData.model_name;

  const applyPreset = (preset: typeof PRESET_MODELS[number] | typeof CUSTOM_PRESET) => {
    setSelectedPreset(preset.provider);
    onFieldChange("base_url", preset.base_url || formData.base_url);
    onFieldChange("model_name", preset.models[0] || formData.model_name);
  };
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? t("aiSettings.form.editTitle") : t("aiSettings.form.addTitle")}
    >
      <div className="flex flex-col gap-4 py-2 max-h-[70vh] overflow-y-auto">
        {!isEditing && (
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">
              {t("aiSettings.presets.custom")}
            </label>
            <div className="flex flex-wrap gap-2">
              {[...PRESET_MODELS, CUSTOM_PRESET].map((p) => (
                <PresetCard
                  key={p.provider}
                  preset={p}
                  isSelected={selectedPreset === p.provider}
                  onClick={() => applyPreset(p)}
                />
              ))}
            </div>
          </div>
        )}
        <FieldGroup label={t("aiSettings.form.name")} required>
          <TextInput
            value={formData.name}
            onValueChange={(v) => onFieldChange("name", v)}
            placeholder={t("aiSettings.form.namePlaceholder")}
          />
        </FieldGroup>
        <FieldGroup label={t("aiSettings.form.baseUrlLabel")} required>
          <TextInput
            value={formData.base_url}
            onValueChange={(v) => onFieldChange("base_url", v)}
            placeholder={t("aiSettings.form.baseUrlPlaceholder")}
          />
        </FieldGroup>
        <div>
          <label className="text-sm font-medium text-gray-700">
            {t("aiSettings.form.apiKeyLabel")} <span className="text-red-500">*</span>
          </label>
          <TextInput
            value={formData.api_key}
            onValueChange={(v) => onFieldChange("api_key", v)}
            placeholder={t("aiSettings.form.apiKeyPlaceholder")}
            type="password"
          />
          {isEditing && editingModel?.api_key_hint && (
            <p className="text-xs text-gray-500 mt-1">
              Current: {editingModel.api_key_hint}
            </p>
          )}
        </div>
        <FieldGroup label={t("aiSettings.form.modelNameLabel")} required>
          <TextInput
            value={formData.model_name}
            onValueChange={(v) => onFieldChange("model_name", v)}
            placeholder={t("aiSettings.form.modelNamePlaceholder")}
          />
        </FieldGroup>
        <div>
          <label className="text-sm font-medium text-gray-700">
            {t("aiSettings.form.fallbackModelsLabel")}
          </label>
          <TextInput
            value={formData.fallback_models}
            onValueChange={(v) => onFieldChange("fallback_models", v)}
            placeholder={t("aiSettings.form.fallbackModelsPlaceholder")}
          />
          <p className="text-xs text-gray-400 mt-1">
            {t("aiSettings.form.fallbackModelsHint")}
          </p>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">
            {t("aiSettings.form.extraConfigLabel")}
          </label>
          <Textarea
            value={formData.extra_config}
            onValueChange={(v) => onFieldChange("extra_config", v)}
            placeholder={t("aiSettings.form.extraConfigPlaceholder")}
            rows={3}
          />
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Switch
              checked={formData.is_default}
              onChange={(v) => onFieldChange("is_default", v)}
            />
            <label className="text-sm text-gray-700">{t("aiSettings.form.isDefault")}</label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={formData.enabled}
              onChange={(v) => onFieldChange("enabled", v)}
            />
            <label className="text-sm text-gray-700">{t("aiSettings.form.enabled")}</label>
          </div>
        </div>
        {testResult && testResult.state !== "idle" && (
          <div
            className={`p-2 rounded text-sm flex items-center gap-1 ${
              testResult.state === "success"
                ? "bg-green-50 text-green-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {testResult.state === "success" ? (
              <CheckCircleIcon className="w-4 h-4" />
            ) : (
              <ExclamationCircleIcon className="w-4 h-4" />
            )}
            <span>{testResult.message}</span>
          </div>
        )}
        <div className="flex justify-between items-center gap-2 mt-4 pt-2 border-t">
          <Button size="xs" variant="secondary" onClick={onClose}>
            {t("common.actions.cancel")}
          </Button>
          <div className="flex gap-2">
            <Button
              size="xs"
              variant="light"
              color="orange"
              onClick={onTestConnection}
              disabled={saving}
            >
              {testResult?.state === "testing"
                ? t("aiSettings.form.testing")
                : t("aiSettings.form.testConnection")}
            </Button>
            <Button
              size="xs"
              color="orange"
              onClick={onSave}
              loading={saving}
              disabled={!isValid || saving}
            >
              {t("common.actions.save")}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

function FieldGroup({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="mt-1">{children}</div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────
export default function AISettings() {
  const api = useApi();
  const { t } = useI18n();

  // ── Data fetching ────────────────────────────────────────────────
  const { data: modelsData, mutate: mutateModels } = useSWR(
    api.isReady() ? "/ai/models" : null,
    (url: string) => api.get(url),
    { revalidateOnFocus: false }
  );

  const models: AIModelConfig[] = (modelsData as AIModelConfig[] | undefined) ?? [];

  // ── Local state ─────────────────────────────────────────────────
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<AIModelConfig | null>(null);
  const [formData, setFormData] = useState<ModelFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, TestResult | null>>({});
  const [modalTestResult, setModalTestResult] = useState<TestResult | null>(null);

  // ── Form handlers ────────────────────────────────────────────────
  const handleFieldChange = useCallback(
    (field: string, value: string | boolean) =>
      setFormData((prev) => ({ ...prev, [field]: value })),
    []
  );

  const openAddModal = useCallback(() => {
    setEditingModel(null);
    setFormData(EMPTY_FORM);
    setModalTestResult(null);
    setIsModalOpen(true);
  }, []);

  const openEditModal = useCallback((model: AIModelConfig) => {
    setEditingModel(model);
    setFormData({
      name: model.name,
      provider: model.provider,
      base_url: model.base_url,
      api_key: "",
      model_name: model.model_name,
      fallback_models: model.fallback_models?.join(", ") ?? "",
      is_default: model.is_default,
      enabled: model.enabled,
      extra_config: model.extra_config
        ? JSON.stringify(model.extra_config, null, 2)
        : "",
    });
    setModalTestResult(null);
    setIsModalOpen(true);
  }, []);

  // ── CRUD handlers ────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    setSaving(true);
    let extraConfig: Record<string, unknown> | null = null;
    try {
      if (formData.extra_config.trim()) {
        extraConfig = JSON.parse(formData.extra_config);
      }
    } catch {
      showErrorToast(new Error(t("aiSettings.form.validation.invalidJson")));
      setSaving(false);
      return;
    }
    const payload: AIModelConfigCreate = {
      name: formData.name,
      provider: formData.provider,
      base_url: formData.base_url,
      api_key: formData.api_key,
      model_name: formData.model_name,
      fallback_models: formData.fallback_models
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      is_default: formData.is_default,
      enabled: formData.enabled,
      priority: editingModel?.priority ?? 0,
      extra_config: extraConfig,
    };
    try {
      if (editingModel) {
        await api.put(`/ai/models/${editingModel.id}`, payload);
        showSuccessToast(t("aiSettings.messages.updateSuccess"));
      } else {
        await api.post("/ai/models", payload);
        showSuccessToast(t("aiSettings.messages.addSuccess"));
      }
      mutateModels();
      setIsModalOpen(false);
      setEditingModel(null);
      setFormData(EMPTY_FORM);
    } catch (error) {
      showErrorToast(error);
    } finally {
      setSaving(false);
    }
  }, [formData, editingModel, api, mutateModels, t]);

  const handleDelete = useCallback(
    async (model: AIModelConfig) => {
      if (!confirm(t("aiSettings.form.deleteConfirm", { name: model.name }))) return;
      try {
        await api.delete(`/ai/models/${model.id}`);
        mutateModels();
        showSuccessToast(t("aiSettings.messages.deleteSuccess"));
      } catch (error) {
        showErrorToast(error);
      }
    },
    [api, mutateModels, t]
  );

  const handleTestConnection = useCallback(
    async (model: AIModelConfig) => {
      const key = model.id;
      setTestResults((prev) => ({ ...prev, [key]: { state: "testing" } }));
      try {
        await api.post(`/ai/models/${model.id}/test`);
        setTestResults((prev) => ({
          ...prev,
          [key]: { state: "success", message: t("aiSettings.form.testSuccess") },
        }));
        mutateModels();
      } catch (error) {
        const msg =
          error instanceof KeepApiError
            ? error.proposedResolution || error.message
            : "Unknown error";
        setTestResults((prev) => ({
          ...prev,
          [key]: { state: "failed", message: msg },
        }));
      }
    },
    [api, mutateModels, t]
  );

  const handleModalTestConnection = useCallback(async () => {
    if (!formData.base_url || !formData.api_key || !formData.model_name) return;
    setModalTestResult({ state: "testing" });
    try {
      const testPayload = {
        base_url: formData.base_url,
        api_key: formData.api_key,
        model_name: formData.model_name,
        provider: formData.provider,
      };
      await api.post("/ai/models/test", testPayload);
      setModalTestResult({
        state: "success",
        message: t("aiSettings.form.testSuccess"),
      });
    } catch (error) {
      const msg =
        error instanceof KeepApiError
          ? error.proposedResolution || error.message
          : "Unknown error";
      setModalTestResult({ state: "failed", message: msg });
    }
  }, [formData, api, t]);

  // ── Render ────────────────────────────────────────────────────────────
  if (!modelsData) {
    return <Loading />;
  }

  return (
    <div className="flex flex-col gap-4">
      <header>
        <PageTitle>{t("aiSettings.title")}</PageTitle>
        <PageSubtitle>{t("aiSettings.subtitle")}</PageSubtitle>
      </header>
      <div className="flex justify-end">
        <Button
          size="xs"
          color="orange"
          icon={PlusIcon}
          onClick={openAddModal}
        >
          {t("aiSettings.form.addTitle")}
        </Button>
      </div>
      {models.length === 0 ? (
        <div className="text-center py-12">
          <CpuChipIcon className="w-12 h-12 mx-auto text-gray-300" />
          <p className="mt-4 text-gray-500 font-medium">{t("aiSettings.modelList.emptyTitle")}</p>
          <p className="mt-1 text-sm text-gray-400">{t("aiSettings.modelList.emptyDescription")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {models.map((model) => (
            <Card key={model.id} className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900">
                      {model.name}
                    </span>
                    <Badge size="xs" color="blue">{model.provider}</Badge>
                    {model.enabled ? (
                      <Badge size="xs" color="green">{t("common.labels.enabled")}</Badge>
                    ) : (
                      <Badge size="xs" color="gray">{t("common.labels.disabled")}</Badge>
                    )}
                    {model.is_default && (
                      <StarIcon className="w-4 h-4 text-yellow-500" />
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1 space-x-4">
                    <span
                      className="inline-block truncate max-w-[300px]"
                      title={model.base_url}
                    >
                      {model.base_url}
                    </span>
                    <span className="text-gray-300">|</span>
                    <span>{model.model_name}</span>
                    {model.fallback_models && model.fallback_models.length > 0 && (
                      <>
                        <span className="text-gray-300">|</span>
                        <span className="text-gray-400" title={model.fallback_models.join(", ")}>
                          fallback: {model.fallback_models.length}
                        </span>
                      </>
                    )}
                  </div>
                  {model.api_key_hint && (
                    <div className="text-xs text-gray-400 mt-0.5">
                      Key: {model.api_key_hint}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Button
                    size="xs"
                    variant="light"
                    icon={PencilIcon}
                    onClick={() => openEditModal(model)}
                  />
                  <Button
                    size="xs"
                    variant="light"
                    color="orange"
                    onClick={() => handleTestConnection(model)}
                    disabled={testResults[model.id]?.state === "testing"}
                  >
                    {testResults[model.id]?.state === "success" ? (
                      <CheckCircleIcon className="w-4 h-4 text-green-500" />
                    ) : testResults[model.id]?.state === "failed" ? (
                      <ExclamationCircleIcon className="w-4 h-4 text-red-500" />
                    ) : (
                      <ArrowPathIcon className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    size="xs"
                    variant="light"
                    color="red"
                    icon={TrashIcon}
                    onClick={() => handleDelete(model)}
                  />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      <ModelFormModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingModel(null);
          setFormData(EMPTY_FORM);
          setModalTestResult(null);
        }}
        editingModel={editingModel}
        formData={formData}
        onFieldChange={handleFieldChange}
        onSave={handleSave}
        saving={saving}
        onTestConnection={handleModalTestConnection}
        testResult={modalTestResult}
      />
    </div>
  );
}
