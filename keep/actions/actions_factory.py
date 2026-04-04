import time
import logging
from io import StringIO
from typing import List, Optional, Union
from uuid import uuid4

from pydantic import ValidationError

from keep.api.models.action import ActionDTO
from keep.api.models.db.action import Action
from keep.api.core.db import get_all_actions, create_actions, delete_action, get_action, update_action
from keep.api.core.group_filter import check_group_access
from keep.actions.actions_exception import ActionsCRUDException
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.api.i18n import t
from keep.functions import cyaml

logger = logging.getLogger(__name__)

class ActionsCRUD:
    """CRUD for Action model that shares across CLI, API, ..."""
    @staticmethod
    def get_all_actions(tenant_id: str, selected_group_id: Optional[str] = None) -> List[ActionDTO]:
        action_models = get_all_actions(tenant_id, selected_group_id=selected_group_id)
        return ActionsCRUD._convert_models_to_dtos(action_models)

    @staticmethod
    def _convert_models_to_dtos(models: List[Action]) -> List[ActionDTO]:
        """Convert model to dto, ignore the result if one model is invalid"""
        results: List[ActionDTO] = []
        for model in models:
            try:
                dto = ActionDTO(id=model.id, use=model.use, name=model.name, details=cyaml.safe_load(StringIO(model.action_raw)))
                results.append(dto)
            except ValidationError:
                logger.warning("Unmatched Action model and the coresponding DTO", exc_info=True, extra={
                    "data": model.dict()
                })
        return results

    @staticmethod
    def add_actions(
        tenant_id: str,
        installed_by: str,
        action_dtos: List[dict],
        group_id: Optional[str] = None,
    ):
        try:
            actions = []
            for action_dto in action_dtos:
                action = Action(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    installed_by=installed_by,
                    installation_time=time.time(),
                    name=action_dto.get("name"),
                    use=action_dto.get("use") or action_dto.get("name"),  # if there is no `use` tag, use `name` instead
                    action_raw=cyaml.dump(action_dto),
                    group_id=group_id,
                )
                actions.append(action)
            create_actions(actions)
        except Exception:
            logger.exception("Failed to create actions")
            raise ActionsCRUDException(status_code=422, detail=t("Unable to create the actions"))

    @staticmethod
    def remove_action(tenant_id: str, action_id: str, authenticated_entity: Optional[AuthenticatedEntity] = None):
        try:
            # Check group access if authenticated_entity is provided
            if authenticated_entity:
                action_model = get_action(tenant_id, action_id)
                if action_model and not check_group_access(action_model, authenticated_entity):
                    raise ActionsCRUDException(status_code=403, detail="No access to this resource")
            deleted_action = delete_action(tenant_id, action_id)
            return deleted_action
        except ActionsCRUDException:
            raise
        except Exception:
            logger.exception("Unknown exception when delete action from database")
            raise ActionsCRUDException(status_code=422, detail=t("Unable to delete the requested action"))

    @staticmethod
    def get_action(tenant_id: str, action_id: str) -> Union[Action, None]:
        try:
            return get_action(tenant_id, action_id)
        except Exception:
            logger.exception("Unknown exception when getting action from database")
            raise ActionsCRUDException(status_code=400, detail=t("Unable to get an action"))

    @staticmethod
    def update_action(tenant_id: str, action_id: str, payload: dict) -> Union[Action, None]:
        try:
            action_payload = Action(
                name=payload.get("name"),
                use=payload.get("use") or payload.get("name"),
                action_raw=cyaml.dump(payload),
            )
            updated_action = update_action(tenant_id, action_id, action_payload)
            if updated_action:
                return updated_action
            raise ActionsCRUDException(status_code=422, detail=t("No action matched to be updated"))
        except ActionsCRUDException:
            raise
        except Exception:
            logger.exception("Unknown exception when update an action on database")
            raise ActionsCRUDException(status_code=400, detail=t("Unable to update an action"))
