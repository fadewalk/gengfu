"use client";

import { useI18n } from "@/i18n/hooks/useI18n";
import React, { useState, useEffect } from "react";
import {
  Select,
  SelectItem,
  Badge,
  MultiSelect,
  MultiSelectItem,
} from "@tremor/react";
import { UserGroupIcon } from "@heroicons/react/24/outline";

interface Group {
  id: string;
  name: string;
  memberCount?: number;
}

interface GroupSelectorProps {
  /** Currently selected group_id. null = tenant-wide */
  value: string | null;
  /** Called when user selects a group */
  onChange: (groupId: string | null) => void;
  /** Whether to show "All Groups" / "Tenant-wide" option */
  showGlobal?: boolean;
}

/**
 * A reusable group selector component.
 * Used when creating/editing resources (Preset, Dashboard, Workflow, etc.)
 * to assign them to a group.
 */
export function GroupSelector({
  value,
  onChange,
  showGlobal = true,
}: GroupSelectorProps) {
  const { t } = useI18n();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchGroups() {
      try {
        const res = await fetch("/auth/groups");
        if (res.ok) {
          const data = await res.json();
          setGroups(data);
        }
      } catch {
        // Silently fail - groups are optional
      } finally {
        setLoading(false);
      }
    }
    fetchGroups();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-400 text-sm">
        <UserGroupIcon className="w-4 h-4" />
        Loading groups...
      </div>
    );
  }

  if (groups.length === 0) {
    return null; // No groups configured - hide selector
  }

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700">
        {t("common.group") || "Group"}
      </label>
      <Select
        value={value ?? "__global__"}
        onValueChange={(v: string) => {
          onChange(v === "__global__" ? null : v);
        }}
      >
        {showGlobal && (
          <SelectItem value="__global__">
            <div className="flex items-center gap-2">
              <Badge color="gray" size="xs">
                Global
              </Badge>
              <span className="text-gray-500 text-xs">
                Visible to all users in tenant
              </span>
            </div>
          </SelectItem>
        )}
        {groups.map((group) => (
          <SelectItem key={group.id} value={group.id}>
            <div className="flex items-center gap-2">
              <UserGroupIcon className="w-4 h-4 text-gray-400" />
              {group.name}
              {group.memberCount !== undefined && (
                <span className="text-xs text-gray-400">
                  ({group.memberCount} members)
                </span>
              )}
            </div>
          </SelectItem>
        ))}
      </Select>
    </div>
  );
}

/**
 * A multi-select component for assigning users to groups.
 */
export function GroupMultiSelect({
  selectedGroupIds,
  onChange,
}: {
  selectedGroupIds: string[];
  onChange: (groupIds: string[]) => void;
}) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchGroups() {
      try {
        const res = await fetch("/auth/groups");
        if (res.ok) {
          const data = await res.json();
          setGroups(data);
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }
    fetchGroups();
  }, []);

  if (loading || groups.length === 0) return null;

  return (
    <MultiSelect
      value={selectedGroupIds}
      onValueChange={onChange}
    >
      {groups.map((group) => (
        <MultiSelectItem key={group.id} value={group.id}>
          {group.name}
        </MultiSelectItem>
      ))}
    </MultiSelect>
  );
}
