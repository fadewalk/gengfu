"use client";

import {
  useCopilotAction,
  useCopilotReadable,
  useCopilotChatInternal,
} from "@copilotkit/react-core";
import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useI18n } from "@/i18n/hooks/useI18n";
import { useLocale } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  DocumentChartBarIcon,
  ArrowTrendingUpIcon,
  MagnifyingGlassIcon,
  BeakerIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  WrenchScrewdriverIcon,
  UserIcon,
  ClockIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { IncidentsReport } from "./incidents-report";
import type { IncidentData, ReportTemplateType } from "./models";

const REPORT_CHAT_INSTRUCTIONS_EN = `You are an expert incident analyst. The user wants to explore incidents interactively.

Your capabilities:
- Analyze incident patterns, trends, and root causes
- Compare incidents and identify recurring issues
- Suggest improvements and preventive measures
- Assess risk levels and potential impact
- Query incidents by time range, severity, or category using the queryIncidents action when the user asks about specific aspects

Rules:
- DO NOT make up any information. Use only the data provided.
- Be concise and actionable.
- When suggesting analysis, reference specific incidents by name or ID.
- If you need more context, ask the user.
- Always respond in the same language as the user's question.`;

const REPORT_CHAT_INSTRUCTIONS_ZH = `你是一个专业的事件分析师。用户希望通过对话来深入探索事件。

你的能力：
- 分析事件模式、趋势和根因
- 比较事件并识别重复出现的问题
- 提出改进建议和预防措施
- 评估风险等级和潜在影响
- 当用户询问特定方面时，可使用 queryIncidents 工具按时间段、严重程度或类别查询事件

规则：
- 不要编造任何信息，只使用提供的数据
- 回答要简洁、有针对性
- 在建议分析时，引用具体的事件名称或 ID
- 如果需要更多上下文，请向用户提问
- 始终用与用户提问相同的语言回答`;

/** Preset prompt definitions */
interface PresetPrompt {
  key: ReportTemplateType;
  labelKey: string;
  icon: React.ElementType;
  color: string;
}

