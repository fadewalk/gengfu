"use client";

import { useState, useEffect } from "react";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useProviders } from "@/utils/hooks/useProviders";
import { KeepApiError } from "@/shared/api";
import {
  Card,
  Title,
  TextInput,
  Textarea,
  Button,
  Select,
  SelectItem,
  Badge,
} from "@tremor/react";
import Modal from "@/components/ui/Modal";
import { toast } from "react-toastify";
import { TrashIcon, PlusIcon, PencilIcon, CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";

interface AIEndpoint {
  id?: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  models: string;
  isDefault: boolean;
}

interface ProviderInfo {
  type: string;
  installed: boolean;
  name?: string;
}

export default function AISettings() {
  const api = useApi();
  const { data: providersData, mutate } = useProviders();
  const [endpoints, setEndpoints] = useState<AIEndpoint[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEndpoint, setEditingEndpoint] = useState<AIEndpoint | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Form state
  const [formData, setFormData] = useState<AIEndpoint>({
    name: "",
    baseUrl: "",
    apiKey: "",
    models: "",
    isDefault: false,
  });

  // Load CustomAI providers from the installed providers list
  useEffect(() => {
    if (providersData?.installed_providers) {
      const customAIProviders = providersData.installed_providers
        .filter((p: ProviderInfo) => p.type === "customai")
        .map((p: any) => ({
          id: p.id,
          name: p.name || p.type,
          baseUrl: p.config?.base_url || "",
          apiKey: p.config?.api_key ? "***" : "",
          models: p.config?.models || "",
          isDefault: p.name?.includes("(默认)") || false,
        }));
      setEndpoints(customAIProviders);
    }
  }, [providersData]);

  const resetForm = () => {
    setFormData({
      name: "",
      baseUrl: "",
      apiKey: "",
      models: "",
      isDefault: false,
    });
    setEditingEndpoint(null);
  };

  const openAddModal = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const openEditModal = (endpoint: AIEndpoint) => {
    setEditingEndpoint(endpoint);
    setFormData({ ...endpoint });
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formData.name || !formData.baseUrl || !formData.apiKey) {
      toast.error("请填写所有必填字段");
      return;
    }

    setIsLoading(true);
    try {
      const providerData = {
        provider_id: `customai_${formData.name.replace(/\s+/g, "_").toLowerCase()}`,
        provider_name: formData.isDefault ? `${formData.name} (默认)` : formData.name,
        provider_type: "customai",
        pulling_enabled: false,
        base_url: formData.baseUrl,
        api_key: formData.apiKey,
        models: formData.models || "gpt-4o-mini",
      };

      const response = await api.post(`/providers/install`, providerData);

      if (response.ok || response.status === 200) {
        toast.success(editingEndpoint ? "AI 端点已更新" : "AI 端点已添加");
        setIsModalOpen(false);
        mutate();
        resetForm();
      } else {
        const error = await response.json();
        throw new Error(error.message || "保存失败");
      }
    } catch (error) {
      console.error("Failed to save AI endpoint:", error);
      toast.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (endpoint: AIEndpoint) => {
    if (!endpoint.id) return;

    if (!confirm(`确定要删除 AI 端点 "${endpoint.name}" 吗？`)) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.delete(`/providers/customai/${endpoint.id}`);

      if (response.ok || response.status === 200) {
        toast.success("AI 端点已删除");
        mutate();
      } else {
        throw new Error("删除失败");
      }
    } catch (error) {
      console.error("Failed to delete AI endpoint:", error);
      toast.error("删除失败");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <Card>
        <div className="flex justify-between items-center mb-4">
          <div>
            <Title>AI 端点配置</Title>
            <p className="text-sm text-gray-500 mt-1">
              配置自定义 AI 模型端点（支持 OpenAI 兼容 API）。可配置多个端点实现故障转移。
            </p>
          </div>
          <Button size="xs" icon={PlusIcon} onClick={openAddModal}>
            添加端点
          </Button>
        </div>

        {/* Endpoints List */}
        {endpoints.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>暂无配置的 AI 端点</p>
            <p className="text-sm mt-1">点击上方按钮添加您的第一个 AI 端点</p>
          </div>
        ) : (
          <div className="space-y-3">
            {endpoints.map((endpoint) => (
              <div
                key={endpoint.id}
                className="flex items-center justify-between p-4 border rounded-lg bg-gray-50"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{endpoint.name}</span>
                    {endpoint.isDefault && (
                      <Badge color="blue" size="xs">
                        默认
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    <span className="mr-4">地址: {endpoint.baseUrl}</span>
                    <span>模型: {endpoint.models || "gpt-4o-mini"}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="xs"
                    variant="light"
                    icon={PencilIcon}
                    onClick={() => openEditModal(endpoint)}
                  />
                  <Button
                    size="xs"
                    variant="light"
                    color="red"
                    icon={TrashIcon}
                    onClick={() => handleDelete(endpoint)}
                    disabled={isLoading}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Info Card */}
      <Card>
        <Title className="text-base">使用说明</Title>
        <ul className="text-sm text-gray-600 mt-2 space-y-1">
          <li>• 在工作流中使用时，引用 provider 名称即可（如 {"{{ providers.my_ai }}"}）</li>
          <li>• 可以配置多个端点实现故障转移，Keep 会按顺序尝试</li>
          <li>• 支持的模型：GLM、MiniMax、DeepSeek、Qwen、Kimi 等所有 OpenAI 兼容 API</li>
        </ul>
      </Card>

      {/* Add/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          resetForm();
        }}
        title={editingEndpoint ? "编辑 AI 端点" : "添加 AI 端点"}
      >
        <div className="flex flex-col gap-4 py-4">
          <div>
            <label className="text-sm font-medium text-gray-700">
              端点名称 <span className="text-red-500">*</span>
            </label>
            <TextInput
              value={formData.name}
              onValueChange={(value) => setFormData({ ...formData, name: value })}
              placeholder="例如: 智谱 GLM"
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              API 地址 <span className="text-red-500">*</span>
            </label>
            <TextInput
              value={formData.baseUrl}
              onValueChange={(value) => setFormData({ ...formData, baseUrl: value })}
              placeholder="https://api.deepseek.com/v1"
              className="mt-1"
            />
            <p className="text-xs text-gray-500 mt-1">
              提供 OpenAI 兼容 API 的地址
            </p>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              API Key <span className="text-red-500">*</span>
            </label>
            <TextInput
              value={formData.apiKey}
              onValueChange={(value) => setFormData({ ...formData, apiKey: value })}
              placeholder="sk-..."
              className="mt-1"
              type="password"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">模型列表</label>
            <TextInput
              value={formData.models}
              onValueChange={(value) => setFormData({ ...formData, models: value })}
              placeholder="glm-4, glm-3, qwen-2"
              className="mt-1"
            />
            <p className="text-xs text-gray-500 mt-1">
              多个模型用逗号分隔，第一个为默认模型。故障时会自动尝试后续模型。
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isDefault"
              checked={formData.isDefault}
              onChange={(e) =>
                setFormData({ ...formData, isDefault: e.target.checked })
              }
              className="rounded border-gray-300"
            />
            <label htmlFor="isDefault" className="text-sm text-gray-700">
              设为默认端点
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <Button
            size="xs"
            variant="secondary"
            onClick={() => {
              setIsModalOpen(false);
              resetForm();
            }}
          >
            取消
          </Button>
          <Button
            size="xs"
            onClick={handleSave}
            loading={isLoading}
            disabled={!formData.name || !formData.baseUrl || !formData.apiKey}
          >
            保存
          </Button>
        </div>
      </Modal>
    </div>
  );
}
