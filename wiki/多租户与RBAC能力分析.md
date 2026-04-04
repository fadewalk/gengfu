# Keep 多租户、RBAC 与用户组管理能力分析

> 分析日期：2026-03-28
> 分析分支：develop

## 一、总体结论

Keep 当前**不支持**"租户内按组隔离数据"的需求。现有架构是 **租户级硬隔离 + 组仅为身份概念（不影响数据可见性）**。

### 能力矩阵

| 能力 | 状态 | 支持的 Auth 类型 |
|---|---|---|
| 多租户（扁平） | 支持 | Keycloak（多组织）、Auth0 |
| 子租户/组织层级 | 不支持 | — |
| 租户切换 UI | 支持 | Keycloak（多组织） |
| RBAC 预定义角色 | 支持（4 个角色） | 所有 auth 类型 |
| 自定义角色 | 支持 | Keycloak EE |
| Scope-based 授权 (`verb:resource`) | 支持 | 所有 auth 类型 |
| 资源级权限 (ABAC) | 部分支持（仅 preset、incident） | Keycloak EE |
| 用户组管理 | 支持 | Keycloak EE |
| 子组/组层级 | 不支持 | — |
| 用户邀请 | 不支持 | — |
| 组级数据隔离 | 不支持 | — |
| 组级配置可见性 | 不支持 | — |

---

## 二、多租户

### 2.1 现状

租户是数据隔离的**唯一硬边界**。每个核心表都有 `tenant_id`，所有查询都按租户过滤。

**Tenant 模型**（`keep/api/models/db/tenant.py`）：

```python
class Tenant(SQLModel, table=True):
    id: str  # UUID
    name: str
    configuration: dict  # JSON
```

- 只有 `id`、`name`、`configuration` 三个字段
- **没有 `parent_tenant_id`**，不支持层级组织

### 2.2 各 Auth 类型的多租户支持

| Auth 类型 | 多租户 | 机制 |
|---|---|---|
| **Keycloak** (EE) | 多组织 | `KEYCLOAK_ROLES_FROM_GROUPS=true`，token 中组路径如 `/keep-org-a-admin`，自动创建租户 |
| **Auth0** (EE) | 多租户 | 用户 `app_metadata.keep_tenant_id` 标识所属租户 |
| **DB** (开源版) | 单租户 | 固定 `SINGLE_TENANT_UUID` |
| **Azure AD** (EE) | 受限 | 委托给 DB 存储 |
| **LDAP** | 单租户 | LDAP 用户映射到单一租户 |
| **NoAuth** | 无认证 | 所有请求直接通过 |

### 2.3 租户切换

前端 `TenantSwitcher`（`keep-ui/components/navbar/Search.tsx`）：当 `session.user.tenantIds.length > 1` 时显示下拉菜单切换租户。

---

## 三、RBAC（角色访问控制）

### 3.1 预定义角色

定义在 `keep/identitymanager/rbac.py`：

| 角色 | 权限范围 | 用途 |
|---|---|---|
| `admin` | `read:*`, `write:*`, `delete:*`, `update:*`, `execute:*` | 全权限 |
| `noc` | `read:*`, `execute:workflows` | 只读 + 运行工作流 |
| `webhook` | `write:alert`, `write:incident` | API Key，用于推送告警 |
| `workflowrunner` | `write:workflows`, `execute:workflows` | API Key，用于运行工作流 |

### 3.2 权限格式

`{verb}:{resource}` 格式（受 Auth0 启发），支持通配符 `read:*`。

### 3.3 权限执行流程

1. API 路由声明所需 scope：`IdentityManagerFactory.get_auth_verifier(scopes=["read:settings"])`
2. `AuthVerifierBase.__call__` 认证请求（Bearer token / API Key / HTTP Basic）
3. `_authorize()` 解析用户角色为 `Role` 类，调用 `role.has_scopes(self.scopes)` 检查

### 3.4 自定义角色

- 仅 **Keycloak EE** 实现了 `create_role`、`update_role`、`delete_role`
- 其他 IdentityManager 使用基类默认实现（不持久化）
- 前端 `RolesTab` 有"Create Custom Role"按钮，非 Keycloak 时禁用

### 3.5 限制

