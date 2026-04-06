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


class OpenAIReportPart(BaseModel):
    most_frequent_reasons: Optional[dict[str, list[str]]] = None


system_prompt = """
Generate an incident report based on the provided incidents dataset and response schema. Ensure all calculated metrics follow the specified format for consistency.

**Calculations and Metrics:**
1. **Most Frequent Incident Reasons**
   - JSON property name: most_frequent_reasons
   - Identify the most common root causes by analyzing the following fields: incident_name, incident_summary, severity.
   - Try to find root causes that are not explicitly mentioned in the dataset.
   - Be concise, the reasons must be short but descriptive at the same time.
   - Group similar reasons to avoid duplicates.
   - Output only top 6 reasons.
   - Return a JSON object, which is a dictionary.
   - Each key in this dictionary must be an incident reason (a string describing the reason for the incident).
   - The value for each key must be a list of incident IDs (strings) that correspond to that reason.
   - The structure of object in most_frequent_reasons property should follow this exact format:
            {
                "Reason 1": ["incident_id_1", "incident_id_2"],
                "Reason 2": ["incident_id_3"],
                "Reason 3": ["incident_id_4", "incident_id_5", "incident_id_6"]
            }
"""

system_prompt_zh = """
根据提供的事件数据集和响应架构生成事件报告。确保所有计算指标遵循指定格式以保持一致性。

**计算和指标：**
1. **最常见事件原因**
   - JSON 属性名：most_frequent_reasons
   - 通过分析以下字段识别最常见的根本原因：incident_name（事件名称）、incident_summary（事件摘要）、severity（严重程度）
   - 尝试找出数据集中未明确提及的根本原因
   - 保持简洁，原因必须简短但同时具有描述性
   - 对相似原因进行分组以避免重复
   - 仅输出前 6 个原因
   - 返回一个 JSON 对象，即一个字典
   - 字典中每个键必须是事件原因（描述事件原因的字符串）
   - 每个键的值必须是与该原因对应的事件 ID 列表（字符串）
   - most_frequent_reasons 属性中的对象结构应遵循以下确切格式：
            {
                "原因 1": ["incident_id_1", "incident_id_2"],
                "原因 2": ["incident_id_3"],
                "原因 3": ["incident_id_4", "incident_id_5", "incident_id_6"]
            }
"""

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
    ) -> IncidentReport:
        incidents = self.__get_incidents(
            incidents_query_cel, allowed_incident_ids, incident_ids
        )
        open_ai_report_part = self.__calculate_report_in_openai(incidents)
        report = IncidentReport(
            most_frequent_reasons=open_ai_report_part.most_frequent_reasons
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
        self, incidents: list[IncidentDto]
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

        # Select prompt based on locale
        locale = os.environ.get("KEEP_DEFAULT_LOCALE", "zh_CN")
        use_chinese = locale in ("zh_CN", "zh")
        selected_prompt = system_prompt_zh if use_chinese else system_prompt

        # Only add response_format for OpenAI API; many compatible APIs don't support json_schema
        base_url_str = str(open_ai_client.base_url) if open_ai_client.base_url else ""
        kwargs: dict = {
            "model": get_model_name(self.tenant_id),
            "messages": [
                {"role": "system", "content": selected_prompt},
                {"role": "user", "content": incidents_json},
            ],
            "seed": 1239,
            "temperature": 0.2,
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
