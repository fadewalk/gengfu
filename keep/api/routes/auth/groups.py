"""
Group management API routes.

DB-backed group management that works with ALL auth types (not just Keycloak).
Groups are stored in the `group` and `user_group` tables.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from keep.api.core.db import engine
from keep.api.models.db.group import Group, UserGroup
from keep.api.models.user import Group as GroupDTO
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / Response Models ──────────────────────────────────────────


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    members: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    members: Optional[list[str]] = None
    roles: Optional[list[str]] = None


class AddMembersRequest(BaseModel):
    members: list[str] = Field(..., min_length=1)


class GroupMemberResponse(BaseModel):
    user_email: str
    role: str
    created_at: datetime

    class Config:
        orm_mode = True


# ── Helper ─────────────────────────────────────────────────────────────


def _group_to_dto(group: Group) -> GroupDTO:
    """Convert a DB Group to a DTO."""
    members = [ug.user_email for ug in group.members]
    roles = list({ug.role for ug in group.members})
    return GroupDTO(
        id=group.id,
        name=group.name,
        roles=roles,
        members=members,
        memberCount=len(members),
    )


# ── CRUD Endpoints ─────────────────────────────────────────────────────


@router.get("", description="Get all groups for the current tenant")
def get_groups(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
) -> list[GroupDTO]:
    with Session(engine) as session:
        groups = session.exec(
            select(Group).where(Group.tenant_id == authenticated_entity.tenant_id)
        ).all()
        return [_group_to_dto(g) for g in groups]


@router.post("", description="Create a new group", status_code=201)
def create_group(
    request: CreateGroupRequest,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
) -> GroupDTO:
    with Session(engine) as session:
        # Check for duplicate name within tenant
        existing = session.exec(
            select(Group).where(
                Group.tenant_id == authenticated_entity.tenant_id,
                Group.name == request.name,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Group '{request.name}' already exists",
            )

        group = Group(
            id=str(uuid4()),
            tenant_id=authenticated_entity.tenant_id,
            name=request.name,
            description=request.description,
            created_by=authenticated_entity.email,
        )
        session.add(group)

        # Add members
        for email in request.members:
            member = UserGroup(
                id=str(uuid4()),
                user_email=email,
                group_id=group.id,
                role="admin" if email == authenticated_entity.email else "member",
            )
            session.add(member)

        session.commit()
        session.refresh(group)
        logger.info(
            "Group created",
            extra={"group_id": group.id, "group_name": group.name},
        )
        return _group_to_dto(group)


@router.get("/{group_id}", description="Get group details")
def get_group(
    group_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
) -> GroupDTO:
    with Session(engine) as session:
        group = session.exec(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return _group_to_dto(group)


@router.put("/{group_id}", description="Update a group")
def update_group(
    group_id: str,
    request: UpdateGroupRequest,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
) -> GroupDTO:
    with Session(engine) as session:
        group = session.exec(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        if request.name is not None:
            group.name = request.name
        if request.description is not None:
            group.description = request.description
        group.updated_at = datetime.utcnow()

        if request.members is not None:
            # Remove existing members
            existing_members = session.exec(
                select(UserGroup).where(UserGroup.group_id == group_id)
            ).all()
            for m in existing_members:
                session.delete(m)
            # Add new members
            for email in request.members:
                member = UserGroup(
                    id=str(uuid4()),
                    user_email=email,
                    group_id=group_id,
                    role="admin" if email == authenticated_entity.email else "member",
                )
                session.add(member)

        session.add(group)
        session.commit()
        session.refresh(group)
        logger.info(
            "Group updated",
            extra={"group_id": group_id},
        )
        return _group_to_dto(group)


@router.delete("/{group_id}", description="Delete a group")
def delete_group(
    group_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
) -> dict:
    with Session(engine) as session:
        group = session.exec(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Delete members first
        members = session.exec(
            select(UserGroup).where(UserGroup.group_id == group_id)
        ).all()
        for m in members:
            session.delete(m)

        session.delete(group)
        session.commit()
        logger.info(
            "Group deleted",
            extra={"group_id": group_id},
        )
        return {"status": "deleted", "group_id": group_id}


# ── Member Management ──────────────────────────────────────────────────


@router.get("/{group_id}/members", description="List group members")
def get_group_members(
    group_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
) -> list[GroupMemberResponse]:
    with Session(engine) as session:
        group = session.exec(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        members = session.exec(
            select(UserGroup).where(UserGroup.group_id == group_id)
        ).all()
        return [GroupMemberResponse.from_orm(m) for m in members]


@router.post("/{group_id}/members", description="Add members to a group")
def add_members(
    group_id: str,
    request: AddMembersRequest,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
) -> dict:
    with Session(engine) as session:
        group = session.exec(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        existing_emails = {
            ug.user_email
            for ug in session.exec(
                select(UserGroup).where(UserGroup.group_id == group_id)
            ).all()
        }

        added = []
        for email in request.members:
            if email not in existing_emails:
                member = UserGroup(
                    id=str(uuid4()),
                    user_email=email,
                    group_id=group_id,
                    role="member",
                )
                session.add(member)
                added.append(email)

        session.commit()
        return {"added": added, "count": len(added)}


@router.delete(
    "/{group_id}/members/{user_email}",
    description="Remove a member from a group",
)
def remove_member(
    group_id: str,
    user_email: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
) -> dict:
    with Session(engine) as session:
        group = session.exec(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        member = session.exec(
            select(UserGroup).where(
                UserGroup.group_id == group_id,
                UserGroup.user_email == user_email,
            )
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        session.delete(member)
        session.commit()
        return {"removed": user_email}


# ── User's Groups ──────────────────────────────────────────────────────


@router.get("/user/{user_email}", description="Get groups for a specific user")
def get_user_groups(
    user_email: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
) -> list[GroupDTO]:
    """Get all groups a user belongs to in the current tenant."""
    with Session(engine) as session:
        user_groups = session.exec(
            select(UserGroup).where(UserGroup.user_email == user_email)
        ).all()
        group_ids = [ug.group_id for ug in user_groups]

        if not group_ids:
            return []

        groups = session.exec(
            select(Group).where(
                Group.id.in_(group_ids),
                Group.tenant_id == authenticated_entity.tenant_id,
            )
        ).all()
        return [_group_to_dto(g) for g in groups]