- 每个用户只绑定**一个角色**（代码中有 `TODO: more than one role`）
- `DbIdentityManager` 不支持 `update_user`

---

## 四、资源级权限（ABAC）

### 4.1 现状

仅 **Keycloak EE** 通过 UMA（User-Managed Access）实现资源级权限，且只覆盖两种资源：

| 资源类型 | 权限检查位置 |
|---|---|
| Preset | `keep/api/routes/preset.py` |
| Incident | `keep/api/routes/incidents.py` |

### 4.2 执行流程

```
API 请求 → 获取 identity_manager →
  identity_manager.get_user_permission_on_resource_type(resource_type="incident") →
    基础实现：返回空（不过滤，全部可见）
    Keycloak 实现：调用 Keycloak Policy Evaluation API → 返回允许的资源 ID 列表 →
  SQL 查询加 filter: Incident.id.in_(allowed_incident_ids)
```

### 4.3 关键代码

```python
# keep/api/routes/preset.py
allowed_preset_ids = identity_manager.get_user_permission_on_resource_type(
    resource_type="preset",
    authenticated_entity=authenticated_entity,
)
# 如果 allowed_preset_ids 为空列表，则所有 preset 都允许访问

# keep/api/core/incidents.py
if allowed_incident_ids:
    query = query.filter(Incident.id.in_(allowed_incident_ids))
```

### 4.4 前端

`PermissionsTab`（`keep-ui/app/(keep)/settings/auth/permissions-tab.tsx`）：展示权限矩阵，可为 preset 和 incident 分配用户/组/角色。

---

## 五、用户组管理

### 5.1 现状

组功能**仅 Keycloak EE 完整实现**。开源版 `DbIdentityManager.get_groups()` 返回空列表。

### 5.2 Group 模型

`keep/api/models/user.py` — **Pydantic DTO，不是数据库表**：

```python
class Group(BaseModel):
    id: str
    name: str
    roles: list[str] = []
    members: list[str] = []
    memberCount: int = 0
```

组实际存储在 Keycloak 中，Keep 只是读取和展示。

### 5.3 组 CRUD API

`keep/api/routes/auth/groups.py`：
- `GET /auth/groups` — 获取组列表
- `POST /auth/groups` — 创建组（指定名称、成员 email、角色）
- `PUT /auth/groups/{name}` — 更新组
- `DELETE /auth/groups/{name}` — 删除组

### 5.4 前端

- `keep-ui/app/(keep)/settings/auth/groups-tab.tsx` — 组管理表格
- `keep-ui/app/(keep)/settings/auth/groups-sidebar.tsx` — 创建/编辑组侧边栏

### 5.5 限制

- **没有子组**：Group 模型无 `parent_id`，不支持层级
- **没有邀请机制**：搜索整个代码库，auth 相关代码中无 `invite` 关键词
- **组不影响数据可见性**：见下文第六节

---

## 六、组级数据隔离分析（核心问题）

### 6.1 结论：不存在组级数据隔离

**所有核心数据表都没有 `group_id` 字段，组不参与任何数据查询过滤。**

| 表 | 有 `tenant_id` | 有 `group_id` | 隔离级别 |
|---|---|---|---|
| Alert | 是 | **否** | 租户级 |
| LastAlert | 是 | **否** | 租户级 |
| Incident | 是 | **否** | 租户级 |
| AlertEnrichment | 是 | **否** | 租户级 |
| Preset | 是 | **否** | 租户级 + `is_private`（仅创建者） |
| Dashboard | 是 | **否** | 租户级 + `is_private`（仅创建者） |
| Workflow | 是 | **否** | 租户级 |

### 6.2 当前数据可见性模型

```
┌─────────────────────────────────────────────┐
│  租户 A (tenant_id)       ← 硬隔离           │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  所有用户共享：                        │    │
│  │  · 全部告警 (Alert)                   │    │
│  │  · 全部事件 (Incident)                │    │
│  │  · 全部工作流 (Workflow)               │    │
│  │  · 非私有 Preset / Dashboard          │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  组X ── 仅管理身份和角色，不影响数据可见性      │
│  组Y ── 仅管理身份和角色，不影响数据可见性      │
│                                             │
│  is_private=true 的资源 ── 仅创建者可见       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  租户 B (tenant_id)       ← 完全看不到租户A   │
└─────────────────────────────────────────────┘
```

