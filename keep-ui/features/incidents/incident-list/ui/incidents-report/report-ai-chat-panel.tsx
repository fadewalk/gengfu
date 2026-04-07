"use client";

import {
  useCopilotAction,
  useCopilotReadable,
  useCopilotChatInternal,
} from "@copilotkit/react-core";
import {
  TextMessage,
  MessageRole,
} from "@copilotkit/runtime-client-gql";
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
} from "@heroicons/react/24/outline";

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
  const isZh = locale === "zh" || locale === "zh-CN";
  const instructions = isZh
    ? REPORT_CHAT_INSTRUCTIONS_ZH
    : REPORT_CHAT_INSTRUCTIONS_EN;

  const { messages: chatMessages, appendMessage, isLoading, isAvailable } = useCopilotChatInternal();
  const messages = chatMessages ?? [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [reportData, setReportData] = useState<any>(null);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

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
      try {
        const serializable = messages.map((msg) => {
          const m = msg as unknown as Record<string, unknown>;
          return {
            id: m.id,
            role: m.role,
            content: m.content,
          };
        });
        localStorage.setItem(
          storageKey,
          JSON.stringify(serializable.filter(Boolean))
        );
      } catch {
        // Ignore serialization errors
      }
    }
  }, [messages, storageKey]);

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
      if (!isAvailable) {
        console.warn("[ReportAIChat] Agent not available, skipping send");
        return;
      }
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

  // Handle preset tab click
  const handlePresetClick = useCallback(
    (prompt: PresetPrompt) => {
      if (isLoading) return;
      const text = isZh ? prompt.promptZH : prompt.promptEN;
      sendMessage(text);
    },
    [isZh, isLoading, sendMessage]
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
    // AG-UI messages use role: "user" | "assistant"
    // Tool call messages have role: "assistant" and a toolCall or function_call field
    const msg = message as unknown as Record<string, unknown>;
    const role = msg.role as string;
    const isUser = role === "user";
    const content = msg.content as string;
    const msgId = (msg.id as string) || `msg-${index}`;

    // Check if this is a tool call message (has toolCall or function_call)
    const hasToolCall =
      !!msg.toolCall ||
      !!msg.function_call;

    // Render tool call messages as "generating analysis" indicator
    if (role === "assistant" && hasToolCall) {
      const toolName =
        (msg.toolCall as Record<string, unknown>)?.name as string ||
        (msg.function_call as Record<string, unknown>)?.name as string ||
        "";
      return (
        <div
          key={msgId}
          className="flex justify-start gap-2.5"
        >
          <div className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <WrenchScrewdriverIcon className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 text-xs text-amber-700 flex items-center gap-1.5">
            <span className="animate-pulse">●</span>
            <span className="font-medium">
              {toolName === "generateFocusedAnalysis"
                ? isZh
                  ? "正在生成分析..."
                  : "Generating analysis..."
                : `${toolName}...`}
            </span>
          </div>
        </div>
      );
    }

    // Render text messages (user or assistant)
    if (isUser || (role === "assistant" && content)) {
      return (
        <div
          key={msgId}
          className={clsx("flex gap-2.5", isUser ? "justify-end" : "justify-start")}
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
            <div className="whitespace-pre-wrap break-words">
              {content}
            </div>
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
            return (
              <button
                key={prompt.key}
                onClick={() => handlePresetClick(prompt)}
                disabled={isLoading}
                type="button"
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap",
                  prompt.color,
                  isLoading
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

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center p-8 opacity-60">
            <SparklesIcon className="w-10 h-10 text-slate-300 mb-3" />
            <p className="text-sm text-slate-500 max-w-md">
              {t("incidents.report.aiChat.initialMessage")}
            </p>
          </div>
        )}
        {messages.map((msg, i) => renderMessage(msg, i))}
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
