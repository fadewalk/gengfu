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
  ResultMessage,
  TextMessage,
} from "@copilotkit/runtime-client-gql";
import { useApi } from "@/shared/lib/hooks/useApi";
import { useI18n } from "@/i18n/hooks/useI18n";
import { useLocale } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { toast } from "react-toastify";
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
  const [reportData, setReportData] = useState<any>(null);

  // Load incident data for context
  useEffect(() => {
    if (!api.isReady()) return;
    const fetchReportData = async () => {
      try {
        let data: any;
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
        const parsed = JSON.parse(stored).map((message: any) => {
          if (message.type === "TextMessage") {
            return new TextMessage({
              id: message.id,
              role: message.role,
              content: message.content,
              createdAt: message.createdAt,
            });
          } else if (message.type === "ActionExecutionMessage") {
            return new ActionExecutionMessage({
              id: message.id,
              name: message.name,
              scope: message.scope,
              arguments: message.arguments,
              createdAt: message.createdAt,
            });
          } else if (message.type === "ResultMessage") {
            return new ResultMessage({
              id: message.id,
              actionExecutionId: message.actionExecutionId,
              actionName: message.actionName,
              result: message.result,
              createdAt: message.createdAt,
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
    description: "Incident report data including metrics, severity, services, durations, and AI analysis",
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

  // Action: Generate a focused analysis on a specific aspect
  useCopilotAction({
    name: "generateFocusedAnalysis",
    description:
      "Generate a focused deep-dive analysis on a specific aspect of the incidents (e.g., root cause, trend, risk, recommendations). Returns a structured analysis.",
    parameters: [
      {
        name: "focusArea",
        type: "string",
        description:
          "The area to focus the analysis on: 'root_cause', 'trend', 'risk', 'recommendations', or 'comprehensive'",
      },
      {
        name: "question",
        type: "string",
        description: "The specific question or angle the user wants to explore",
      },
    ],
    handler: async ({ focusArea, question }) => {
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

  const handleSubmitMessage = useCallback((_message: string) => {
    // Track usage if needed
  }, []);

  const instructions =
    locale === "zh" || locale === "zh-CN"
      ? REPORT_CHAT_INSTRUCTIONS_ZH
      : REPORT_CHAT_INSTRUCTIONS_EN;

  return (
    <div className="flex flex-col h-full">
      <style>{`
        .report-chat .copilotKitMessages {
          height: calc(85vh - 120px) !important;
          overflow-y: auto;
        }
        .report-chat .copilotKitInput {
          border-top: 1px solid #e2e8f0;
        }
      `}</style>
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
