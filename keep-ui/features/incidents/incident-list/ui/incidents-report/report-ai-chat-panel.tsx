"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import {
  useCopilotAction,
  useCopilotReadable,
  useCopilotMessagesContext,
  useCopilotChat,
} from "@copilotkit/react-core";
import {
  ActionExecutionMessage,
  MessageRole,
  ResultMessage,
  TextMessage,
} from "@copilotkit/runtime-client-gql";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useI18n } from "@/i18n/hooks/useI18n";
import { useLocale } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import {
  DocumentChartBarIcon,
  ArrowTrendingUpIcon,
  MagnifyingGlassIcon,
  BeakerIcon,
} from "@heroicons/react/24/outline";
import "@copilotkit/react-ui/styles.css";

const REPORT_CHAT_INSTRUCTIONS_EN = `You are an expert incident analyst. The user has selected a set of incidents and wants to explore them interactively.

Your capabilities:
- Analyze incident patterns, trends, and root causes
- Compare incidents and identify recurring issues
- Suggest improvements and preventive measures
- Assess risk levels and potential impact

Rules:
- DO NOT make up any information. Use only the data provided.
- Be concise and actionable.
- When suggesting analysis, reference specific incidents by name or ID.
- If you need more context, ask the user.
- Always respond in the same language as the user's question.`;

const REPORT_CHAT_INSTRUCTIONS_ZH = `你是一个专业的事件分析师。用户选择了一组事件，希望通过对话来深入探索。

你的能力：
- 分析事件模式、趋势和根因
- 比较事件并识别重复出现的问题
- 提出改进建议和预防措施
- 评估风险等级和潜在影响

规则：
- 不要编造任何信息，只使用提供的数据
- 回答要简洁、有针对性
- 在建议分析时，引用具体的事件名称或 ID
- 如果需要更多上下文，请向用户提问
- 始终用与用户提问相同的语言回答`;

/** Preset prompt definitions */
interface PresetPrompt {
  key: string;
  labelKey: string;
  icon: React.ElementType;
  color: string;
  promptEN: string;
  promptZH: string;
}

const PRESET_PROMPTS: PresetPrompt[] = [
  {
    key: "comprehensive",
    labelKey: "incidents.report.template.comprehensive",
    icon: DocumentChartBarIcon,
    color: "text-blue-600 bg-blue-50 hover:bg-blue-100",
    promptEN:
      "Please generate a comprehensive incident report covering all metrics: severity distribution, affected services, MTTD, MTTR, recurring incidents, most common reasons, and actionable recommendations.",
    promptZH:
      "请生成一份综合事件报告，涵盖所有指标：严重程度分布、受影响服务、平均检测时间(MTTD)、平均恢复时间(MTTR)、重复发生事件、最常见原因、以及可执行的改进建议。",
  },
  {
    key: "trend",
    labelKey: "incidents.report.template.trend",
    icon: ArrowTrendingUpIcon,
    color: "text-green-600 bg-green-50 hover:bg-green-100",
    promptEN:
      "Please analyze the incident trends: time distribution patterns, frequency changes over time, identify any emerging patterns or anomalies, and suggest what trends might develop.",
    promptZH:
      "请分析事件趋势：时间分布规律、频率随时间的变化、识别任何新出现的模式或异常、并预测未来可能的发展趋势。",
  },
  {
    key: "root_cause",
    labelKey: "incidents.report.template.rootCause",
    icon: MagnifyingGlassIcon,
    color: "text-orange-600 bg-orange-50 hover:bg-orange-100",
    promptEN:
      "Please perform a root cause analysis: identify the most common root causes, analyze systemic weaknesses, find correlations between incidents, and suggest specific fixes for each root cause.",
    promptZH:
      "请进行根因分析：识别最常见的根本原因、分析系统性的薄弱环节、找出事件之间的关联、并为每个根因提供具体的修复建议。",
  },
  {
    key: "deep",
    labelKey: "incidents.report.template.deep",
    icon: BeakerIcon,
    color: "text-purple-600 bg-purple-50 hover:bg-purple-100",
    promptEN:
      "Please perform a deep analysis including: risk assessment of each incident, impact scope analysis, improvement roadmap with priorities, and preventive measures that would reduce future incidents.",
    promptZH:
      "请进行深度分析，包括：每个事件的风险评估、影响范围分析、按优先级排序的改进路线图、以及能减少未来事件的预防措施。",
  },
];

interface ReportAIChatPanelProps {
  filterCel?: string;
  incidentIds?: string[];
}

