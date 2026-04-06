import hashlib
import json
import logging
import re
import uuid
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import HTTPException
from openai import OpenAI, OpenAIError
from sqlmodel import Session

from keep.api.bl.ai_model_service import get_client, get_model_name
from keep.api.bl.incidents_bl import IncidentBl
from keep.api.i18n import t
from keep.api.core.db import get_session_sync
from keep.api.models.alert import AlertDto
from keep.api.models.db.ai_suggestion import AIFeedback, AISuggestion, AISuggestionType
from keep.api.models.db.topology import TopologyServiceDtoOut
from keep.api.models.incident import (
    IncidentCandidate,
    IncidentClustering,
    IncidentDto,
    IncidentsClusteringSuggestion,
)


class AISuggestionBl:
    def __init__(self, tenant_id: str, session: Session | None = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.tenant_id = tenant_id
        self.session = session if session else get_session_sync()

        # Resolve AI client via the model configuration service (DB → env fallback)
        try:
            self._client = get_client(tenant_id)
        except (OpenAIError, ValueError) as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise HTTPException(
                status_code=400, detail=t("AI service is not enabled for the client.")
            )

    def get_suggestion_by_input(self, suggestion_input: Dict) -> Optional[AISuggestion]:
        """
        Retrieve an AI suggestion by its input.

        Args:
        - suggestion_input (Dict): The input of the suggestion.

        Returns:
        - Optional[AISuggestion]: The suggestion object if found, otherwise None.
        """
        suggestion_input_hash = self.hash_suggestion_input(suggestion_input)
        return (
            self.session.query(AISuggestion)
            .filter(
                AISuggestion.tenant_id == self.tenant_id,
                AISuggestion.suggestion_input_hash == suggestion_input_hash,
            )
            .first()
        )

    def hash_suggestion_input(self, suggestion_input: Dict) -> str:
        """
        Hash the suggestion input to allow for duplicate suggestions with the same input.

        Args:
        - suggestion_input (Dict): The input of the suggestion.

        Returns:
        - str: The hash of the suggestion input.
        """

        json_input = json.dumps(suggestion_input, sort_keys=True)
        return hashlib.sha256(json_input.encode()).hexdigest()

    def add_suggestion(
        self,
        user_id: str,
        suggestion_input: Dict,
        suggestion_type: AISuggestionType,
        suggestion_content: Dict,
        model: str,
    ) -> AISuggestion:
        """
        Add a new AI suggestion to the database.

        Args:
        - suggestion_type (AISuggestionType): The type of suggestion.
        - suggestion_content (Dict): The content of the suggestion.
        - model (str): The model used for the suggestion.

        Returns:
        - AISuggestion: The created suggestion object.
        """
        self.logger.info(
            "Adding new AI suggestion",
            extra={
                "tenant_id": self.tenant_id,
                "suggestion_type": suggestion_type,
            },
        )

        try:
            suggestion_input_hash = self.hash_suggestion_input(suggestion_input)
            suggestion = AISuggestion(
                tenant_id=self.tenant_id,
                user_id=user_id,
                suggestion_input=suggestion_input,
                suggestion_input_hash=suggestion_input_hash,
                suggestion_type=suggestion_type,
                suggestion_content=suggestion_content,
                model=model,
            )
            self.session.add(suggestion)
            self.session.commit()
            self.logger.info(
                "AI suggestion added successfully",
                extra={
                    "tenant_id": self.tenant_id,
                    "suggestion_id": suggestion.id,
                },
            )
            return suggestion
        except Exception as e:
            self.logger.error(
                "Failed to add AI suggestion",
                extra={
                    "tenant_id": self.tenant_id,
                    "error": str(e),
                },
            )
            self.session.rollback()
            raise

    def add_feedback(
        self,
        suggestion_id: UUID,
        user_id: str,
        feedback_content: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> AIFeedback:
        """
        Add AI feedback to the database.

        Args:
        - suggestion_id (UUID): The ID of the suggestion being feedback on.
        - user_id (str): The ID of the user providing feedback.
        - feedback_content (str): The feedback content.
        - rating (Optional[int]): The user's rating of the AI suggestion.
        - comment (Optional[str]): Any additional comments from the user.

        Returns:
        - AIFeedback: The created feedback object.
        """
        self.logger.info(
            "Saving AI feedback",
            extra={
                "tenant_id": self.tenant_id,
                "suggestion_id": suggestion_id,
            },
        )

        try:
            feedback = AIFeedback(
                suggestion_id=suggestion_id,
                user_id=user_id,
                feedback_content=feedback_content,
                rating=rating,
                comment=comment,
            )
            self.session.add(feedback)
            self.session.commit()
            self.logger.info(
                "AI feedback saved successfully",
                extra={
                    "tenant_id": self.tenant_id,
                    "feedback_id": feedback.id,
                },
            )
            return feedback
        except Exception as e:
            self.logger.error(
                "Failed to save AI feedback",
                extra={
                    "tenant_id": self.tenant_id,
                    "error": str(e),
                },
            )
            self.session.rollback()
            raise

    def get_feedback(
        self, suggestion_type: AISuggestionType | None = None
    ) -> List[AIFeedback]:
        """
        Retrieve AI feedback from the database.

        Args:
        - suggestion_type (AISuggestionType | None): Optional filter for suggestion type.

        Returns:
        - List[AIFeedback]: List of feedback objects.
        """
        query = (
            self.session.query(AIFeedback)
            .join(AISuggestion)
            .filter(AISuggestion.tenant_id == self.tenant_id)
        )

        if suggestion_type:
            query = query.filter(AISuggestion.suggestion_type == suggestion_type)

        feedback_list = query.all()

        self.logger.info(
            "Retrieved AI feedback",
            extra={
                "tenant_id": self.tenant_id,
                "feedback_count": len(feedback_list),
                "suggestion_type": suggestion_type,
            },
        )

        return feedback_list

    def suggest_incidents(
        self,
        alerts_dto: List[AlertDto],
        topology_data: List[TopologyServiceDtoOut],
        user_id: str,
    ) -> IncidentsClusteringSuggestion:
        """Create incident suggestions using AI."""
        if len(alerts_dto) > 50:
            raise HTTPException(status_code=400, detail=t("Too many alerts to process"))

        # Check for existing suggestion
        alerts_fingerprints = [alert.fingerprint for alert in alerts_dto]
        suggestion_input = {"alerts_fingerprints": alerts_fingerprints}
        existing_suggestion = self.get_suggestion_by_input(suggestion_input)

        if existing_suggestion:
            self.logger.info("Retrieving existing suggestion from DB")
            incident_clustering = IncidentClustering.parse_obj(
                existing_suggestion.suggestion_content
            )
            processed_incidents = self._process_incidents(
                incident_clustering.incidents, alerts_dto
            )
            return IncidentsClusteringSuggestion(
                incident_suggestion=processed_incidents,
                suggestion_id=str(existing_suggestion.id),
            )

        try:
            # Prepare prompts
            system_prompt, user_prompt = self._prepare_prompts(
                alerts_dto, topology_data
            )

            # Get completion from OpenAI
            completion = self._get_ai_completion(system_prompt, user_prompt)

            # Parse and process response
            raw_content = completion.choices[0].message.content.strip()
            # Strip markdown code fences that some LLMs wrap around JSON
            if raw_content.startswith("```"):
                raw_content = raw_content.split("\n", 1)[1] if "\n" in raw_content else raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3].strip()

            # Strip thinking tags that some LLMs output (e.g., MiniMax-M2.7-highspeed)
            # These models output content like "<think>...</think>{...}" or just "<think>...thinking...}"
            import re
            thinking_pattern = r'<think>[^}]*?</think>'
            raw_content = re.sub(thinking_pattern, '', raw_content, flags=re.DOTALL).strip()

            # Some LLMs output thinking followed by JSON without proper tags,
            # so try to find JSON starting from the first '{'
            json_start = raw_content.find('{')
            if json_start > 0:
                raw_content = raw_content[json_start:]
                # Find the matching closing brace by counting nesting level
                brace_count = 0
                json_end = -1
                for i, c in enumerate(raw_content):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                if json_end > 0:
                    raw_content = raw_content[:json_end]

            # Parse JSON and normalize LLM field name variations
            raw_data = json.loads(raw_content)
            incidents = raw_data.get("incidents", [])
            self.logger.info(
                "LLM raw response data",
                extra={"raw_data": raw_data},
            )

            # Comprehensive field name normalization for various LLMs
            # Different LLMs return different field names despite json_schema instructions
            FIELD_MAP = {
                # incident_name variations
                "title": "incident_name",
                "name": "incident_name",
                "incident_title": "incident_name",
                "incident_id": "incident_name",
                # alerts variations
                "included_alerts": "alerts",
                "alert_indices": "alerts",
                "alert_ids": "alerts",
                "affected_alerts": "alerts",
                "grouped_alert_ids": "alerts",
                "alert_names": "alerts",
                "involved_alerts": "alerts",
                "assigned_alerts": "alerts",
                "related_alerts": "alerts",
                "correlated_alerts": "alerts",
                "alert_references": "alerts",
                "alert_list": "alerts",
                "grouped_alerts": "alerts",
                # reasoning variations
                "root_cause_hypothesis": "reasoning",
                "root_cause": "reasoning",
                "description": "reasoning",
                "analysis": "reasoning",
                "reason": "reasoning",
                "summary": "reasoning",
                "explanation": "reasoning",
                "potential_root_cause": "reasoning",
                "cause": "reasoning",
                "issue": "reasoning",
                "issue_type": "reasoning",
                # confidence_explanation variations
                "confidence_score_explanation": "confidence_explanation",
                "confidence_explanation_text": "confidence_explanation",
                "confidence_rationale": "confidence_explanation",
                "confidence_calculation_explanation": "confidence_explanation",
                # recommended_actions variations
                "recommendations": "recommended_actions",
                "actions": "recommended_actions",
                "suggested_actions": "recommended_actions",
                "remediation_steps": "recommended_actions",
                "initial_actions": "recommended_actions",
            }
            for item in incidents:
                for old_key, new_key in FIELD_MAP.items():
                    if old_key in item:
                        item[new_key] = item.pop(old_key)
                # LLM may return confidence_explanation as dict instead of string
                if "confidence_explanation" in item and isinstance(item["confidence_explanation"], dict):
                    item["confidence_explanation"] = json.dumps(
                        item["confidence_explanation"], ensure_ascii=False
                    )
                # LLM may return alert names as strings instead of ints
                if "alerts" in item and isinstance(item["alerts"], list):
                    coerced = []
                    for x in item["alerts"]:
                        if isinstance(x, int):
                            coerced.append(x)
                        elif isinstance(x, str):
                            try:
                                coerced.append(int(x))
                            except ValueError:
                                # Not a number — might be an alert name/fingerprint
                                coerced.append(x)
                        else:
                            coerced.append(x)
                    item["alerts"] = coerced

            # Resolve alert name/fingerprint strings to 1-based indices
            # Build lookup: alert name/fingerprint → 1-based index
            alert_name_to_index: Dict[str, int] = {}
            for idx, alert in enumerate(alerts_dto):
                if alert.name:
                    alert_name_to_index[alert.name] = idx + 1
                if alert.fingerprint:
                    alert_name_to_index[alert.fingerprint] = idx + 1

            for item in incidents:
                if "alerts" not in item or not isinstance(item["alerts"], list):
                    continue
                resolved = []
                # Build a case-insensitive lookup once
                lower_map = {k.lower(): v for k, v in alert_name_to_index.items()}
                for x in item["alerts"]:
                    if isinstance(x, int):
                        resolved.append(x)
                        continue
                    if not isinstance(x, str):
                        continue
                    # Strip common LLM prefixes like "Alert 1: HighDiskUsage"
                    cleaned = x
                    m = re.match(r"^Alert\s+\d+\s*:\s*(.+)$", x, re.IGNORECASE)
                    if m:
                        cleaned = m.group(1).strip()
                    # Try exact match first, then case-insensitive
                    if cleaned in alert_name_to_index:
                        resolved.append(alert_name_to_index[cleaned])
                    elif cleaned.lower() in lower_map:
                        resolved.append(lower_map[cleaned.lower()])
                    elif x in alert_name_to_index:
                        resolved.append(alert_name_to_index[x])
                    elif x.lower() in lower_map:
                        resolved.append(lower_map[x.lower()])
                    else:
                        self.logger.warning(
                            f"Could not resolve alert name '{x}' to any known alert"
                        )
                item["alerts"] = resolved

            incident_clustering = IncidentClustering.parse_obj({"incidents": incidents})

            # Save suggestion
            suggestion = self.add_suggestion(
                user_id=user_id,
                suggestion_input=suggestion_input,
                suggestion_type=AISuggestionType.INCIDENT_SUGGESTION,
                suggestion_content=incident_clustering.dict(),
                model=get_model_name(self.tenant_id),
            )

            # Process incidents
            processed_incidents = self._process_incidents(
                incident_clustering.incidents, alerts_dto
            )

            return IncidentsClusteringSuggestion(
                incident_suggestion=processed_incidents,
                suggestion_id=str(suggestion.id),
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"AI incident creation failed: invalid JSON response from model: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM 返回了无效响应，请检查模型配置是否正确。原始错误: {str(e)[:100]}",
            )
        except Exception as e:
            self.logger.error(f"AI incident creation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"AI 服务不可用: {str(e)[:200]}",
            )

    async def commit_incidents(
        self,
        suggestion_id: UUID,
        incidents_with_feedback: List[Dict],
        user_id: str,
        incident_bl: IncidentBl,
    ) -> List[IncidentDto]:
        """Commit incidents with user feedback."""
        committed_incidents = []

        # Add feedback to the database
        changes = {
            incident_commit["incident"]["id"]: incident_commit["changes"]
            for incident_commit in incidents_with_feedback
        }
        self.add_feedback(
            suggestion_id=suggestion_id,
            user_id=user_id,
            feedback_content=changes,
        )

        for incident_with_feedback in incidents_with_feedback:
            if not incident_with_feedback["accepted"]:
                self.logger.info(
                    f"Incident {incident_with_feedback['incident']['name']} rejected by user, skipping creation"
                )
                continue

            try:
                # Create the incident
                incident_dto = IncidentDto.parse_obj(incident_with_feedback["incident"])
                created_incident = incident_bl.create_incident(
                    incident_dto, generated_from_ai=True
                )

                # Add alerts to the created incident
                alert_ids = [
                    alert["fingerprint"]
                    for alert in incident_with_feedback["incident"]["alerts"]
                ]
                await incident_bl.add_alerts_to_incident(created_incident.id, alert_ids)

                committed_incidents.append(created_incident)
                self.logger.info(
                    f"Incident {incident_with_feedback['incident']['name']} created successfully"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to create incident {incident_with_feedback['incident']['name']}: {str(e)}"
                )

        return committed_incidents

    def _prepare_prompts(
        self, alerts_dto: List[AlertDto], topology_data: List[TopologyServiceDtoOut]
    ) -> Tuple[str, str]:
        """Prepare system and user prompts for AI."""
        import os

        locale = os.environ.get("KEEP_DEFAULT_LOCALE", "zh_CN")
        use_chinese = locale in ("zh_CN", "zh")

        alert_descriptions = "\n".join(
            [
                f"Alert {idx+1}: {json.dumps(alert.dict())}"
                for idx, alert in enumerate(alerts_dto)
            ]
        )

        topology_text = "\n".join(
            [
                f"Topology {idx+1}: {json.dumps(topology.dict(), default=str)}"
                for idx, topology in enumerate(topology_data)
            ]
        )

        if use_chinese:
            system_prompt = """
你是一个专注于 IT 运维和事件管理的高级 AI 系统。
你的任务是分析提供的 IT 运维告警和拓扑数据，将它们聚类为有意义的事件。
请综合考虑以下因素：
1. 告警描述和内容
2. 时间上的接近性
3. 受影响的系统或服务
4. IT 问题的类型（如：性能下降、服务中断、资源利用率异常等）
5. 潜在的根本原因
6. 拓扑数据中服务之间的关系和依赖

将相关的告警分组到不同的事件中，并为每个事件提供详细分析。
对于每个事件：
1. 评估其严重程度
2. 为运维团队推荐初步处置措施
3. 提供聚类置信度分数（0.0 到 1.0）
4. 解释置信度分数的计算依据，考虑告警相似度、拓扑关系和告警间关联强度等因素

利用拓扑数据来改进事件聚类，充分考虑服务依赖和关联关系。

重要：所有文本内容（incident_name、reasoning、recommended_actions、confidence_explanation）必须使用中文输出。
"""
            user_prompt = f"""
请分析以下 IT 运维告警和拓扑数据，将告警分组为事件：

告警列表：
{alert_descriptions}

拓扑数据：
{topology_text}

请以指定的 JSON 格式提供分析和聚类结果。所有文本字段必须使用中文。
"""
        else:
            system_prompt = """
        You are an advanced AI system specializing in IT operations and incident management.
        Your task is to analyze the provided IT operations alerts and topology data, and cluster them into meaningful incidents.
        Consider factors such as:
        1. Alert description and content
        2. Potential temporal proximity
        3. Affected systems or services
        4. Type of IT issue (e.g., performance degradation, service outage, resource utilization)
        5. Potential root causes
        6. Relationships and dependencies between services in the topology data

        Group related alerts into distinct incidents and provide a detailed analysis for each incident.
        For each incident:
        1. Assess its severity
        2. Recommend initial actions for the IT operations team
        3. Provide a confidence score (0.0 to 1.0) for the incident clustering
        4. Explain how the confidence score was calculated, considering factors like alert similarity, topology relationships, and the strength of the correlation between alerts

        Use the topology data to improve your incident clustering by considering service dependencies and relationships.
        """

            user_prompt = f"""
        Analyze the following IT operations alerts and topology data, then group the alerts into incidents:

        Alerts:
        {alert_descriptions}

        Topology data:
        {topology_text}

        Provide your analysis and clustering in the specified JSON format.
        """

        return system_prompt, user_prompt

    def _get_ai_completion(self, system_prompt: str, user_prompt: str):
        """Get completion from OpenAI. Falls back without response_format if API doesn't support it."""
        kwargs = {
            "model": get_model_name(self.tenant_id),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,  # Set a reasonable limit for response
        }
        # Only add response_format for OpenAI; many compatible APIs don't support json_schema
        base_url_str = str(self._client.base_url) if self._client.base_url else ""
        if "api.openai.com" in base_url_str:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "incident_clustering",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "incidents": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "incident_name": {"type": "string"},
                                        "alerts": {
                                            "type": "array",
                                            "items": {"type": "integer"},
                                            "description": "List of alert numbers (1-based index)",
                                        },
                                        "reasoning": {"type": "string"},
                                        "severity": {
                                            "type": "string",
                                            "enum": [
                                                "critical",
                                                "high",
                                                "warning",
                                                "info",
                                                "low",
                                            ],
                                        },
                                        "recommended_actions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "confidence_score": {"type": "number"},
                                        "confidence_explanation": {"type": "string"},
                                    },
                                    "required": [
                                        "incident_name",
                                        "alerts",
                                        "reasoning",
                                        "severity",
                                        "recommended_actions",
                                        "confidence_score",
                                        "confidence_explanation",
                                    ],
                                },
                            }
                        },
                        "required": ["incidents"],
                    },
                },
            }
        try:
            completion = self._client.chat.completions.create(**kwargs)
            raw_content = completion.choices[0].message.content
            if not raw_content:
                raise ValueError("API returned empty response content")
            return completion
        except Exception as e:
            self.logger.error(
                f"AI API call failed: {type(e).__name__}: {e}",
                extra={
                    "model": kwargs["model"],
                    "base_url": base_url_str,
                    "messages_length": len(system_prompt) + len(user_prompt),
                },
            )
            raise

    def _process_incidents(
        self, incidents: List[IncidentCandidate], alerts_dto: List[AlertDto]
    ) -> List[IncidentDto]:
        """Process incidents and create DTOs."""
        processed_incidents = []
        for incident in incidents:
            # Skip incidents with no alerts or out-of-range indices
            if not incident.alerts:
                self.logger.warning(f"Skipping incident '{incident.incident_name}' with no alerts")
                continue
            valid_indices = [i for i in incident.alerts if isinstance(i, int) and 1 <= i <= len(alerts_dto)]
            if not valid_indices:
                self.logger.warning(
                    f"Skipping incident '{incident.incident_name}': "
                    f"all alert indices out of range (alerts count: {len(alerts_dto)}, indices: {incident.alerts})"
                )
                continue

            alert_sources: Set[str] = set()
            alert_services: Set[str] = set()
            for alert_index in valid_indices:
                alert = alerts_dto[alert_index - 1]
                if alert.source and len(alert.source) > 0:
                    alert_sources.add(alert.source[0])
                if alert.service:
                    alert_services.add(alert.service)

            incident_alerts = [alerts_dto[i - 1] for i in valid_indices]
            start_time = min(alert.lastReceived for alert in incident_alerts)
            last_seen_time = max(alert.lastReceived for alert in incident_alerts)

            incident_dto = IncidentDto(
                id=uuid.uuid4(),
                name=incident.incident_name,
                start_time=start_time,
                last_seen_time=last_seen_time,
                description=incident.reasoning,
                confidence_score=incident.confidence_score,
                confidence_explanation=incident.confidence_explanation,
                severity=incident.severity,
                alert_ids=[alerts_dto[i - 1].id for i in valid_indices],
                recommended_actions=incident.recommended_actions,
                is_predicted=True,
                is_candidate=True,
                is_visible=True,
                alerts_count=len(valid_indices),
                alert_sources=list(alert_sources),
                alerts=incident_alerts,
                services=list(alert_services),
            )
            processed_incidents.append(incident_dto)
        return processed_incidents