const PRESET_PROMPTS: PresetPrompt[] = [
  {
    key: "comprehensive",
    labelKey: "incidents.report.template.comprehensive",
    icon: DocumentChartBarIcon,
    color: "text-blue-600 bg-blue-50 hover:bg-blue-100",
  },
  {
    key: "trend",
    labelKey: "incidents.report.template.trend",
    icon: ArrowTrendingUpIcon,
    color: "text-green-600 bg-green-50 hover:bg-green-100",
  },
  {
    key: "root_cause",
    labelKey: "incidents.report.template.rootCause",
    icon: MagnifyingGlassIcon,
    color: "text-orange-600 bg-orange-50 hover:bg-orange-100",
  },
  {
    key: "deep",
    labelKey: "incidents.report.template.deep",
    icon: BeakerIcon,
    color: "text-purple-600 bg-purple-50 hover:bg-purple-100",
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
  const isZh = locale === "zh" || locale === "zh-CN";
  const instructions = isZh
    ? REPORT_CHAT_INSTRUCTIONS_ZH
    : REPORT_CHAT_INSTRUCTIONS_EN;

  const {
    messages: chatMessages,
    appendMessage,
    isLoading,
    isAvailable,
  } = useCopilotChatInternal();
  const messages = chatMessages ?? [];

  // Session ID for this report chat (stable per user)
  const sessionId = "incident-report-chat";

  // Persist messages to backend on change
  const lastSavedCount = useRef(0);
  useEffect(() => {
    if (messages.length === 0 || messages.length <= lastSavedCount.current) return;
    lastSavedCount.current = messages.length;
    const serialized = messages.map((m) => {
      const msg = m as unknown as Record<string, unknown>;
      return {
        session_id: sessionId,
        role: msg.role as string,
        content: msg.content as string,
      };
    });
    // Fire-and-forget save (only new messages since last save)
    api.post(`/incidents/chat/messages`, {
      session_id: sessionId,
      messages: serialized,
    }).catch(() => {
      // ignore save errors
    });
  }, [messages, api, sessionId]);

  // Restore messages from backend on mount
  const [restoredMessages, setRestoredMessages] = useState<
    { id: string; role: string; content: string; createdAt?: string }[]
  >([]);
  useEffect(() => {
    if (!api.isReady()) return;
    api.get(`/incidents/chat/messages?session_id=${sessionId}&limit=200`)
      .then((data: { id: string; role: string; content: string; createdAt?: string }[]) => {
        setRestoredMessages(data);
        lastSavedCount.current = data.length;
      })
      .catch(() => {
        // ignore load errors
      });
  }, [api, sessionId]);

  // Structured report from backend API (fixed format)
  const [activeReport, setActiveReport] = useState<IncidentData | null>(null);
  const [activeTemplateType, setActiveTemplateType] =
    useState<ReportTemplateType | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [reportCollapsed, setReportCollapsed] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(true);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [reportData, setReportData] = useState<any>(null);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Load incident data for AI context (lightweight, no template_type)
  useEffect(() => {
    if (!api.isReady()) return;
    const fetchReportData = async () => {
      try {
        const data = await api.post(`/incidents/report`, {
          incident_ids: incidentIds?.length ? incidentIds : undefined,
          cel: filterCel || undefined,
          template_type: "comprehensive",
        });
        setReportData(data);
      } catch (err) {
        console.error("Failed to load report data for AI chat:", err);
      }
    };
    fetchReportData();
  }, [api, filterCel, incidentIds]);

  // System instructions as readable context
  useCopilotReadable({
    description: "AI assistant system instructions",
    value: instructions,
  });

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

  // Action: Query incidents with custom filters (for AI auto-query)
  useCopilotAction({
    name: "queryIncidents",
    description:
      "Query incidents with custom CEL filter expression to analyze specific time ranges, severities, or categories. Returns structured incident report data.",
    parameters: [
      {
        name: "celFilter",
        type: "string",
        description:
          "CEL expression to filter incidents, e.g. 'severity == \"critical\"', 'creation_time > now() - duration(\"7d\")', or combined expressions",
      },
      {
        name: "analysisType",
        type: "string",
        description:
          "Type of analysis: 'comprehensive', 'trend', 'root_cause', or 'deep'",
      },
    ],
    handler: async ({
      celFilter,
      analysisType,
    }: {
      celFilter: string;
      analysisType: string;
    }) => {
      try {
        const result = await api.post(`/incidents/report`, {
          cel: celFilter,
          template_type: analysisType || "comprehensive",
        });
        return result;
      } catch (err) {
        return `Error querying incidents: ${err}`;
      }
    },
  });

  // Action: Generate a focused analysis (legacy, kept for compatibility)
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
    handler: async ({
      focusArea,
      question,
    }: {
      focusArea: string;
      question: string;
    }) => {
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

  // Send a user message and trigger AI completion
  const sendMessage = useCallback(
    async (text: string) => {
      if (!isAvailable) return;
      const userMessage = new TextMessage({
        id: crypto.randomUUID(),
        role: MessageRole.User,
        content: text,
        createdAt: new Date().toISOString(),
      });
      try {
        await appendMessage(userMessage);
      } catch (err) {
        console.error("[ReportAIChat] appendMessage failed:", err);
      }
    },
    [appendMessage, isAvailable]
  );

  // Handle preset tab click — call backend API for fixed-format report
  const handlePresetClick = useCallback(
    async (prompt: PresetPrompt) => {
      if (isLoadingReport || isLoading) return;
      const templateType = prompt.key;
      setActiveTemplateType(templateType);
      setIsLoadingReport(true);
      setActiveReport(null);
      setReportCollapsed(false);
      try {
        const data = await api.post(`/incidents/report`, {
          incident_ids: incidentIds?.length ? incidentIds : undefined,
          cel: filterCel || undefined,
          template_type: templateType,
        });
        setActiveReport(data);
        setReportData(data);
      } catch (err) {
        console.error("Failed to generate report:", err);
      } finally {
        setIsLoadingReport(false);
      }
    },
    [api, filterCel, incidentIds, isLoadingReport, isLoading]
  );

  // Handle textarea submit
  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isLoading) return;
    sendMessage(inputValue.trim());
    setInputValue("");
  }, [inputValue, isLoading, sendMessage]);

  // Enter to submit, Shift+Enter for newline
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  // Render each message
  const renderMessage = (
    message: (typeof messages)[0],
    index: number
  ): React.ReactNode => {
    const msg = message as unknown as Record<string, unknown>;
    const role = msg.role as string;
    const isUser = role === "user";
    const content = msg.content as string;
    const msgId = (msg.id as string) || `msg-${index}`;

    // Check if this is a tool call message
    const hasToolCall = !!msg.toolCall || !!msg.function_call;

    if (role === "assistant" && hasToolCall) {
      const toolName =
        ((msg.toolCall as Record<string, unknown>)?.name as string) ||
        ((msg.function_call as Record<string, unknown>)?.name as string) ||
        "";
      return (
        <div key={msgId} className="flex justify-start gap-2.5">
          <div className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <WrenchScrewdriverIcon className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 text-xs text-amber-700 flex items-center gap-1.5">
            <span className="animate-pulse">●</span>
            <span className="font-medium">
              {toolName === "generateFocusedAnalysis" ||
              toolName === "queryIncidents"
                ? isZh
                  ? "正在查询事件数据..."
                  : "Querying incidents..."
                : `${toolName}...`}
            </span>
          </div>
        </div>
      );
    }

    if (isUser || (role === "assistant" && content)) {
      return (
        <div
          key={msgId}
          className={clsx(
            "flex gap-2.5",
            isUser ? "justify-end" : "justify-start"
          )}
        >
          {!isUser && (
            <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
              <SparklesIcon className="w-3.5 h-3.5 text-blue-600" />
            </div>
          )}
          <div
            className={clsx(
              "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
              isUser
                ? "bg-blue-600 text-white rounded-br-sm"
                : "bg-slate-100 text-slate-800 rounded-bl-sm"
            )}
          >
            <div className="whitespace-pre-wrap break-words">{content}</div>
          </div>
          {isUser && (
            <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 mt-0.5">
              <UserIcon className="w-3.5 h-3.5 text-slate-500" />
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  const templateLabels: Record<string, string> = {
    comprehensive: isZh ? "综合报告" : "Comprehensive Report",
    trend: isZh ? "趋势分析" : "Trend Analysis",
    root_cause: isZh ? "根因分析" : "Root Cause Analysis",
    deep: isZh ? "深度分析" : "Deep Analysis",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Preset prompt tabs */}
      <div className="flex items-center gap-2 px-4 pt-3 pb-2 border-b border-slate-100 bg-slate-50/30 flex-shrink-0">
        <span className="text-xs text-slate-400 mr-1 flex-shrink-0">
          {t("incidents.report.template.label")}:
        </span>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {PRESET_PROMPTS.map((prompt) => {
            const Icon = prompt.icon;
            const isActive = activeTemplateType === prompt.key;
            return (
              <button
                key={prompt.key}
                onClick={() => handlePresetClick(prompt)}
                disabled={isLoadingReport || isLoading}
                type="button"
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap",
                  prompt.color,
                  isLoadingReport || isLoading
                    ? "opacity-50 cursor-not-allowed"
                    : "cursor-pointer",
                  isActive && "ring-2 ring-offset-1 ring-blue-400"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t(prompt.labelKey)}</span>
                {isLoadingReport && isActive && (
                  <span className="animate-spin inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
                )}
              </button>
            );
          })}
          {/* Chat history button */}
          {restoredMessages.length > 0 && (
            <button
              type="button"
              onClick={() => setHistoryCollapsed(!historyCollapsed)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap ml-auto cursor-pointer transition-all",
                historyCollapsed
                  ? "text-slate-500 bg-slate-100 hover:bg-slate-200"
                  : "text-blue-600 bg-blue-50 hover:bg-blue-100"
              )}
            >
              <ClockIcon className="w-3.5 h-3.5" />
              <span>{isZh ? "历史记录" : "History"}</span>
              <span className={clsx(
                "rounded-full px-1.5 py-0.5 text-[10px] leading-none",
                historyCollapsed ? "bg-slate-300 text-white" : "bg-blue-200 text-blue-700"
              )}>
                {restoredMessages.length}
              </span>
              <button
                type="button"
                onClick={async (e) => {
                  e.stopPropagation();
                  if (!api.isReady()) return;
                  try {
                    await api.delete(`/incidents/chat/messages?session_id=${sessionId}`);
                    setRestoredMessages([]);
                    lastSavedCount.current = 0;
                  } catch {
                    // ignore
                  }
                }}
                className="p-0.5 rounded hover:bg-red-100 cursor-pointer"
                title={isZh ? "清空历史" : "Clear history"}
              >
                <TrashIcon className="w-3 h-3 text-slate-400 hover:text-red-500" />
              </button>
            </button>
          )}
        </div>
      </div>

      {/* Scrollable content area: report card + chat messages */}
      <div className="flex-1 overflow-y-auto">
        {/* Structured report card (fixed format) */}
        {activeReport && activeTemplateType && (
          <div className="border-b border-slate-200">
            <div className="flex items-center justify-between px-4 py-2 bg-slate-50">
              <span className="text-xs font-medium text-slate-600">
                {templateLabels[activeTemplateType] || activeTemplateType}
              </span>
              <button
                type="button"
                onClick={() => setReportCollapsed(!reportCollapsed)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                {reportCollapsed
                  ? isZh
                    ? "展开"
                    : "Expand"
                  : isZh
                    ? "收起"
                    : "Collapse"}
              </button>
            </div>
            {!reportCollapsed && (
              <div className="max-h-[60vh] overflow-y-auto">
                <IncidentsReport
                  incidentsReportData={activeReport}
                  filterCel={filterCel}
                  generatedAt={new Date()}
                  templateType={activeTemplateType}
                />
              </div>
            )}
          </div>
        )}

        {/* Chat messages */}
        <div className="px-4 py-4 space-y-3">
          {/* History section (collapsible) */}
          {restoredMessages.length > 0 && !historyCollapsed && (
            <div className="border border-slate-200 rounded-xl bg-slate-50/50 overflow-hidden">
              <div className="flex items-center justify-between px-3 py-1.5 bg-slate-100/80">
                <span className="text-[11px] font-medium text-slate-500">
                  {isZh ? `历史记录 (${restoredMessages.length}条)` : `History (${restoredMessages.length} messages)`}
                </span>
              </div>
              <div className="px-3 py-2 space-y-2 max-h-[40vh] overflow-y-auto">
                {restoredMessages.map((msg, i) =>
                  renderMessage(msg as unknown as (typeof messages)[0], i)
                )}
              </div>
            </div>
          )}

          {/* Current session messages */}
          {messages.length === 0 &&
            restoredMessages.length === 0 &&
            !isLoading &&
            !activeReport && (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 opacity-60">
              <SparklesIcon className="w-10 h-10 text-slate-300 mb-3" />
              <p className="text-sm text-slate-500 max-w-md">
                {t("incidents.report.aiChat.initialMessage")}
              </p>
            </div>
          )}
          {messages.length > 0
            ? messages.map((msg, i) => renderMessage(msg, i))
            : (restoredMessages.length === 0 || !historyCollapsed) && restoredMessages.map((msg, i) =>
                renderMessage(msg as unknown as (typeof messages)[0], i)
              )}
          {isLoading && (
            <div className="flex justify-start gap-2.5">
              <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <SparklesIcon className="w-3.5 h-3.5 text-blue-600" />
              </div>
              <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 border-t border-slate-200 px-3 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("incidents.report.aiChat.placeholder")}
            disabled={isLoading}
            rows={1}
            className="flex-1 resize-none max-h-[120px] rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSubmit}
            disabled={!inputValue.trim() || isLoading}
            type="button"
            aria-label={t("incidents.report.aiChat.placeholder")}
            className={clsx(
              "rounded-xl p-2.5 transition-all flex-shrink-0",
              inputValue.trim() && !isLoading
                ? "bg-blue-600 text-white hover:bg-blue-700 cursor-pointer"
                : "bg-slate-100 text-slate-400 cursor-not-allowed"
            )}
          >
            <PaperAirplaneIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