### 6.3 用户需求 vs 现状

| 需求 | 现状 |
|---|---|
| 组 A 只能看到自己的告警 | 不支持 — 同一租户内所有告警对所有用户可见 |
| 组 B 只能看到自己的 Dashboard | 不支持 — Dashboard 只有 `tenant_id` + `is_private` |
| 用户加入多个组，看到所有组的资源 | 不支持 — 组根本不影响数据可见性 |
| 组内高级配置只对组成员可见 | 不支持 — 无组级权限概念 |

---

## 七、如需实现组级隔离的改动范围

### 7.1 数据库层

1. **所有核心表加 `group_id`** — Alert、Incident、Preset、Dashboard、Workflow 等
2. **新建用户-组关联表** — `user_group(user_id, group_id)` 多对多
3. **组表从外部迁移到内部** — 或同时保持与 Keycloak 同步

### 7.2 查询层

所有查询从：
```python
query.filter(Alert.tenant_id == tenant_id)
```
改为：
```python
query.filter(Alert.tenant_id == tenant_id)
      .filter(
          or_(
              Alert.group_id.in_(user_group_ids),
              Alert.group_id.is_(None)  # 未指定组的资源全局可见
          )
      )
```

### 7.3 API 层

- 创建资源时接受 `group_id` 参数
- 更新资源时支持变更所属组
- 查询资源时自动按用户所在组过滤

### 7.4 前端层

- 创建 Alert/Dashboard/Preset/Workflow 时增加组选择器
- 资源列表按组筛选
- 组管理独立于 Keycloak（开源版可用）

### 7.5 估计影响

- 涉及文件：30+ 个核心文件
- 涉及表：8+ 张数据库表
- 复杂度：高

---

## 八、关键文件索引

### 后端核心

| 文件 | 作用 |
|---|---|
| `keep/api/models/db/tenant.py` | Tenant、TenantApiKey、TenantInstallation DB 模型 |
| `keep/api/models/user.py` | Group、User、Role、ResourcePermission DTO |
| `keep/identitymanager/rbac.py` | 角色定义和 scope 检查 |
| `keep/identitymanager/authverifierbase.py` | 认证验证基类（scope 执行） |
| `keep/identitymanager/identitymanager.py` | IdentityManager 抽象基类 |
| `keep/identitymanager/identitymanagerfactory.py` | IdentityManager 工厂 |

### 后端路由

| 文件 | 作用 |
|---|---|
| `keep/api/routes/auth/users.py` | 用户 CRUD |
| `keep/api/routes/auth/groups.py` | 组 CRUD |
| `keep/api/routes/auth/roles.py` | 角色 CRUD |
| `keep/api/routes/auth/permissions.py` | 资源权限管理 |

### 企业版 IdentityManager

| 文件 | 作用 |
|---|---|
| `keep/ee/identitymanager/identity_managers/keycloak/keycloak_identitymanager.py` | Keycloak 完整实现（组、角色、权限、ABAC） |
| `keep/ee/identitymanager/identity_managers/keycloak/keycloak_authverifier.py` | Keycloak 认证 + 多组织支持 |
| `keep/ee/identitymanager/identity_managers/auth0/auth0_identitymanager.py` | Auth0 实现 |

### 开源版 IdentityManager

| 文件 | 作用 |
|---|---|
| `keep/identitymanager/identity_managers/db/db_identitymanager.py` | DB 认证（单租户） |
| `keep/identitymanager/identity_managers/noauth/noauth_identitymanager.py` | 无认证 |

### 前端

| 文件 | 作用 |
|---|---|
| `keep-ui/app/(keep)/settings/auth/groups-tab.tsx` | 组管理 UI |
| `keep-ui/app/(keep)/settings/auth/groups-sidebar.tsx` | 组创建/编辑侧边栏 |
| `keep-ui/app/(keep)/settings/auth/roles-tab.tsx` | 角色管理 UI |
| `keep-ui/app/(keep)/settings/auth/permissions-tab.tsx` | 资源权限矩阵 UI |
| `keep-ui/components/navbar/Search.tsx` | 租户切换器 |
