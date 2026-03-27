# Okta 集成指南

本指南提供了关于 Keep 中 Okta 集成的综合信息，包括配置、部署、维护和测试。

## 概述

Keep 支持将 Okta 作为认证提供商，实现：
- 通过 Okta 实现单一登录 (SSO)
- 使用 JWKS 进行 JWT 令牌验证
- 通过 Okta 进行用户和组管理
- 基于角色的访问控制
- 令牌刷新功能

## 环境变量

### 后端环境变量

| 变量 | 描述 | 示例 |
|----------|-------------|---------|
| `AUTH_TYPE` | 设置为 `"okta"` 以启用 Okta 认证 | `okta` |
| `OKTA_DOMAIN` | 您的 Okta 域名 | `company.okta.com` |
| `OKTA_API_TOKEN` | 用于 Okta 管理的 Admin API 令牌 | `00aBcD3f4GhIJkl5m6NoPQr` |
| `OKTA_ISSUER` | 您的 Okta 应用程序的发行者 URL | `https://company.okta.com/oauth2/default` |
| `OKTA_CLIENT_ID` | 您的 Okta 应用程序的客户端 ID | `0oa1b2c3d4e5f6g7h8i9j` |
| `OKTA_CLIENT_SECRET` | 您的 Okta 应用程序的客户端密钥 | `abcd1234efgh5678ijkl9012` |
| `OKTA_AUDIENCE` | （可选）令牌验证的受众 | `api://keep` |

### 前端环境变量

| 变量 | 描述 | 示例 |
|----------|-------------|---------|
| `AUTH_TYPE` | 设置为 `"OKTA"` 以启用 Okta 认证 | `OKTA` |
| `OKTA_CLIENT_ID` | 您的 Okta 应用程序的客户端 ID | `0oa1b2c3d4e5f6g7h8i9j` |
| `OKTA_CLIENT_SECRET` | 您的 Okta 应用程序的客户端密钥 | `abcd1234efgh5678ijkl9012` |
| `OKTA_ISSUER` | 您的 Okta 应用程序的发行者 URL | `https://company.okta.com/oauth2/default` |
| `OKTA_DOMAIN` | 您的 Okta 域名 | `company.okta.com` |

## Okta 配置

### 创建 Okta 应用程序

1. 登录到您的 Okta 管理控制台
2. 导航到 **应用程序** > **应用程序**
3. 点击 **创建应用集成**
4. 选择 **OIDC - OpenID Connect** 作为登录方法
5. 选择 **Web 应用程序** 作为应用程序类型
6. 点击 **下一步**

### 应用程序设置

1. **名称**：输入您应用程序的名称（例如"Keep"）
2. **授权类型**：选择授权代码
3. **登录重定向 URI**：输入您应用程序的回调 URL，例如 `https://your-keep-domain.com/api/auth/callback/okta`
4. **注销重定向 URI**：输入您应用程序的注销 URL，例如 `https://your-keep-domain.com/signin`
5. **分配**：
   - **暂时跳过组分配**或分配给适当的组
6. 点击 **保存**

### 创建 API 令牌

1. 导航到 **安全性** > **API**
2. 选择 **令牌** 选项卡
3. 点击 **创建令牌**
4. 命名您的令牌（例如"Keep Integration"）
5. 复制生成的令牌值（这将是您的 `OKTA_API_TOKEN`）

### 配置 OIDC 声明（可选但推荐）

1. 导航到您的应用程序
2. 转到 **登录** 选项卡
3. 在 **OpenID Connect ID 令牌** 下，点击 **编辑**
4. 添加自定义声明：
   - `keep_tenant_id`：Keep 中的租户 ID
   - `keep_role`：用户在 Keep 中的角色

## 部署说明

### Docker 部署

将所需的环境变量添加到您的 docker-compose 文件或 Kubernetes 部署：

```yaml
environment:
  - AUTH_TYPE=okta
  - OKTA_DOMAIN=your-company.okta.com
  - OKTA_API_TOKEN=your-api-token
  - OKTA_ISSUER=https://your-company.okta.com/oauth2/default
  - OKTA_CLIENT_ID=your-client-id
  - OKTA_CLIENT_SECRET=your-client-secret
```

### Next.js 前端

在您的 `.env.local` 文件中配置环境变量：

```
AUTH_TYPE=OKTA
OKTA_CLIENT_ID=your-client-id
OKTA_CLIENT_SECRET=your-client-secret
OKTA_ISSUER=https://your-company.okta.com/oauth2/default
OKTA_DOMAIN=your-company.okta.com
```

### Vercel 部署

在您的 Vercel 项目设置中添加环境变量。

## 用户和组管理

### 用户

系统自动将 Okta 用户映射到 Keep 用户。关键映射：

- Okta 电子邮件 → Keep 电子邮件
- Okta 名字 → Keep 名称
- Okta 组 → Keep 组
- 自定义声明 `keep_role` → Keep 角色（如果未指定，默认为"user"）

