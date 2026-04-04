import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from keep.api.core.db import (
    create_dashboard as create_dashboard_db,
    get_provider_distribution,
    get_incidents_created_distribution,
    get_combined_workflow_execution_distribution,
    calc_incidents_mttr,
    delete_dashboard as delete_dashboard_db,
    get_dashboards as get_dashboards_db,
    get_session,
    update_dashboard as update_dashboard_db,
)
from keep.api.core.group_filter import check_group_access
from keep.api.i18n import t
from keep.api.models.db.dashboard import Dashboard
from keep.api.models.time_stamp import TimeStampFilter, _get_time_stamp_filter
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory


class DashboardCreateDTO(BaseModel):
    dashboard_name: str
    dashboard_config: Dict


class DashboardUpdateDTO(BaseModel):
    dashboard_config: Optional[Dict] = None  # Allow partial updates
    dashboard_name: Optional[str] = None


class DashboardResponseDTO(BaseModel):
    id: str
    dashboard_name: str
    dashboard_config: Dict
    created_at: datetime
    updated_at: datetime


router = APIRouter()
logger = logging.getLogger(__name__)


def provision_dashboards(tenant_id: str):
    try:
        dashboards_raw = json.loads(os.environ.get("KEEP_DASHBOARDS", "[]"))
    except Exception:
        logger.exception("Failed to load dashboards from environment variable")
        return
    if not dashboards_raw:
        logger.debug("No dashboards to provision")
        return
    logger.info(
        "Provisioning Dashboards", extra={"num_of_dashboards": len(dashboards_raw)}
    )
    dashboards_to_provision = [
        DashboardCreateDTO.parse_obj(dashboard) for dashboard in dashboards_raw
    ]
    for dashboard in dashboards_to_provision:
        logger.info(
            "Provisioning Dashboard",
            extra={"dashboard_name": dashboard.dashboard_name},
        )
        try:
            create_dashboard_db(
                tenant_id,
                dashboard.dashboard_name,
                "system",
                dashboard.dashboard_config,
            )
            logger.info(
                "Provisioned Dashboard",
                extra={"dashboard_name": dashboard.dashboard_name},
            )
        except Exception:
            logger.exception(
                "Failed to provision dashboard",
                extra={"dashboard_name": dashboard.dashboard_name},
            )
    logger.info(
        "Provisioned Dashboards", extra={"num_of_dashboards": len(dashboards_raw)}
    )


@router.get("", response_model=List[DashboardResponseDTO])
def read_dashboards(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:dashboards"])
    ),
    group_id: Optional[str] = Header(None, alias="X-Keep-Group-Id"),
):
    dashboards = get_dashboards_db(authenticated_entity.tenant_id, authenticated_entity=authenticated_entity, selected_group_id=group_id)
    return dashboards


@router.post("", response_model=DashboardResponseDTO)
def create_dashboard(
    dashboard_dto: DashboardCreateDTO,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:dashboards"])
    ),
    group_id: Optional[str] = Header(None, alias="X-Keep-Group-Id"),
):
    email = authenticated_entity.email
    dashboard = create_dashboard_db(
        tenant_id=authenticated_entity.tenant_id,
        dashboard_name=dashboard_dto.dashboard_name,
        dashboard_config=dashboard_dto.dashboard_config,
        created_by=email,
        group_id=group_id,
    )
    return dashboard


@router.put("/{dashboard_id}", response_model=DashboardResponseDTO)
def update_dashboard(
    dashboard_id: str,
    dashboard_dto: DashboardUpdateDTO,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:dashboards"]),
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    # Fetch dashboard to check group access
    statement = select(Dashboard).where(
        Dashboard.id == dashboard_id, Dashboard.tenant_id == tenant_id
    )
    dashboard = session.exec(statement).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail=t("Dashboard not found"))
    if not check_group_access(dashboard, authenticated_entity):
        raise HTTPException(status_code=403, detail="No access to this resource")
    dashboard = update_dashboard_db(
        tenant_id=authenticated_entity.tenant_id,
        dashboard_id=dashboard_id,
        dashboard_name=dashboard_dto.dashboard_name,
        dashboard_config=dashboard_dto.dashboard_config,
        updated_by=authenticated_entity.email,
    )
    return dashboard


@router.delete("/{dashboard_id}")
def delete_dashboard(
    dashboard_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:dashboards"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    # Check group access before deleting
    statement = select(Dashboard).where(
        Dashboard.id == dashboard_id, Dashboard.tenant_id == tenant_id
    )
    dashboard = session.exec(statement).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail=t("Dashboard not found"))
    if not check_group_access(dashboard, authenticated_entity):
        raise HTTPException(status_code=403, detail="No access to this resource")
    # delete the dashboard from the database
    delete_dashboard_db(tenant_id, dashboard_id)
    return {"ok": True}


@router.get("/metric-widgets")
def get_metric_widgets(
    time_stamp: TimeStampFilter = Depends(_get_time_stamp_filter),
    mttr: bool = True,
    apd: bool = True,
    ipd: bool = True,
    wpd: bool = True,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:dashboards"])
    ),
):
    data = {}
    tenant_id = authenticated_entity.tenant_id
    if not time_stamp.lower_timestamp or not time_stamp.upper_timestamp:
        time_stamp = TimeStampFilter(
            upper_timestamp=datetime.utcnow(),
            lower_timestamp=datetime.utcnow() - timedelta(hours=24),
        )
    if apd:
        data["apd"] = get_provider_distribution(
            tenant_id=tenant_id, aggregate_all=True, timestamp_filter=time_stamp
        )
    if ipd:
        data["ipd"] = get_incidents_created_distribution(
            tenant_id=tenant_id, timestamp_filter=time_stamp
        )
    if wpd:
        data["wpd"] = get_combined_workflow_execution_distribution(
            tenant_id=tenant_id, timestamp_filter=time_stamp
        )
    if mttr:
        data["mttr"] = calc_incidents_mttr(
            tenant_id=tenant_id, timestamp_filter=time_stamp
        )
    return data
