import json
import logging
import math
import os
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from keep.api.bl.ai_model_service import get_client, get_model_name
from keep.api.bl.incidents_bl import IncidentBl
from keep.api.models.db.incident import IncidentStatus
from keep.api.models.incident import IncidentDto
from keep.api.utils.ai_utils import get_ai_temperature_kwargs


class IncidentMetrics(BaseModel):
    total_incidents: Optional[int] = None
    resolved_incidents: Optional[int] = None
    deleted_incidents: Optional[int] = None
    unresolved_incidents: Optional[int] = None


class IncidentDurations(BaseModel):
    shortest_duration_seconds: Optional[int] = None
    shortest_duration_incident_id: Optional[str] = None
    longest_duration_seconds: Optional[int] = None
    longest_duration_incident_id: Optional[str] = None


class IncidentReportDto(BaseModel):
    incident_name: Optional[str] = None
    incident_id: Optional[str] = None


class ReoccuringIncidentReportDto(IncidentReportDto):
    occurrence_count: Optional[int] = None


class IncidentReport(BaseModel):
    services_affected_metrics: Optional[dict[str, int]] = None
    severity_metrics: Optional[dict[str, list[IncidentReportDto]]] = None
    incident_durations: Optional[IncidentDurations] = None
    mean_time_to_detect_seconds: Optional[int] = None
    mean_time_to_resolve_seconds: Optional[int] = None
    most_frequent_reasons: Optional[dict[str, list[str]]] = None
    recurring_incidents: Optional[list[ReoccuringIncidentReportDto]] = None
    # Enhanced report fields
    trend_analysis: Optional[str] = None
    root_cause_analysis: Optional[str] = None
    recommendations: Optional[list[str]] = None
    risk_assessment: Optional[str] = None
    template_type: Optional[str] = None  # comprehensive/trend/root_cause/deep


class OpenAIReportPart(BaseModel):
    most_frequent_reasons: Optional[dict[str, list[str]]] = None
    trend_analysis: Optional[str] = None
    root_cause_analysis: Optional[str] = None
    recommendations: Optional[list[str]] = None
    risk_assessment: Optional[str] = None


# ── Multi-template prompts ──────────────────────────────────────────────────

_PROMPTS_EN = {
    "comprehensive": """Generate a comprehensive incident report based on the provided incidents dataset. Return valid JSON with these fields:

1. **most_frequent_reasons** (object): Identify top 6 root causes by analyzing incident_name, incident_summary, severity. Try to find root causes not explicitly mentioned. Be concise but descriptive. Group similar reasons. Format: {"Reason 1": ["id1","id2"], "Reason 2": ["id3"]}

2. **trend_analysis** (string): Identify temporal patterns — time-of-day concentration, day-of-week patterns, frequency trends (increasing/decreasing/stable), seasonality. Be specific with time references.

3. **root_cause_analysis** (string): Deep analysis of root causes — categorize causes (infrastructure/code/config/external), identify dependencies and cascade effects, analyze severity-correlation with causes.

4. **recommendations** (array of strings): 3-5 actionable improvement suggestions prioritized by impact. Each should be specific and implementable.

5. **risk_assessment** (string): Assess current risk level (low/medium/high/critical) with justification. Identify potential future risks based on current patterns.""",

    "trend": """Analyze temporal trends in the provided incidents dataset. Return valid JSON with these fields:

1. **most_frequent_reasons** (object): Top 6 reasons. Format: {"Reason": ["id1","id2"]}
2. **trend_analysis** (string): Detailed temporal analysis — time-of-day patterns, day-of-week distribution, frequency trend direction, seasonality, burst detection, correlation between time and severity.
3. **recommendations** (array of strings): 3-5 suggestions specifically targeting time-based patterns (e.g., scaling schedules, on-call coverage, batch job timing).
4. **root_cause_analysis** (string): Brief — only if time patterns reveal root causes.
5. **risk_assessment** (string): Risk level based on trend trajectory.""",

    "root_cause": """Perform root cause analysis on the provided incidents dataset. Return valid JSON with these fields:

1. **most_frequent_reasons** (object): Top 6 root causes with incident IDs. Format: {"Root Cause": ["id1","id2"]}
2. **root_cause_analysis** (string): Comprehensive root cause analysis — categorize causes, identify cascade effects, map service-to-cause relationships, analyze severity per cause category.
3. **recommendations** (array of strings): 3-5 targeted fixes for identified root causes.
4. **trend_analysis** (string): Brief — only if trends help explain root causes.
5. **risk_assessment** (string): Risk assessment focused on root cause recurrence probability.""",

    "deep": """Perform deep analysis on the provided incidents dataset. Return valid JSON with ALL fields fully populated:

1. **most_frequent_reasons** (object): Top 6 reasons with IDs. Format: {"Reason": ["id1","id2"]}
2. **trend_analysis** (string): Complete temporal analysis — patterns, seasonality, anomalies, predictions.
3. **root_cause_analysis** (string): Exhaustive root cause analysis — categorization, cascade mapping, service dependencies, severity correlation.
4. **recommendations** (array of strings): 5-8 prioritized actionable recommendations with estimated impact.
5. **risk_assessment** (string): Detailed risk matrix — current risk level, future risk projection, worst-case scenarios, mitigation priority.""",
}