### 组

Okta 中的组与 Keep 同步。以 `keep_` 为前缀的组被视为角色。

### 角色

角色被实现为带有前缀 `keep_` 的 Okta 组。例如：
- `keep_admin` → Keep 中的管理员角色
- `keep_user` → Keep 中的用户角色

## 认证流程

1. 用户访问 Keep 应用程序
2. 用户被重定向到 Okta 登录页面
3. 成功认证后，Okta 返回 ID 令牌和访问令牌
4. Keep 使用 Okta 的 JWKS 端点验证令牌
5. Keep 从令牌中提取用户信息和权限
6. 令牌过期时，Keep 自动使用刷新令牌刷新令牌

## 令牌刷新

刷新令牌流程由应用程序自动处理：

1. 系统检测访问令牌何时即将过期
2. 它使用刷新令牌从 Okta 获取新的访问令牌
3. 新令牌被存储并用于后续请求

## 测试策略

### 单元测试

1. **AuthVerifier 测试**：使用模拟令牌测试令牌验证
   ```python
   def test_okta_verify_bearer_token():
       # 使用预期声明创建模拟令牌
       # 初始化 OktaAuthVerifier
       # 验证令牌是否正确验证
   ```

2. **IdentityManager 测试**：测试用户和组管理
   ```python
   def test_okta_create_user():
       # 模拟 Okta API 响应
       # 测试创建用户
       # 验证正确的 API 调用
   ```

### 集成测试

1. **端到端认证流程**：
   - 在 Okta 中创建测试用户
   - 尝试登录应用程序
   - 验证成功认证

2. **令牌刷新测试**：
   - 获取访问令牌和刷新令牌
   - 等待令牌过期
   - 验证令牌刷新自动发生

3. **基于角色的访问控制**：
   - 创建具有不同角色的用户
   - 验证基于角色的不同端点访问

### 负载测试

1. **令牌验证性能**：
   - 使用令牌模拟多个并发请求
   - 测量响应时间和系统负载
   - 验证 JWKS 缓存正常工作

2. **用户管理扩展**：
   - 使用大量用户和组进行测试
   - 测量组和用户操作的性能

## 故障排除

### 常见问题

1. **无效令牌错误**：
   - 检查 `OKTA_ISSUER` 是否与您的 Okta 应用程序中的发行者匹配
   - 验证令牌签名算法 (RS256) 受支持
   - 检查您的服务器和 Okta 之间的时钟偏差

2. **API 请求失败**：
   - 验证 `OKTA_API_TOKEN` 有效且具有足够权限
   - 检查 Okta API 速率限制

3. **用户未找到**：
   - 验证用户在 Okta 中存在
   - 检查用户状态（活跃/停用）

### 调试

1. 启用调试日志：
   ```
   AUTH_DEBUG=true
   ```

2. 在 Okta 管理控制台中检查 Okta API 日志

## 维护注意事项

### 令牌轮换

- 定期轮换 `OKTA_API_TOKEN` 以提高安全性
- 更新应用程序中的新令牌而无需停机

### JWKS 缓存

- 实现缓存 JWKS 密钥 24 小时
- 根据密钥轮换策略需要时调整缓存持续时间

### 自定义声明

- 添加新自定义声明时，更新 Okta 配置和代码

### API 速率限制

- 注意 Okta API 速率限制
- 为速率限制错误实现重试逻辑

## 代码结构

### 后端组件

- **`keep/identitymanager/identity_managers/okta/okta_authverifier.py`**：使用 JWKS 处理 JWT 验证
- **`keep/identitymanager/identity_managers/okta/okta_identitymanager.py`**：通过 Okta API 管理用户、组和角色

### 前端组件

- **`auth.config.ts`**：NextAuth.js Okta 配置
- **`authenticationType.ts`**：定义 Okta 作为认证类型

## 安全注意事项

1. **密钥的安全存储**：
   - 安全存储 `OKTA_CLIENT_SECRET` 和 `OKTA_API_TOKEN`
   - 永远不要将密钥提交到版本控制

2. **令牌验证**：
   - 始终使用适当的签名验证验证令牌
   - 验证令牌受众和发行者

3. **作用域 API 令牌**：
   - 对 API 令牌使用最小权限原则

## 未来改进

1. **增强组映射**：
   - 实现更复杂的组到角色映射
   - 支持 Okta 中的嵌套组

2. **自定义授权服务器**：
   - 支持多个 Okta 授权服务器
   - 允许特定于租户的授权服务器

3. **自定义范围处理**：
   - 更好地将 Okta 范围与 Keep 权限集成

## 支持和资源

- [Okta 开发者文档](https://developer.okta.com/docs/reference/)
- [NextAuth.js Okta 提供商文档](https://next-auth.js.org/providers/okta)
- [JWT 调试工具](https://jwt.io/)
