# ee/ - Enterprise Edition

Keep 的企业版（Enterprise Edition）模块，包含商业认证集成。

## 目录结构

```
ee/
├── identitymanager/identity_managers/
│   ├── auth0/          # Auth0 认证（多租户 SaaS 场景）
│   ├── azuread/        # Azure AD 认证
│   └── keycloak/       # Keycloak 认证
└── LICENSE             # 企业版许可证
```

## 加载机制

`keep/identitymanager/identitymanagerfactory.py` 通过 `importlib` 动态加载：

1. 先在 `keep.identitymanager.identity_managers.{type}` 中查找模块
2. 找不到时 fallback 到 `ee.identitymanager.identity_managers.{type}`
3. 都找不到则抛出 `NotImplementedError`

## 开源版 vs 企业版认证对照

| 认证方式 | 开源版 (keep/) | 企业版 (ee/) |
|---------|:-:|:-:|
| NO_AUTH | Y | |
| DB (单租户) | Y | |
| LDAP | Y | |
| OAuth2 Proxy | Y | |
| Auth0 | | Y |
| Azure AD | | Y |
| Keycloak | | Y |

## 注意事项

- 私有化部署使用 DB/LDAP/NOAUTH 认证时，不会加载此目录
- 此目录为上游项目结构的一部分，不建议修改或移动，避免 merge 冲突