_PROMPTS_ZH = {
    "comprehensive": """根据提供的事件数据集生成综合事件报告。返回合法 JSON，包含以下字段：

1. **most_frequent_reasons** (对象)：通过分析 incident_name、incident_summary、severity 识别前 6 个根本原因。尝试找出未明确提及的原因。简洁但有描述性。对相似原因分组。格式：{"原因 1": ["id1","id2"], "原因 2": ["id3"]}

2. **trend_analysis** (字符串)：识别时间模式——时段集中、星期分布、频率趋势（上升/下降/稳定）、季节性。引用具体时间。

3. **root_cause_analysis** (字符串)：根因深度分析——将原因分类（基础设施/代码/配置/外部），识别依赖链和级联效应，分析严重程度与原因的关联。

4. **recommendations** (字符串数组)：3-5 条按影响优先级排列的可执行改进建议。每条应具体可落地。

5. **risk_assessment** (字符串)：评估当前风险等级（低/中/高/严重）并说明理由。基于当前模式识别未来潜在风险。""",

    "trend": """分析事件数据集中的时间趋势。返回合法 JSON，包含以下字段：

1. **most_frequent_reasons** (对象)：前 6 个原因。格式：{"原因": ["id1","id2"]}
2. **trend_analysis** (字符串)：详细时间分析——时段模式、星期分布、频率趋势方向、季节性、突发检测、时间与严重程度的关联。
3. **recommendations** (字符串数组)：3-5 条针对时间模式的建议（如扩缩容计划、on-call 覆盖、批处理调度）。
4. **root_cause_analysis** (字符串)：简要——仅在时间模式揭示根因时展开。
5. **risk_assessment** (字符串)：基于趋势走向的风险评估。""",

    "root_cause": """对事件数据集执行根因分析。返回合法 JSON，包含以下字段：

1. **most_frequent_reasons** (对象)：前 6 个根因及事件 ID。格式：{"根因": ["id1","id2"]}
2. **root_cause_analysis** (字符串)：全面的根因分析——原因分类、级联效应、服务与原因映射、各原因类别的严重程度分析。
3. **recommendations** (字符串数组)：3-5 条针对识别到的根因的修复建议。
4. **trend_analysis** (字符串)：简要——仅在趋势有助于解释根因时展开。
5. **risk_assessment** (字符串)：聚焦于根因复发概率的风险评估。""",

    "deep": """对事件数据集执行深度分析。返回合法 JSON，所有字段需完整填充：

1. **most_frequent_reasons** (对象)：前 6 个原因及 ID。格式：{"原因": ["id1","id2"]}
2. **trend_analysis** (字符串)：完整时间分析——模式、季节性、异常、预测。
3. **root_cause_analysis** (字符串)：详尽的根因分析——分类、级联映射、服务依赖、严重程度关联。
4. **recommendations** (字符串数组)：5-8 条按优先级排列的可执行建议，附预期影响评估。
5. **risk_assessment** (字符串)：详细风险矩阵——当前风险等级、未来风险预测、最坏场景、缓解优先级。
""",
}


def _get_system_prompt(template_type: str, locale: str = "") -> str:
    use_chinese = locale in ("zh_CN", "zh")
    prompts = _PROMPTS_ZH if use_chinese else _PROMPTS_EN
    return prompts.get(template_type, prompts["comprehensive"])

logger = logging.getLogger(__name__)


