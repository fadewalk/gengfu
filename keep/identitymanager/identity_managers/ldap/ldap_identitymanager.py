import hashlib
import logging
import os

import jwt
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ldap3 import ALL, SUBTREE, Connection, Server
from sqlmodel import Session, select

from keep.api.core.db import engine
from keep.api.core.db import (
    create_user as create_user_in_db,
    delete_user as delete_user_from_db,
    get_users as get_users_from_db,
    user_exists,
)
from keep.api.core.dependencies import SINGLE_TENANT_UUID
from keep.api.i18n import t
from keep.api.models.db.user import User as DbUser
from keep.api.models.user import User
from keep.contextmanager.contextmanager import ContextManager
from keep.identitymanager.identity_managers.ldap.ldap_authverifier import (
    LdapAuthVerifier,
)
from keep.identitymanager.identitymanager import BaseIdentityManager

logger = logging.getLogger(__name__)


class LdapIdentityManager(BaseIdentityManager):
    def __init__(self, tenant_id, context_manager: ContextManager, **kwargs):
        super().__init__(tenant_id, context_manager, **kwargs)
        self.ldap_url = os.environ.get("LDAP_URL", "")
        self.ldap_bind_dn = os.environ.get("LDAP_BIND_DN", "")
        self.ldap_bind_password = os.environ.get("LDAP_BIND_PASSWORD", "")
        self.ldap_base_dn = os.environ.get("LDAP_BASE_DN", "dc=ubiq2,dc=com")
        self.ldap_user_filter = os.environ.get(
            "LDAP_USER_FILTER", "(&(objectClass=inetOrgPerson)(uid={0}))"
        )
        self.ldap_user_search_base = os.environ.get(
            "LDAP_USER_SEARCH_BASE", self.ldap_base_dn
        )
        self.ldap_mail_attribute = os.environ.get("LDAP_MAIL_ATTRIBUTE", "mail")
        self.ldap_name_attribute = os.environ.get(
            "LDAP_NAME_ATTRIBUTE", "displayName"
        )
        self.ldap_default_role = os.environ.get("LDAP_DEFAULT_ROLE", "Admin")
        # 组映射角色：读取用户的组成员属性（默认 memberOf），按映射表决定更夫角色。
        # LDAP_ROLE_MAPPING 格式（分号分隔，DN 含逗号所以用分号）：
        #   cn=gengfu-admins,ou=groups,dc=x=Admin;cn=gengfu-users,ou=groups,dc=x=User
        self.ldap_role_attribute = os.environ.get("LDAP_ROLE_ATTRIBUTE", "memberOf")
        self.ldap_role_mapping = self._parse_role_mapping(
            os.environ.get("LDAP_ROLE_MAPPING", "")
        )
        # LDAP is considered "configured" if LDAP_URL is explicitly set
        self.ldap_configured = bool(self.ldap_url)
        self.logger.info(
            f"LDAP Identity Manager initialized - URL: {self.ldap_url}, "
            f"configured: {self.ldap_configured}"
        )

    def _is_ldap_configured(self) -> bool:
        """Check if LDAP is actually configured (URL is set)."""
        return self.ldap_configured

    def _authenticate_db(self, username, password) -> dict | None:
        """Authenticate a user against the local DB."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with Session(engine, expire_on_commit=False) as session:
            user = session.exec(
                select(DbUser)
                .where(DbUser.tenant_id == SINGLE_TENANT_UUID)
                .where(DbUser.username == username)
                .where(DbUser.password_hash == password_hash)
            ).first()
            if user:
                user.last_sign_in = __import__("datetime").datetime.utcnow()
                session.add(user)
                session.commit()
                return {
                    "username": user.username,
                    "role": user.role,
                    "ldap": False,
                }
        return None

    @staticmethod
    def _parse_role_mapping(raw: str) -> list[tuple[str, str]]:
        """解析 LDAP_ROLE_MAPPING：条目用分号分隔，每条为 LDAP值=更夫角色。"""
        mapping = []
        for entry in (raw or "").split(";"):
            entry = entry.strip()
            if not entry or "=" not in entry:
                continue
            ldap_value, role = entry.rsplit("=", 1)
            ldap_value, role = ldap_value.strip(), role.strip()
            if ldap_value and role:
                mapping.append((ldap_value, role))
        return mapping

    def _resolve_role(self, user_entry):
        """按用户属性（默认 memberOf）与映射表决定角色；无命中回退默认角色。"""
        import os as _os

        role_lower = (
            self.ldap_default_role.lower()
            if self.ldap_default_role
            else "admin"
        )
        if not self.ldap_role_mapping:
            return role_lower
        try:
            # ldap3 Entry 属性访问（返回 Attribute，含 .values 列表）
            raw = getattr(user_entry, self.ldap_role_attribute, None)
            if raw is None:
                user_values = []
            elif hasattr(raw, "values"):
                user_values = [str(v).lower() for v in raw.values]
            else:
                user_values = [str(raw).lower()]
        except Exception:
            user_values = []

        for ldap_value, role in self.ldap_role_mapping:
            for uv in user_values:
                # 精确匹配或 DN 前缀匹配（便于只写组名不写全 DN）
                if uv == ldap_value.lower() or uv.endswith(ldap_value.lower()):
                    return role.lower()
        return role_lower

    def _get_connection(self, bind_dn=None, bind_password=None):
        """Create an LDAP connection and bind."""
        server = Server(self.ldap_url, get_info=ALL)
        conn = Connection(
            server,
            user=bind_dn or self.ldap_bind_dn,
            password=bind_password or self.ldap_bind_password,
            auto_bind=True,
            raise_exceptions=True,
        )
        return conn

    def _search_user(self, username, conn=None):
        """Search for a user in LDAP by username."""
        close_conn = False
        if conn is None:
            conn = self._get_connection()
            close_conn = True

        try:
            search_filter = self.ldap_user_filter.format(username)
            conn.search(
                search_base=self.ldap_user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    self.ldap_mail_attribute,
                    self.ldap_name_attribute,
                    self.ldap_role_attribute,
                ],
            )
            if conn.entries:
                return conn.entries[0]
            return None
        finally:
            if close_conn:
                conn.unbind()

    def _authenticate_ldap(self, username, password) -> dict | None:
        """Authenticate a user against LDAP using simple bind."""
        user_entry = self._search_user(username)
        if not user_entry:
            return None

        user_dn = user_entry.entry_dn
        try:
            conn = Connection(
                Server(self.ldap_url, get_info=ALL),
                user=user_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=True,
            )
            conn.unbind()

            mail = (
                str(user_entry[self.ldap_mail_attribute])
                if self.ldap_mail_attribute in user_entry
                else f"{username}@ldap"
            )
            # displayName 缺失时回退 cn → uid（轻量目录常只有 cn）
            display_name = (
                str(user_entry[self.ldap_name_attribute])
                if self.ldap_name_attribute in user_entry and user_entry[self.ldap_name_attribute]
                else (
                    str(user_entry["cn"])
                    if "cn" in user_entry
                    else username
                )
            )
            return {
                "username": username,
                "display_name": display_name,
                "mail": mail,
                "role": self._resolve_role(user_entry),
            }
        except Exception:
            self.logger.warning(f"LDAP bind failed for user: {username}")
            return None

    def _generate_jwt(self, username, role, display_name=None):
        """Generate a JWT token for the user."""
        jwt_secret = os.environ.get("KEEP_JWT_SECRET")
        if not jwt_secret:
            self.logger.error(
                "Missing KEEP_JWT_SECRET environment variable"
            )
            raise HTTPException(status_code=401, detail=t("Missing JWT secret"))

        token = jwt.encode(
            {
                "email": username,
                "tenant_id": SINGLE_TENANT_UUID,
                "role": role,
            },
            jwt_secret,
            algorithm="HS256",
        )
        return token

    def on_start(self, app) -> None:
        """Add the signin endpoint supporting both LDAP and DB authentication."""
        self.logger.info("Adding signin endpoint (LDAP + DB hybrid)")

        @app.post("/signin")
        def signin(body: dict):
            username = body.get("username", "").strip()
            password = body.get("password", "")
            auth_method = body.get(
                "auth_method", "auto"
            )  # "ldap", "db", "auto"

            if not username or not password:
                return JSONResponse(
                    status_code=401,
                    content={"message": "Username and password are required"},
                )

            result = None
            method_used = None

            # Determine auth flow based on auth_method
            if auth_method == "ldap":
                # Explicit LDAP-only mode
                if not self._is_ldap_configured():
                    return JSONResponse(
                        status_code=401,
                        content={
                            "message": "LDAP is not configured on this server"
                        },
                    )
                result = self._authenticate_ldap(username, password)
                method_used = "ldap"

            elif auth_method == "db":
                # Explicit DB-only mode
                result = self._authenticate_db(username, password)
                method_used = "db"

            else:
                # Auto mode: try LDAP first (if configured), then fall back to DB
                if self._is_ldap_configured():
                    result = self._authenticate_ldap(username, password)
                    method_used = "ldap"

                if result is None:
                    # Fall back to DB auth
                    result = self._authenticate_db(username, password)
                    method_used = "db"

            if not result:
                return JSONResponse(
                    status_code=401,
                    content={"message": "Invalid username or password"},
                )

            role = result["role"]
            display_name = result.get("display_name", username)

            # Normalize role to lowercase to match RBAC enum values
            role_lower = role.lower() if role else "admin"

            # Auto-provision LDAP users in local DB
            if method_used == "ldap" and not user_exists(
                SINGLE_TENANT_UUID, username
            ):
                create_user_in_db(
                    tenant_id=SINGLE_TENANT_UUID,
                    username=username,
                    password="",  # LDAP users have no local password
                    role=role_lower,
                )
                self.logger.info(
                    f"Auto-provisioned LDAP user: {username}"
                )

            token = self._generate_jwt(username, role_lower, display_name)

            self.logger.info(
                f"User signed in: {username} (method: {method_used})"
            )
            return {
                "accessToken": token,
                "tenantId": SINGLE_TENANT_UUID,
                "email": username,
                "role": role_lower,
                "name": display_name,
                "authMethod": method_used,
            }

        self.logger.info("Added signin endpoint")

    def get_users(self, tenant_id=None) -> list[User]:
        """Get users from local DB."""
        users = get_users_from_db(tenant_id)
        return [
            User(
                email=f"{user.username}",
                name=user.username,
                role=user.role,
                last_login=str(user.last_sign_in)
                if user.last_sign_in
                else None,
                created_at=str(user.created_at),
                ldap=getattr(user, "ldap", False),
            )
            for user in users
        ]

    def create_user(
        self,
        user_email: str,
        user_name: str,
        password: str,
        role: str,
        groups: list,
    ) -> dict:
        """Create user in local DB."""
        try:
            user = create_user_in_db(
                self.tenant_id, user_email, password, role
            )
            return User(
                email=user_email,
                name=user_email,
                role=role,
                last_login=None,
                created_at=str(user.created_at),
                ldap=False,
            )
        except Exception:
            raise HTTPException(status_code=409, detail=t("User already exists"))

    def delete_user(self, user_email: str) -> dict:
        """Delete user from local DB."""
        try:
            delete_user_from_db(user_email)
            return {"status": "OK"}
        except Exception:
            raise HTTPException(
                status_code=404, detail=t("User not found")
            )

    def get_auth_verifier(self, scopes) -> LdapAuthVerifier:
        return LdapAuthVerifier(scopes)

    def update_user(self, user_email: str, update_data: dict) -> User:
        raise NotImplementedError("LdapIdentityManager.update_user")
