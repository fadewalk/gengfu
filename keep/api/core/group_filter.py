"""
Group filtering utility for query-level data isolation.

Provides a reusable function to filter queries by group membership.
Resources with group_id IS NULL are "tenant-wide" and visible to everyone.
"""

from typing import Optional

from sqlalchemy import or_
from sqlmodel import Session, select

from keep.api.models.db.group import Group, UserGroup
from keep.identitymanager.authenticatedentity import AuthenticatedEntity


def get_user_group_ids(
    session: Session,
    tenant_id: str,
    user_email: str,
) -> list[str]:
    """Get all group IDs a user belongs to in a tenant."""
    user_groups = session.exec(
        select(UserGroup).where(UserGroup.user_email == user_email)
    ).all()
    if not user_groups:
        return []

    group_ids = [ug.group_id for ug in user_groups]
    # Filter by tenant
    groups = session.exec(
        select(Group).where(
            Group.id.in_(group_ids),
            Group.tenant_id == tenant_id,
        )
    ).all()
    return [g.id for g in groups]


def apply_group_filter(query, model, authenticated_entity: AuthenticatedEntity):
    """
    Apply group-level filtering to a SQLAlchemy/SQLModel query.

    Resources with group_id IS NULL are "tenant-wide" and visible to all users.
    Resources with group_id set are only visible to members of that group.

    Usage:
        query = session.query(Alert).filter(Alert.tenant_id == tenant_id)
        query = apply_group_filter(query, Alert, authenticated_entity)
    """
    if not hasattr(model, "group_id"):
        # Model doesn't support group isolation yet
        return query

    group_ids = authenticated_entity.group_ids

    if group_ids is None or len(group_ids) == 0:
        # No groups → only see tenant-wide resources
        return query.filter(model.group_id.is_(None))

    # See tenant-wide resources + resources from all user's groups
    return query.filter(
        or_(
            model.group_id.is_(None),
            model.group_id.in_(group_ids),
        )
    )


def populate_group_ids(
    session: Session,
    authenticated_entity: AuthenticatedEntity,
) -> AuthenticatedEntity:
    """
    Populate group_ids on an AuthenticatedEntity from the database.
    Call this at the start of request processing if group_ids is not set.
    """
    if authenticated_entity.group_ids is not None:
        return authenticated_entity

    group_ids = get_user_group_ids(
        session,
        authenticated_entity.tenant_id,
        authenticated_entity.email,
    )
    authenticated_entity.group_ids = group_ids
    return authenticated_entity