export function ReportAIChatPanel({
  filterCel,
  incidentIds,
}: ReportAIChatPanelProps) {
  const { t } = useI18n();
  const locale = useLocale();
  const api = useApi();
  const { messages, setMessages } = useCopilotMessagesContext();
  const { runChatCompletion } = useCopilotChat();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [reportData, setReportData] = useState<any>(null);
  const [sendingPreset, setSendingPreset] = useState(false);

  const isZh = locale === "zh" || locale === "zh-CN";

  // Load incident data for context
  useEffect(() => {
    if (!api.isReady()) return;
    const fetchReportData = async () => {
      try {
        let data: Record<string, unknown>;
        if (incidentIds && incidentIds.length > 0) {
          data = await api.post(`/incidents/report`, {
            incident_ids: incidentIds,
            template_type: "comprehensive",
          });
        } else {
          let url = `/incidents/report`;
          if (filterCel) url += `?cel=${filterCel}`;
          data = await api.get(url);
        }
        setReportData(data);
      } catch (err) {
        console.error("Failed to load report data for AI chat:", err);
      }
    };
    fetchReportData();
  }, [api, filterCel, incidentIds]);

  // Persist messages to localStorage
  const storageKey = `copilotkit-messages-report-${filterCel || "all"}-${(incidentIds || []).slice(0, 3).join(",")}`;

  useEffect(() => {
    if (messages.length !== 0) {
      localStorage.setItem(storageKey, JSON.stringify(messages));
    }
  }, [messages, storageKey]);

  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        const parsed = JSON.parse(stored).map((message: Record<string, unknown>) => {
          if (message.type === "TextMessage") {
            return new TextMessage({
              id: message.id as string,
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              role: message.role as any,
              content: message.content as string,
              createdAt: message.createdAt as string,
            });
          } else if (message.type === "ActionExecutionMessage") {
            return new ActionExecutionMessage({
              id: message.id as string,
              name: message.name as string,
              scope: message.scope as string,
              arguments: message.arguments as Record<string, unknown>,
              createdAt: message.createdAt as string,
            });
          } else if (message.type === "ResultMessage") {
            return new ResultMessage({
              id: message.id as string,
              actionExecutionId: message.actionExecutionId as string,
              actionName: message.actionName as string,
              result: message.result as string,
              createdAt: message.createdAt as string,
            });
          }
          return null;
        });
        setMessages(parsed.filter(Boolean));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Provide incident data as readable context
  useCopilotReadable({
    description:
      "Incident report data including metrics, severity, services, durations, and AI analysis",
    value: reportData,
  });

  useCopilotReadable({
    description: "Filter condition (CEL expression) used to select incidents",
    value: filterCel,
  });

  useCopilotReadable({
    description: "Specific incident IDs selected for analysis",
    value: incidentIds,
  });

  // Action: Generate a focused analysis
  useCopilotAction({
    name: "generateFocusedAnalysis",
    description:
      "Generate a focused deep-dive analysis on a specific aspect of the incidents",
    parameters: [
      {
        name: "focusArea",
        type: "string",
        description:
          "The area to focus: 'root_cause', 'trend', 'risk', 'recommendations', or 'comprehensive'",
      },
      {
        name: "question",
        type: "string",
        description: "The specific question to explore",
      },
    ],
    handler: async ({ focusArea, question }: { focusArea: string; question: string }) => {
      try {
        const result = await api.post(`/incidents/report`, {
          incident_ids: incidentIds,
          cel: filterCel,
          template_type: focusArea === "comprehensive" ? "deep" : focusArea,
        });
        return result;
      } catch (err) {
        return `Error generating analysis: ${err}`;
      }
    },
  });

  // Handle preset prompt click
  const handlePresetClick = useCallback(
    (prompt: PresetPrompt) => {
      if (sendingPreset) return;
      setSendingPreset(true);
      const text = isZh ? prompt.promptZH : prompt.promptEN;
      const userMessage = new TextMessage({
        id: crypto.randomUUID(),
        role: MessageRole.User,
        content: text,
        createdAt: new Date().toISOString(),
      });
      setMessages([...messages, userMessage]);
      setTimeout(() => {
        runChatCompletion();
        setSendingPreset(false);
      }, 100);
    },
    [isZh, sendingPreset, messages, setMessages, runChatCompletion]
  );

  const handleSubmitMessage = useCallback((_message: string) => {
    // Track usage if needed
  }, []);

  const instructions = isZh
    ? REPORT_CHAT_INSTRUCTIONS_ZH
    : REPORT_CHAT_INSTRUCTIONS_EN;

  return (
    <div className="flex flex-col h-full">
      <style>{`
        .report-chat .copilotKitMessages {
          height: calc(85vh - 170px) !important;
          overflow-y: auto;
        }
        .report-chat .copilotKitInput {
          border-top: 1px solid #e2e8f0;
        }
      `}</style>
      {/* Preset prompt tabs */}
      <div className="flex items-center gap-2 px-4 pt-3 pb-2 border-b border-slate-100 bg-slate-50/30 flex-shrink-0">
        <span className="text-xs text-slate-400 mr-1 flex-shrink-0">
          {t("incidents.report.template.label")}:
        </span>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {PRESET_PROMPTS.map((prompt) => {
            const Icon = prompt.icon;
            return (
              <button
                key={prompt.key}
                onClick={() => handlePresetClick(prompt)}
                disabled={sendingPreset}
                type="button"
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap",
                  prompt.color,
                  sendingPreset
                    ? "opacity-50 cursor-not-allowed"
                    : "cursor-pointer"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t(prompt.labelKey)}</span>
              </button>
            );
          })}
        </div>
      </div>
      {/* Chat area */}
      <div className="flex-1 report-chat">
        <CopilotChat
          className="h-full"
          instructions={instructions}
          labels={{
            title: t("incidents.report.aiChat.title"),
            initial: t("incidents.report.aiChat.initialMessage"),
            placeholder: t("incidents.report.aiChat.placeholder"),
          }}
          onSubmitMessage={handleSubmitMessage}
        />
      </div>
    </div>
  );
}
