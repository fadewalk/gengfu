import { useI18n } from "@/i18n/hooks/useI18n";
import { ReportTemplateType } from "./models";
import {
  DocumentChartBarIcon,
  ArrowTrendingUpIcon,
  MagnifyingGlassIcon,
  BeakerIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/react/24/outline";
import clsx from "clsx";

export interface TemplateOption {
  type: ReportTemplateType | "ai_chat";
  icon: React.ElementType;
  color: string;
}

const TEMPLATES: TemplateOption[] = [
  { type: "comprehensive", icon: DocumentChartBarIcon, color: "text-blue-600" },
  { type: "trend", icon: ArrowTrendingUpIcon, color: "text-green-600" },
  { type: "root_cause", icon: MagnifyingGlassIcon, color: "text-orange-600" },
  { type: "deep", icon: BeakerIcon, color: "text-purple-600" },
  { type: "ai_chat", icon: ChatBubbleLeftRightIcon, color: "text-pink-600" },
];

interface ReportTemplateNavProps {
  selected: string;
  onSelect: (type: string) => void;
}

export function ReportTemplateNav({
  selected,
  onSelect,
}: ReportTemplateNavProps) {
  const { t } = useI18n();

  const labelMap: Record<string, string> = {
    comprehensive: t("incidents.report.template.comprehensive"),
    trend: t("incidents.report.template.trend"),
    root_cause: t("incidents.report.template.rootCause"),
    deep: t("incidents.report.template.deep"),
    ai_chat: t("incidents.report.template.aiChat"),
  };

  const descMap: Record<string, string> = {
    comprehensive: t("incidents.report.template.comprehensiveDesc"),
    trend: t("incidents.report.template.trendDesc"),
    root_cause: t("incidents.report.template.rootCauseDesc"),
    deep: t("incidents.report.template.deepDesc"),
    ai_chat: t("incidents.report.template.aiChatDesc"),
  };

  return (
    <nav className="w-48 flex-shrink-0 border-r border-slate-200 bg-white py-2">
      <div className="px-3 pb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
        {t("incidents.report.template.label")}
      </div>
      {TEMPLATES.map((tmpl) => {
        const Icon = tmpl.icon;
        const isActive = selected === tmpl.type;
        return (
          <button
            key={tmpl.type}
            onClick={() => onSelect(tmpl.type)}
            className={clsx(
              "w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors",
              isActive
                ? "bg-orange-50 border-r-2 border-orange-500"
                : "hover:bg-slate-50 border-r-2 border-transparent"
            )}
          >
            <Icon
              className={clsx(
                "w-5 h-5 mt-0.5 flex-shrink-0",
                isActive ? "text-orange-600" : tmpl.color
              )}
            />
            <div className="min-w-0">
              <div
                className={clsx(
                  "text-sm font-medium truncate",
                  isActive ? "text-orange-700" : "text-slate-700"
                )}
              >
                {labelMap[tmpl.type]}
              </div>
              <div className="text-xs text-slate-400 line-clamp-2 mt-0.5">
                {descMap[tmpl.type]}
              </div>
            </div>
          </button>
        );
      })}
    </nav>
  );
}
