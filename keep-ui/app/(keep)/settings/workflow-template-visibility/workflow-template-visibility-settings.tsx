"use client";

import { useState } from "react";
import { TextInput, Button, Badge, Switch } from "@tremor/react";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import useSWR from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useI18n } from "@/i18n/hooks/useI18n";
import { showErrorToast, showSuccessToast } from "@/shared/ui";
import { PageTitle } from "@/shared/ui/PageTitle";
import Loading from "@/app/(keep)/loading";
import { useQueryWorkflowTemplate } from "@/entities/workflows/lib/use-query-workflow-template";

interface WorkflowTemplateItem {
  name: string;
  workflow_raw_id: string;
  workflow?: {
    name?: string;
    description?: string;
    id?: string;
  };
}

export default function WorkflowTemplateVisibilitySettings() {
  const { t } = useI18n();
  const api = useApi();
  const [search, setSearch] = useState("");
  const [localHidden, setLocalHidden] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);

  // Load all templates (including hidden) for the settings page
  const { data: templatesData, isLoading: templatesLoading } =
    useQueryWorkflowTemplate(
      { cel: "", limit: 1000, offset: 0 },
      {
        revalidateOnFocus: false,
      }
    );

  // Override: we need include_hidden=true for settings, so fetch directly
  const { data: allTemplatesData, isLoading: allTemplatesLoading } = useSWR(
    api.isReady() ? "/workflows/templates/query?include_hidden=true" : null,
    (url: string) => api.post(url, { cel: "", limit: 1000, offset: 0 }),
    { revalidateOnFocus: false }
  );

  // Load hidden template list
  const { data: hiddenData, mutate: mutateHidden } = useSWR(
    api.isReady() ? "/settings/tenant/hidden-workflow-templates" : null,
    (url: string) => api.get(url),
    { revalidateOnFocus: false }
  );

  const allTemplates: WorkflowTemplateItem[] =
    allTemplatesData?.results ?? templatesData ?? [];
  const hiddenTemplates = localHidden ?? hiddenData?.hidden_workflow_templates ?? [];
  const hiddenSet = new Set(hiddenTemplates ?? []);

  const filteredTemplates = allTemplates
    ?.filter((tmpl: WorkflowTemplateItem) => {
      const displayName =
        tmpl.workflow?.name || tmpl.workflow_raw_id || tmpl.name || "";
      const desc = tmpl.workflow?.description || "";
      return (
        displayName.toLowerCase().includes(search.toLowerCase()) ||
        desc.toLowerCase().includes(search.toLowerCase()) ||
        (tmpl.workflow_raw_id || "").toLowerCase().includes(search.toLowerCase())
      );
    })
    .sort((a: WorkflowTemplateItem, b: WorkflowTemplateItem) => {
      const aId = a.workflow_raw_id || a.name || "";
      const bId = b.workflow_raw_id || b.name || "";
      const aHidden = hiddenSet.has(aId);
      const bHidden = hiddenSet.has(bId);
      if (aHidden !== bHidden) return aHidden ? 1 : -1;
      const aName = a.workflow?.name || aId;
      const bName = b.workflow?.name || bId;
      return aName.localeCompare(bName);
    }) ?? [];

  const toggleTemplate = (templateId: string) => {
    setLocalHidden((prev) => {
      const base = (prev ?? hiddenTemplates ?? []) as string[];
      const newSet = new Set<string>(base);
      if (newSet.has(templateId)) {
        newSet.delete(templateId);
      } else {
        newSet.add(templateId);
      }
      return Array.from(newSet);
    });
  };

  const saveChanges = async () => {
    if (!localHidden) return;
    setSaving(true);
    try {
      await api.put("/settings/tenant/hidden-workflow-templates", {
        hidden_workflow_templates: localHidden,
      });
      await mutateHidden(
        { hidden_workflow_templates: localHidden },
        false
      );
      showSuccessToast(t("common.messages.updatedSuccessfully"));
      setLocalHidden(null);
    } catch {
      showErrorToast(t("common.messages.error"));
    } finally {
      setSaving(false);
    }
  };

  const hideAll = () => {
    const allIds = allTemplates?.map((t: WorkflowTemplateItem) => t.workflow_raw_id || t.name) ?? [];
    setLocalHidden(allIds);
  };

  const showAll = () => {
    setLocalHidden([]);
  };

  if (templatesLoading && allTemplatesLoading) return <Loading />;

  const visibleCount =
    (allTemplates?.length ?? 0) - (hiddenTemplates?.length ?? 0);

  return (
    <div className="space-y-6">
      <div>
        <PageTitle>
          {t("workflowTemplateVisibility.title")}
        </PageTitle>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t("workflowTemplateVisibility.subtitle")}
        </p>
      </div>

      <div className="flex gap-2">
        <TextInput
          placeholder={t("common.filters.search")}
          value={search}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            setSearch(e.target.value)
          }
          className="max-w-xs"
          icon={MagnifyingGlassIcon}
        />
        {localHidden !== null && (
          <div className="flex gap-2">
            <Button
              size="xs"
              variant="secondary"
              onClick={saveChanges}
              loading={saving}
              disabled={saving}
            >
              {t("common.actions.save")} ({localHidden.length})
            </Button>
            <Button
              size="xs"
              variant="secondary"
              color="orange"
              onClick={() => setLocalHidden(null)}
            >
              {t("common.actions.reset")}
            </Button>
          </div>
        )}
      </div>

      <div className="flex gap-2 text-sm text-gray-500 pb-2">
        <Button size="xs" variant="light" onClick={showAll}>
          {t("workflowTemplateVisibility.showAll")}
        </Button>
        <Button size="xs" variant="light" onClick={hideAll}>
          {t("workflowTemplateVisibility.hideAll")}
        </Button>
        <span className="flex items-center">
          {t("workflowTemplateVisibility.stats", {
            hidden: hiddenTemplates?.length ?? 0,
            total: allTemplates?.length ?? 0,
          })}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-2 gap-2 max-h-[600px] overflow-y-auto">
        {filteredTemplates.map((tmpl: WorkflowTemplateItem) => {
          const templateId = tmpl.workflow_raw_id || tmpl.name || "";
          const displayName = tmpl.workflow?.name || templateId;
          const description = tmpl.workflow?.description || "";
          const isHidden = hiddenSet.has(templateId);
          return (
            <div
              key={templateId}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                isHidden
                  ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="font-medium text-sm truncate">
                  {displayName}
                </span>
                {description && (
                  <span className="text-xs text-gray-400 truncate max-w-[200px]">
                    {description.slice(0, 60)}
                    {description.length > 60 ? "..." : ""}
                  </span>
                )}
              </div>
              <Switch
                checked={!isHidden}
                onChange={() => toggleTemplate(templateId)}
                color={!isHidden ? "green" : "red"}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
