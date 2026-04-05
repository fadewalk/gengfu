"use client";

import { useState } from "react";
import {
  TextInput,
  Button,
  Badge,
  Switch,
} from "@tremor/react";
import { EyeIcon } from "@heroicons/react/24/outline";
import useSWR from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useI18n } from "@/i18n/hooks/useI18n";
import { showErrorToast, showSuccessToast } from "@/shared/ui";
import { PageTitle } from "@/shared/ui/PageTitle";
import Loading from "@/app/(keep)/loading";
import { useProviders } from "@/utils/hooks/useProviders";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { Provider } from "@/shared/api/providers";

export default function ProviderVisibilitySettings() {
  const { t } = useI18n();
  const api = useApi();
  const [search, setSearch] = useState("");
  const [localHidden, setLocalHidden] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);

  const { data: providersData, isLoading: providersLoading } = useProviders(
    { revalidateOnFocus: false },
    { include_hidden: "true" }
  );
  const { data: hiddenData, mutate: mutateHidden } = useSWR(
    api.isReady() ? "/settings/tenant/hidden-providers" : null,
    (url: string) => api.get(url),
    { revalidateOnFocus: false }
  );

  const allProviders: Provider[] = providersData?.providers ?? [];

  const hiddenProviders = localHidden ?? hiddenData?.hidden_providers ?? [];
  const hiddenSet = new Set(hiddenProviders ?? []);

  const filteredProviders = allProviders
    ?.filter((p: Provider) =>
      p.display_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.type?.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a: Provider, b: Provider) => {
      const aHidden = hiddenSet.has(a.type);
      const bHidden = hiddenSet.has(b.type);
      if (aHidden !== bHidden) return aHidden ? 1 : -1;
      return (a.display_name || a.type).localeCompare(b.display_name || b.type);
    }) ?? [];

  const toggleProvider = (providerType: string) => {
    setLocalHidden((prev) => {
      const base = (prev ?? hiddenProviders ?? []) as string[];
      const newSet = new Set<string>(base);
      if (newSet.has(providerType)) {
        newSet.delete(providerType);
      } else {
        newSet.add(providerType);
      }
      return Array.from(newSet) as string[];
    });
  };

  const saveChanges = async () => {
    if (!localHidden) return;
    setSaving(true);
    try {
      await api.put("/settings/tenant/hidden-providers", {
        hidden_providers: localHidden,
      });
      // Update SWR cache immediately so the UI reflects the change without refresh
      await mutateHidden({ hidden_providers: localHidden }, false);
      showSuccessToast(t("common.messages.updatedSuccessfully"));
      setLocalHidden(null);
    } catch {
      showErrorToast(t("common.messages.error"));
    } finally {
      setSaving(false);
    }
  };

  const hideAll = () => {
    const allTypes = allProviders?.map((p) => p.type) ?? [];
    setLocalHidden(allTypes);
  };

  const showAll = () => {
    setLocalHidden([]);
  };

  if (providersLoading) return <Loading />;

  const visibleCount =
    (allProviders?.length ?? 0) - (hiddenProviders?.length ?? 0);

  return (
    <div className="space-y-6">
      <div>
        <PageTitle>{t("providerVisibility.title")}</PageTitle>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t("providerVisibility.subtitle")}
        </p>
      </div>

      <div className="flex gap-2">
        <TextInput
          placeholder={t("common.filters.search")}
          value={search}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
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
          {t("providerVisibility.showAll")}
        </Button>
        <Button size="xs" variant="light" onClick={hideAll}>
          {t("providerVisibility.hideAll")}
        </Button>
        <span className="flex items-center">
          {hiddenProviders?.length ?? 0} / {allProviders?.length ?? 0}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-2 gap-2 max-h-[600px] overflow-y-auto">
        {filteredProviders.map((provider: Provider) => {
          const isHidden = hiddenSet.has(provider.type);
          return (
            <div
              key={provider.type}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                isHidden ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950" : "border-gray-200 dark:border-gray-700"
              }`}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="font-medium text-sm truncate">
                  {provider.display_name || provider.type}
                </span>
                <div className="flex gap-1">
                  {provider.tags?.slice(0, 3).map((tag: string) => (
                    <Badge key={tag} size="xs" color="gray">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
              <Switch
                checked={!isHidden}
                onChange={() => toggleProvider(provider.type)}
                color={!isHidden ? "green" : "red"}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
