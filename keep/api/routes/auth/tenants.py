"""
Tenant management API routes.

Provides CRUD operations for tenant management in the admin panel.
Admin-only access required.
"""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from keep.api.core.db import engine
from keep.api.models.db.tenant import Tenant
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory
from keep.identitymanager.rbac import Admin as AdminRole

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / Response Models ──────────────────────────────────────────


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    configuration: Optional[dict] = None


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    configuration: Optional[dict] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    configuration: Optional[dict] = None

    class Config:
        orm_mode = True


# ── Helper ─────────────────────────────────────────────────────────────


def _require_admin(authenticated_entity: AuthenticatedEntity) -> None:
    """Ensure the requesting user has admin role."""
    if authenticated_entity.role != AdminRole.get_name():
        raise HTTPException(
            status_code=403,
            detail="Admin access required for tenant management",
        )


# ── CRUD Endpoints ─────────────────────────────────────────────────────


@router.get("", description="List all tenants (admin only)")
def list_tenants(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
) -> list[TenantResponse]:
    _require_admin(authenticated_entity)
    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()
        return [TenantResponse.from_orm(t) for t in tenants]


@router.post("", description="Create a new tenant (admin only)", status_code=201)
def create_tenant(
    request: CreateTenantRequest,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
) -> TenantResponse:
    _require_admin(authenticated_entity)
    with Session(engine) as session:
        # Check for duplicate name
        existing = session.exec(
            select(Tenant).where(Tenant.name == request.name)
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Tenant with name '{request.name}' already exists",
            )
        tenant = Tenant(
            id=str(uuid4()),
            name=request.name,
            configuration=request.configuration,
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        logger.info(
            "Tenant created",
            extra={"tenant_id": tenant.id, "tenant_name": tenant.name},
        )
        return TenantResponse.from_orm(tenant)


@router.get(
    "/{tenant_id}",
    description="Get tenant details (admin only)",
)
def get_tenant(
    tenant_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
) -> TenantResponse:
    _require_admin(authenticated_entity)
    with Session(engine) as session:
        tenant = session.exec(
            select(Tenant).where(Tenant.id == tenant_id)
        ).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return TenantResponse.from_orm(tenant)


@router.put(
    "/{tenant_id}",
    description="Update tenant (admin only)",
)
def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["update:settings"])
    ),
) -> TenantResponse:
    _require_admin(authenticated_entity)
    with Session(engine) as session:
        tenant = session.exec(
            select(Tenant).where(Tenant.id == tenant_id)
        ).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        if request.name is not None:
            tenant.name = request.name
        if request.configuration is not None:
            tenant.configuration = request.configuration
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        logger.info(
            "Tenant updated",
            extra={"tenant_id": tenant.id},
        )
        return TenantResponse.from_orm(tenant)


@router.delete(
    "/{tenant_id}",
    description="Delete tenant (admin only)",
)
def delete_tenant(
    tenant_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["delete:settings"])
    ),
) -> dict:
    _require_admin(authenticated_entity)
    with Session(engine) as session:
        tenant = session.exec(
            select(Tenant).where(Tenant.id == tenant_id)
        ).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        session.delete(tenant)
        session.commit()
        logger.info(
            "Tenant deleted",
            extra={"tenant_id": tenant_id},
        )
        return {"status": "deleted", "tenant_id": tenant_id}
