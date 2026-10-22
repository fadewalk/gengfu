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

type AckWindow = "7" | "30";

type AckRecordItem = {
  alert_name: string;
  member: string;
  created_at: string;
  acked_at: string | null;
  acked: boolean;
  mtta_seconds: number | null;
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
  const [ackStats, setAckStats] = useState<Record<string, Record<AckWindow, AckStats | null>>>({});
  const [statWindow, setStatWindow] = useState<AckWindow>("30");
  const [previews, setPreviews] = useState<Record<string, { date: string; member: string }[]>>({});
  const [recentAcks, setRecentAcks] = useState<Record<string, AckRecordItem[]>>({});
  const [copied, setCopied] = useState<string>("");
  const [calendarView, setCalendarView] = useState<"strip" | "month">("strip");
  const [monthOffset, setMonthOffset] = useState(0);
  const [form, setForm] = useState<typeof EMPTY_FORM>({ ...EMPTY_FORM });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.get("/schedules");
      setSchedules(data.schedules ?? []);
      // 逐组拉取认领统计（7 天 + 30 天双窗口）
      for (const s of data.schedules ?? []) {
        for (const days of ["7", "30"] as AckWindow[]) {
          api
            .get(`/acks/stats?schedule=${encodeURIComponent(s.name)}&days=${days}`)
            .then((stats) =>
              setAckStats((prev) => ({
                ...prev,
                [s.name]: { ...(prev[s.name] ?? {}), [days]: stats },
              }))
            )
            .catch(() => {});
        }
        api
          .get(`/acks/recent?schedule=${encodeURIComponent(s.name)}&days=30&limit=5`)
          .then((d) => setRecentAcks((prev) => ({ ...prev, [s.name]: d.records ?? [] })))
          .catch(() => {});
        api
          .get(`/schedules/${s.id}/preview?days=31`)
          .then((p) =>
            setPreviews((prev) => ({
              ...prev,
              [s.name]: p.rotation?.map((r: { date: string; member: string }) => r) ?? [],
            }))
          )
          .catch(() => {});
      }
    } catch (e) {
      showErrorToast(e);
    }
  }, [api]);

  // 全部组 30 天 MTTA 汇总
  const summary = (() => {
    const total = schedules.reduce((acc, s) => acc + (ackStats[s.name]?.["30"]?.total ?? 0), 0);
    const claimed = schedules.reduce((acc, s) => acc + (ackStats[s.name]?.["30"]?.claimed ?? 0), 0);
    const withMtta = schedules
      .map((s) => ackStats[s.name]?.["30"]?.mtta_seconds)
      .filter((v): v is number => v != null);
    const avgMtta = withMtta.length
      ? Math.round(withMtta.reduce((a, b) => a + b, 0) / withMtta.length / 60)
      : null;
    return { total, claimed, avgMtta };
  })();

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

      <div className="grid grid-cols-3 gap-3">
        <Card className="p-3">
          <p className="text-xs text-gray-500">{t("schedule.statNotifications")}</p>
          <p className="text-xl font-semibold">{summary.total}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-gray-500">{t("schedule.statClaimed")}</p>
          <p className="text-xl font-semibold">{summary.claimed}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-gray-500">{t("schedule.statMtta")}</p>
          <p className="text-xl font-semibold">
            {summary.avgMtta != null ? `${summary.avgMtta} ${t("schedule.minutes")}` : "-"}
          </p>
        </Card>
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
                {(() => {
                  const st = ackStats[s.name]?.[statWindow];
                  if (!st) return null;
                  return (
                    <div className="mt-2 flex items-center gap-2 text-xs">
                      <select
                        className="rounded border-gray-300 bg-transparent text-xs"
                        value={statWindow}
                        onChange={(e) => setStatWindow(e.target.value as AckWindow)}
                      >
                        <option value="7">{t("schedule.last7Days")}</option>
                        <option value="30">{t("schedule.last30Days")}</option>
                      </select>
                      <span className="text-gray-500">
                        {t("schedule.ackStats", {
                          total: st.total,
                          claimed: st.claimed,
                          mtta: st.mtta_seconds != null
                            ? `${Math.round(st.mtta_seconds / 60)} ${t("schedule.minutes")}`
                            : "-",
                        })}
                      </span>
                    </div>
                  );
                })()}
                {recentAcks[s.name] && recentAcks[s.name]!.length > 0 && (
                  <div className="mt-2 border-t pt-2">
                    <p className="text-xs text-gray-500 mb-1">{t("schedule.recentClaims")}</p>
                    {recentAcks[s.name]!.slice(0, 5).map((r, i) => (
                      <div key={i} className="flex items-center justify-between text-xs py-0.5">
                        <span className="truncate text-gray-700">{r.alert_name || "-"}</span>
                        <span className={r.acked ? "text-green-600" : "text-orange-500"}>
                          {r.acked ? t("schedule.acked") : t("schedule.pending")}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {previews[s.name] && previews[s.name]!.length > 0 && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs text-gray-500">{t("schedule.next7Days")}</p>
                      <div className="flex gap-1">
                        <Button size="xs" variant={calendarView === "strip" ? "primary" : "secondary"}
                          onClick={() => setCalendarView("strip")}>{t("schedule.viewStrip")}</Button>
                        <Button size="xs" variant={calendarView === "month" ? "primary" : "secondary"}
                          onClick={() => setCalendarView("month")}>{t("schedule.viewMonth")}</Button>
                      </div>
                    </div>
                    {calendarView === "strip" ? (
                      <div className="flex gap-1 overflow-x-auto pb-1">
                        {previews[s.name]!.slice(0, 14).map((p) => {
                          const isToday = p.date === new Date().toISOString().slice(0, 10);
                          return (
                            <div
                              key={p.date}
                              className={`flex-shrink-0 rounded-md border px-2 py-1 text-center ${
                                isToday ? "border-orange-400 bg-orange-50" : "border-gray-200"
                              }`}
                            >
                              <p className={`text-xs font-medium ${isToday ? "text-orange-600" : "text-gray-700"}`}>
                                {p.date.slice(5)}
                              </p>
                              <p className="text-xs text-gray-500">{p.member || "-"}</p>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <MonthGrid
                        preview={previews[s.name]!}
                        monthOffset={monthOffset}
                        onPrev={() => setMonthOffset((v) => v - 1)}
                        onNext={() => setMonthOffset((v) => v + 1)}
                      />
                    )}
                  </div>
                )}
              </div>
              <Button
                size="xs"
                variant="secondary"
                onClick={() => {
                  const link = `${window.location.origin}/ack/${s.name}`;
                  navigator.clipboard.writeText(link);
                  setCopied(s.name);
                  setTimeout(() => setCopied(""), 1500);
                }}
              >
                {copied === s.name ? t("schedule.copied") : t("schedule.copyClaimLink")}
              </Button>
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


function MonthGrid({
  preview,
  monthOffset,
  onPrev,
  onNext,
}: {
  preview: { date: string; member: string }[];
  monthOffset: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  const byDate: Record<string, string> = {};
  for (const p of preview) byDate[p.date] = p.member;

  const base = new Date();
  base.setDate(1);
  base.setMonth(base.getMonth() + monthOffset);
  const year = base.getFullYear();
  const month = base.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDow = new Date(year, month, 1).getDay(); // 0=周日
  const todayStr = new Date().toISOString().slice(0, 10);

  const cells: ({ date: string; member: string; inMonth: boolean } | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ date, member: byDate[date] ?? "", inMonth: true });
  }

  const monthLabel = `${year}-${String(month + 1).padStart(2, "0")}`;
  const dows = ["日", "一", "二", "三", "四", "五", "六"];

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Button size="xs" variant="secondary" onClick={onPrev}>‹</Button>
        <p className="text-xs font-medium text-gray-700">{monthLabel}</p>
        <Button size="xs" variant="secondary" onClick={onNext}>›</Button>
      </div>
      <div className="grid grid-cols-7 gap-1">
        {dows.map((d) => (
          <p key={d} className="text-xs text-gray-400 text-center">{d}</p>
        ))}
        {cells.map((c, i) =>
          c === null ? (
            <div key={`e${i}`} />
          ) : (
            <div
              key={c.date}
              className={`rounded border px-1 py-1 text-center ${
                c.date === todayStr ? "border-orange-400 bg-orange-50" : "border-gray-200"
              }`}
            >
              <p className="text-xs text-gray-500">{c.date.slice(8)}</p>
              <p className="text-xs truncate" title={c.member}>{c.member || "-"}</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}