class IncidentReportsBl:

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.incidents_bl = IncidentBl(
            tenant_id=tenant_id, session=None, pusher_client=None, user=None
        )

    def get_incident_reports(
        self,
        incidents_query_cel: str,
        allowed_incident_ids: list[str],
        incident_ids: Optional[List[str]] = None,
        template_type: str = "comprehensive",
    ) -> IncidentReport:
        incidents = self.__get_incidents(
            incidents_query_cel, allowed_incident_ids, incident_ids
        )
        open_ai_report_part = self.__calculate_report_in_openai(
            incidents, template_type=template_type
        )
        report = IncidentReport(
            most_frequent_reasons=open_ai_report_part.most_frequent_reasons
            if open_ai_report_part
            else None,
            trend_analysis=open_ai_report_part.trend_analysis
            if open_ai_report_part
            else None,
            root_cause_analysis=open_ai_report_part.root_cause_analysis
            if open_ai_report_part
            else None,
            recommendations=open_ai_report_part.recommendations
            if open_ai_report_part
            else None,
            risk_assessment=open_ai_report_part.risk_assessment
            if open_ai_report_part
            else None,
            template_type=template_type,
        )
        incidents_dict = {incident.id: incident for incident in incidents}
        resolved_incidents = [
            incident
            for incident in incidents
            if incident.status == IncidentStatus.RESOLVED
        ]
        report.mean_time_to_detect_seconds = self.__calculate_mttd(incidents)
        report.mean_time_to_resolve_seconds = self.__calculate_mttr(resolved_incidents)
        report.incident_durations = self.__calculate_durations(resolved_incidents)
        report.recurring_incidents = self.__calculate_recurring_incidents(
            incidents_dict
        )
        report.severity_metrics = self.__calculate_severity_metrics(incidents)
        report.services_affected_metrics = self.__calculate_top_services_affected(
            incidents
        )

        return report

    def __calculate_report_in_openai(
        self, incidents: list[IncidentDto], template_type: str = "comprehensive"
    ) -> OpenAIReportPart:
        try:
            open_ai_client = get_client(self.tenant_id)
        except (ValueError, Exception) as e:
            logger.warning(f"AI service not configured for report scenario: {e}")
            return OpenAIReportPart()

        # Most recent incidents first
        incidents = sorted(incidents, key=lambda x: x.creation_time, reverse=True)

        # Limit incidents because OpenAI is either slow (timeouts) or has token limits
        incidents = incidents[:40]

        incidents_minified: list[dict] = []
        for item in incidents:
            incidents_minified.append(
                {
                    "incident_id": str(item.id),
                    "incident_name": "\n".join(
                        filter(None, [item.user_generated_name, item.ai_generated_name])
                    ),
                    "incident_summary": "\n".join(
                        filter(None, [item.user_summary, item.generated_summary])
                    ),
                    "severity": item.severity,
                    "services": item.services,
                }
            )

        incidents_json = json.dumps(incidents_minified, default=str)

        # Select prompt based on locale and template type
        locale = os.environ.get("KEEP_DEFAULT_LOCALE", "zh_CN")
        selected_prompt = _get_system_prompt(template_type, locale)

        # Only add response_format for OpenAI API; many compatible APIs don't support json_schema
        base_url_str = str(open_ai_client.base_url) if open_ai_client.base_url else ""
        kwargs: dict = {
            "model": get_model_name(self.tenant_id),
            "messages": [
                {"role": "system", "content": selected_prompt},
                {"role": "user", "content": incidents_json},
            ],
            "seed": 1239,
            **get_ai_temperature_kwargs(0.2),
        }
        if "api.openai.com" in base_url_str:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "OpenAIReportPart",
                    "schema": OpenAIReportPart.schema(),
                },
            }
        response = open_ai_client.chat.completions.create(**kwargs)

        model_response = response.choices[0].message.content
        if not model_response:
            logger.error("LLM returned empty response")
            return OpenAIReportPart()
        try:
            # Extract JSON from markdown code fences using regex (more robust)
            import re
            # Try to find JSON between ```json and ``` or just between ``` and ```
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', model_response, re.DOTALL)
            if json_match:
                stripped = json_match.group(1).strip()
            else:
                # No markdown fences, use the raw response
                stripped = model_response.strip()
            if not stripped:
                logger.error("LLM response empty after stripping markdown")
                return OpenAIReportPart()
            report = OpenAIReportPart(**json.loads(stripped))
            return report
        except Exception as e:
            logger.error(
                f"Failed to parse OpenAI response: {e}, Response: {model_response}"
            )
            raise e

    def __calculate_top_services_affected(
        self, incidents: list[IncidentDto]
    ) -> dict[str, int]:
        top_services_affected = {}
        for incident in incidents:
            for service in incident.services:
                if service == "null":
                    continue
                if service not in top_services_affected:
                    top_services_affected[service] = 0
                top_services_affected[service] += 1

        return top_services_affected

    def __calculate_severity_metrics(
        self, incidents: list[IncidentDto]
    ) -> dict[str, list[IncidentReportDto]]:
        severity_metrics: dict[str, list[IncidentReportDto]] = {}
        for incident in incidents:
            severity_key = str(incident.severity)
            if severity_key not in severity_metrics:
                severity_metrics[severity_key] = []
            severity_metrics[severity_key].append(
                IncidentReportDto(
                    incident_name=incident.user_generated_name
                    or incident.ai_generated_name,
                    incident_id=str(incident.id),
                )
            )

        return severity_metrics

    def __calculate_mttd(self, incidents: list[IncidentDto]) -> int:
        duration_sum = 0
        incidents_count = 0

        for incident in incidents:
            if not incident.start_time:
                continue

            duration_sum += (
                incident.creation_time - incident.start_time
            ).total_seconds()
            incidents_count += 1

        if incidents_count == 0:
            return 0

        return math.ceil(duration_sum / incidents_count)

    def __calculate_mttr(self, resolved_incidents: list[IncidentDto]) -> int:
        filtered_incidents = [
            incident for incident in resolved_incidents if incident.end_time
        ]

        if len(filtered_incidents) == 0:
            return 0

        duration_sum = 0
        for incident in filtered_incidents:
            start_time = incident.start_time or incident.creation_time
            duration_sum += (incident.end_time - start_time).total_seconds()

        return math.ceil(duration_sum / len(filtered_incidents))

    def __calculate_durations(
        self, resolved_incidents: list[IncidentDto]
    ) -> IncidentDurations:
        if len(resolved_incidents) == 0:
            return None

        shortest_duration_ms = None
        shortest_duration_incident_id = None
        longest_duration_ms = None
        longest_duration_incident_id = None

        for incident in resolved_incidents:
            start_time = incident.start_time or incident.creation_time
            if not start_time or not incident.end_time:
                continue

            duration = (incident.end_time - start_time).total_seconds()
            if not shortest_duration_ms or duration < shortest_duration_ms:
                shortest_duration_ms = duration
                shortest_duration_incident_id = incident.id

            if not longest_duration_ms or duration > longest_duration_ms:
                longest_duration_ms = duration
                longest_duration_incident_id = incident.id

        return IncidentDurations(
            shortest_duration_seconds=shortest_duration_ms,
            shortest_duration_incident_id=str(shortest_duration_incident_id),
            longest_duration_seconds=longest_duration_ms,
            longest_duration_incident_id=str(longest_duration_incident_id),
        )

    def __calculate_recurring_incidents(
        self, incidents_dict: dict[UUID, IncidentDto]
    ) -> list[ReoccuringIncidentReportDto]:
        recurring_incidents: dict[str, set[str]] = {}
        for incident in incidents_dict.values():
            current_incident_in_the_past_id = incident.same_incident_in_the_past_id
            path = list([incident.id])
            while current_incident_in_the_past_id:
                path.append(current_incident_in_the_past_id)
                past_incident = same_incident_in_the_past_id = incidents_dict.get(
                    current_incident_in_the_past_id, None
                )

                if not past_incident:
                    break

                same_incident_in_the_past_id = (
                    past_incident.same_incident_in_the_past_id
                )

                if not same_incident_in_the_past_id:
                    root_incident_id = path[-1]

                    if root_incident_id not in recurring_incidents:
                        recurring_incidents[root_incident_id] = set()

                    for incident_id in path:
                        recurring_incidents[root_incident_id].add(incident_id)
                    break

                current_incident_in_the_past_id = (
                    past_incident.same_incident_in_the_past_id
                )

        return [
            ReoccuringIncidentReportDto(
                incident_name=incidents_dict[root_incident_id].user_generated_name
                or incidents_dict[root_incident_id].ai_generated_name,
                incident_id=str(root_incident_id),
                occurrence_count=len(recurring_incidents),
            )
            for root_incident_id, recurring_incidents in recurring_incidents.items()
        ]

    def __get_incidents(
        self,
        incidents_query_cel: str,
        allowed_incident_ids: list[str],
        incident_ids: Optional[List[str]] = None,
    ) -> list[IncidentDto]:
        # When incident_ids are provided directly, use them instead of CEL
        if incident_ids:
            if not incident_ids:
                return []
            # Build CEL expression: id == 'uuid1' || id == 'uuid2' || ...
            id_expressions = " || ".join([f"id == '{uid}'" for uid in incident_ids])
            query_cel = f"status != 'deleted' && ({id_expressions})"
        else:
            query_cel = f"status != 'deleted' && {incidents_query_cel}"
        query_result = self.incidents_bl.query_incidents(
            tenant_id=self.tenant_id,
            cel=query_cel,
            limit=100,
            offset=0,
            allowed_incident_ids=allowed_incident_ids,
            is_candidate=False,
        )
        return query_result.items
