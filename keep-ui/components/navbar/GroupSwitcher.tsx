"use client";

import { Fragment, useState, useEffect } from "react";
import { Popover, Transition } from "@headlessui/react";
import { UserGroupIcon } from "@heroicons/react/24/outline";
import { useGroups } from "@/utils/hooks/useGroups";
import { useI18n } from "@/i18n/hooks/useI18n";

const STORAGE_KEY = "keep-current-group-id";

export function GroupSwitcher() {
  const { t } = useI18n();
  const { data: groups, isLoading } = useGroups();
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  // Load persisted group from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSelectedGroupId(stored);
      }
    } catch {
      // localStorage unavailable (SSR or blocked)
    }
  }, []);

  // Don't render if no groups or still loading
  if (isLoading || !groups || groups.length === 0) {
    return null;
  }

  const handleSelect = (groupId: string | null) => {
    setSelectedGroupId(groupId);
    try {
      if (groupId === null) {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        localStorage.setItem(STORAGE_KEY, groupId);
      }
    } catch {
      // localStorage unavailable
    }
  };

  const selectedGroup = selectedGroupId
    ? groups.find((g) => g.id === selectedGroupId)
    : null;

  const label = selectedGroup
    ? selectedGroup.name
    : t("nav.groupSwitcher.allGroups");

  return (
    <Popover className="relative">
      {({ open, close }) => (
        <>
          <Popover.Button className="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-tremor-content hover:bg-tremor-background-muted dark:text-dark-tremor-content dark:hover:bg-dark-tremor-background-muted focus:outline-none transition-colors">
            <UserGroupIcon className="h-4 w-4" />
            <span className="max-w-[120px] truncate">{label}</span>
          </Popover.Button>

          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Popover.Panel className="absolute left-0 z-20 mt-1 w-52 rounded-md bg-white shadow-lg ring-1 ring-black/5 focus:outline-none dark:bg-dark-tremor-background">
              <div className="py-1">
                <div className="px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                  {t("nav.groupSwitcher.switchGroup")}
                </div>

                {/* "All Groups" option */}
                <button
                  className={`block w-full text-left px-4 py-2 text-sm transition-colors ${
                    selectedGroupId === null
                      ? "bg-orange-50 text-orange-700 font-medium dark:bg-orange-900/20 dark:text-orange-400"
                      : "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-dark-tremor-background-muted"
                  }`}
                  onClick={() => {
                    handleSelect(null);
                    close();
                  }}
                >
                  {t("nav.groupSwitcher.allGroups")}
                </button>

                {/* Individual groups */}
                {groups.map((group) => (
                  <button
                    key={group.id}
                    className={`block w-full text-left px-4 py-2 text-sm transition-colors ${
                      selectedGroupId === group.id
                        ? "bg-orange-50 text-orange-700 font-medium dark:bg-orange-900/20 dark:text-orange-400"
                        : "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-dark-tremor-background-muted"
                    }`}
                    onClick={() => {
                      handleSelect(group.id);
                      close();
                    }}
                  >
                    {group.name}
                  </button>
                ))}
              </div>
            </Popover.Panel>
          </Transition>
        </>
      )}
    </Popover>
  );
}
