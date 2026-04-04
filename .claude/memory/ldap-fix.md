---
name: ldap-keep-shared-network-fix
description: LDAP browser login failed because frontend couldn't resolve backend hostname
type: reference
---

# LDAP 浏览器登录失败修复

## 问题
用户通过浏览器使用 LDAP (AD/LDAP) 登录时失败，显示 "The authentication service is currently unavailable"

## 根本原因
`keep-frontend` 容器没有加入 `keep-shared` Docker 网络，无法解析 `keep-backend` 主机名。

当前端容器内执行 `nslookup keep-backend` 时返回 `NXDOMAIN`。

## 修复
在 `deploy/local-mac/docker-compose.yml` 中给 `keep-frontend` 服务添加：
```yaml
networks:
  - keep-shared
```

同时添加 LDAP 环境变量到 backend 服务。

## 验证
修复后容器内可解析：
```
$ docker exec local-mac-keep-frontend-1 nslookup keep-backend
Name: keep-backend
Address: 172.20.0.5
```

用户 lisi (密码: Test@123456) 可以通过浏览器 LDAP 标签登录成功。

## 相关文件
- `deploy/local-mac/docker-compose.yml`
- `deploy/ldap/docker-compose.yml`
