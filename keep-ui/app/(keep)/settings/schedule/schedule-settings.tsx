"use client";

import { useApi } from "@/shared/lib/hooks/useApi";
import { Button, Card, Subtitle, TextInput, Title } from "@tremor/react";
import { useCallback, useEffect, useState } from "react";
import { useI18n } from "@/i18n/hooks/useI18n";
import { showErrorToast } from "@/shared/ui";

type Member = {
  id?: number;
  name: string;
  phone?: string;
  email?: string;
  position: number;
};

type Schedule = {
  id: number;
  name: string;
  timezone: string;
  rotation_type: "daily" | "weekly";
  rotation_starts_at: string;
  current_oncall?: string;
  members: Member[];
};

type AckStats = {
  schedule: string;
  days: number;
  total: number;
  claimed: number;
  claim_rate?: number | null;
  mtta_seconds?: number | null;
};

const EMPTY_FORM = {
  id: 0,
  name: "",
  timezone: "Asia/Shanghai",
  rotation_type: "daily" as "daily" | "weekly",
  rotation_starts_at: new Date().toISOString().slice(0, 16),
  members: [{ name: "", phone: "", email: "", position: 0 }] as Member[],
};

export default function ScheduleSettings() {
  const api = useApi();
  const { t } = useI18n();
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [ackStats, setAckStats] = useState<Record<string, AckStats>>({});
  const [form, setForm] = useState<typeof EMPTY_FORM>({ ...EMPTY_FORM });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.get("/schedules");
      setSchedules(data.schedules ?? []);
      // 逐组拉取认领统计（近 30 天）
      for (const s of data.schedules ?? []) {
        api
          .get(`/acks/stats?schedule=${encodeURIComponent(s.name)}&days=30`)
          .then((stats) => setAckStats((prev) => ({ ...prev, [s.name]: stats })))
          .catch(() => {});
      }
    } catch (e) {
      showErrorToast(e);
    }
  }, [api]);

  useEffect(() => {
    if (api.isReady()) load();
  }, [api, load]);

  const save = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      timezone: form.timezone,
      rotation_type: form.rotation_type,
      rotation_starts_at: new Date(form.rotation_starts_at).toISOString(),
      members: form.members.filter((m) => m.name.trim()),
    };
    try {
      if (editing && form.id) {
        await api.put(`/schedules/${form.id}`, payload);
      } else {
        await api.post("/schedules", payload);
      }
      setForm({ ...EMPTY_FORM });
      setEditing(false);
      await load();
    } catch (e) {
      showErrorToast(e);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    try {
      await api.delete(`/schedules/${id}`);
      await load();
    } catch (e) {
      showErrorToast(e);
    }
  };

  const edit = (s: Schedule) => {
    setEditing(true);
    setForm({
      id: s.id,
      name: s.name,
      timezone: s.timezone,
      rotation_type: s.rotation_type,
      rotation_starts_at: s.rotation_starts_at.slice(0, 16),
      members: s.members.length
        ? s.members.map((m) => ({ id: m.id, name: m.name, phone: m.phone ?? "", email: m.email ?? "", position: m.position }))
        : [{ name: "", phone: "", email: "", position: 0 }],
    });
  };

  const setMember = (idx: number, field: keyof Member, value: string) => {
    setForm((prev) => {
      const members = [...prev.members];
      members[idx] = { ...members[idx], [field]: value };
      return { ...prev, members };
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <Title>{t("schedule.title")}</Title>
        <Subtitle>{t("schedule.subtitle")}</Subtitle>
      </div>

      <Card>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <TextInput
            placeholder={t("schedule.namePlaceholder")}
            value={form.name}
            onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
          />
          <TextInput
            placeholder={t("schedule.timezonePlaceholder")}
            value={form.timezone}
            onChange={(e) => setForm((p) => ({ ...p, timezone: e.target.value }))}
          />
          <select
            className="rounded-md border-gray-300 bg-transparent text-tremor-default"
            value={form.rotation_type}
            onChange={(e) => setForm((p) => ({ ...p, rotation_type: e.target.value as "daily" | "weekly" }))}
          >
            <option value="daily">{t("schedule.daily")}</option>
            <option value="weekly">{t("schedule.weekly")}</option>
          </select>
          <input
            type="datetime-local"
            className="rounded-md border-gray-300 bg-transparent text-tremor-default shadow-tremor-input"
            value={form.rotation_starts_at}
            onChange={(e) => setForm((p) => ({ ...p, rotation_starts_at: e.target.value }))}
          />
        </div>

        <div className="mt-3 space-y-2">
          {form.members.map((m, idx) => (
            <div key={idx} className="grid grid-cols-1 md:grid-cols-4 gap-2 items-center">
              <TextInput
                placeholder={t("schedule.memberName")}
                value={m.name}
                onChange={(e) => setMember(idx, "name", e.target.value)}
              />
              <TextInput
                placeholder={t("schedule.memberPhone")}
                value={m.phone}
                onChange={(e) => setMember(idx, "phone", e.target.value)}
              />
              <TextInput
                placeholder={t("schedule.memberEmail")}
                value={m.email}
                onChange={(e) => setMember(idx, "email", e.target.value)}
              />
              <Button
                variant="secondary"
                size="xs"
                onClick={() =>
                  setForm((p) => ({ ...p, members: p.members.filter((_, i) => i !== idx) }))
                }
              >
                {t("common.delete")}
              </Button>
            </div>
          ))}
          <Button
            variant="light"
            size="xs"
            onClick={() =>
              setForm((p) => ({
                ...p,
                members: [...p.members, { name: "", phone: "", email: "", position: p.members.length }],
              }))
            }
          >
            {t("schedule.addMember")}
          </Button>
        </div>

        <div className="mt-4 flex gap-2">
          <Button color="orange" loading={saving} onClick={save}>
            {editing ? t("common.actions.update") : t("common.actions.create")}
          </Button>
          {editing && (
            <Button
              variant="secondary"
              onClick={() => {
                setEditing(false);
                setForm({ ...EMPTY_FORM });
              }}
            >
              {t("common.actions.cancel")}
            </Button>
          )}
        </div>
      </Card>

      <Card>
        <Title>{t("schedule.listTitle")}</Title>
        <div className="mt-3 space-y-3">
          {schedules.length === 0 && (
            <p className="text-gray-500 text-sm">{t("schedule.empty")}</p>
          )}
          {schedules.map((s) => (
            <div key={s.id} className="flex items-center justify-between border rounded-lg p-3">
              <div>
                <p className="font-medium">
                  {s.name}
                  {s.current_oncall && (
                    <span className="ml-2 inline-block rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
                      {t("schedule.currentOncall")}: {s.current_oncall}
                    </span>
                  )}
                </p>
                <p className="text-xs text-gray-500">
                  {s.rotation_type === "daily" ? t("schedule.daily") : t("schedule.weekly")}
                  {" · "}
                  {s.timezone}
                  {" · "}
                  {s.members.map((m) => m.name).join(" → ")}
                </p>
                {ackStats[s.name] && (
                  <p className="text-xs text-gray-500 mt-1">
                    {t("schedule.ackStats", {
                      total: ackStats[s.name]!.total,
                      claimed: ackStats[s.name]!.claimed,
                      mtta: ackStats[s.name]!.mtta_seconds != null
                        ? `${Math.round(ackStats[s.name]!.mtta_seconds! / 60)} ${t("schedule.minutes")}`
                        : "-",
                    })}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="xs" variant="secondary" onClick={() => edit(s)}>
                  {t("common.actions.edit")}
                </Button>
                <Button size="xs" variant="secondary" color="red" onClick={() => remove(s.id)}>
                  {t("common.delete")}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
