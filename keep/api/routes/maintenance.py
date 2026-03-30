import logging
from typing import Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session

from keep.api.core.db import get_session
from keep.api.core.group_filter import check_group_access, apply_group_filter, apply_selected_group_filter
from keep.api.i18n import t

from keep.api.models.db.maintenance_window import (
    MaintenanceRuleCreate,
    MaintenanceRuleRead,
    MaintenanceWindowRule,
)
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory

router = APIRouter()


@router.get(
    "",
    response_model=list[MaintenanceRuleRead],
    description="Get all maintenance rules",
)
def get_maintenance_rules(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:maintenance"])
    ),
    session: Session = Depends(get_session),
    group_id: Optional[str] = Header(None, alias="X-Keep-Group-Id"),
) -> list[MaintenanceRuleRead]:
    rules_query = (
        session.query(MaintenanceWindowRule)
        .filter(MaintenanceWindowRule.tenant_id == authenticated_entity.tenant_id)
    )
    # Apply group filter: use selected group or fall back to user's groups
    if group_id:
        rules_query = apply_selected_group_filter(rules_query, MaintenanceWindowRule, group_id)
    else:
        rules_query = apply_group_filter(rules_query, MaintenanceWindowRule, authenticated_entity)
    rules = rules_query.all()
    return [MaintenanceRuleRead(**rule.dict()) for rule in rules]


@router.post(
    "", response_model=MaintenanceRuleRead, description="Create a new maintenance rule"
)
def create_maintenance_rule(
    rule_dto: MaintenanceRuleCreate,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:maintenance"])
    ),
    session: Session = Depends(get_session),
    group_id: Optional[str] = Header(None, alias="X-Keep-Group-Id"),
) -> MaintenanceRuleRead:
    end_time = rule_dto.start_time + timedelta(seconds=rule_dto.duration_seconds)
    new_rule = MaintenanceWindowRule(
        **rule_dto.dict(),
        end_time=end_time,
        created_by=authenticated_entity.email,
        tenant_id=authenticated_entity.tenant_id,
        group_id=group_id,
    )
    session.add(new_rule)
    session.commit()
    session.refresh(new_rule)
    return MaintenanceRuleRead(**new_rule.dict())


@router.put(
    "/{rule_id}",
    response_model=MaintenanceRuleRead,
    description="Update an existing maintenance rule",
)
def update_maintenance_rule(
    rule_id: int,
    rule_dto: MaintenanceRuleCreate,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:maintenance"])
    ),
    session: Session = Depends(get_session),
) -> MaintenanceRuleRead:
    rule: MaintenanceWindowRule = (
        session.query(MaintenanceWindowRule)
        .filter(
            MaintenanceWindowRule.tenant_id == authenticated_entity.tenant_id,
            MaintenanceWindowRule.id == rule_id,
        )
        .first()
    )
    if not rule:
        raise HTTPException(
            status_code=404, detail=t("Maintenance rule not found or access denied")
        )

    # Check group access
    if not check_group_access(rule, authenticated_entity):
        raise HTTPException(status_code=403, detail="No access to this resource")

    for key, value in rule_dto.dict().items():
        setattr(rule, key, value)

    end_time = rule_dto.start_time + timedelta(seconds=rule_dto.duration_seconds)
    rule.end_time = end_time

    session.commit()
    session.refresh(rule)
    return MaintenanceRuleRead(**rule.dict())


@router.delete("/{rule_id}", description="Delete a maintenance rule")
def delete_maintenance_rule(
    rule_id: int,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:maintenance"])
    ),
    session: Session = Depends(get_session),
):
    rule = (
        session.query(MaintenanceWindowRule)
        .filter(
            MaintenanceWindowRule.tenant_id == authenticated_entity.tenant_id,
            MaintenanceWindowRule.id == rule_id,
        )
        .first()
    )
    if not rule:
        raise HTTPException(
            status_code=404, detail=t("Maintenance rule not found or access denied")
        )

    # Check group access
    if not check_group_access(rule, authenticated_entity):
        raise HTTPException(status_code=403, detail="No access to this resource")

    session.delete(rule)
    session.commit()
    return {"detail": "Maintenance rule deleted successfully"}
