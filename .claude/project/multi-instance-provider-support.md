# 需求：支持外部系统多实例接入

## 背景
用户希望能够在 Keep 系统中接入同一个外部系统（如 Prometheus）的多个实例。

## 现状分析

### 系统架构层面：已支持多实例

1. **数据库约束**：[keep/api/models/db/provider.py:9](keep/api/models/db/provider.py#L9)
   - 唯一约束是 `(tenant_id, name)`，而非 `(tenant_id, type)`
   - 每个实例通过 UUID 独立标识

2. **配置存储**：[keep/providers/providers_service.py:157](keep/providers/providers_service.py#L157)
   - secret 名称格式：`{tenant_id}_{provider_type}_{provider_unique_id}`
   - 每个实例的配置独立存储

3. **API 层**：[keep/api/routes/providers.py:471](keep/api/routes/providers.py#L471)
   - `POST /install` 接受 `provider_name` 参数
   - 只要实例名称不同，即可安装多个同类型 provider

4. **Workflow 层**
   - Workflow 通过 `provider_id` 引用 provider
   - 多实例在 workflow 层面天然支持

### 可能存在的限制点

1. **UI 展示层面**
   - Provider 列表可能按 type 分组
   - Provider 选择下拉框可能只显示每种类型的第一个实例

## 实现方案

### 方案一：UI 优化（推荐）
- 在 Provider 选择组件中显示实例名称（而非仅显示类型）
- 支持按实例名搜索和筛选

### 方案二：文档说明
- 明确告知用户如何配置多实例
- 提供命名规范建议（如 `prometheus-prod`, `prometheus-dev`）

## 验收标准

1. 可以通过 UI 安装同一个 provider 类型的多个实例
2. 每个实例有独立的配置和状态
3. Workflow 可以选择使用哪个实例
4. 告警来源可以区分来自哪个实例

## 相关代码文件

- [keep/api/models/db/provider.py](keep/api/models/db/provider.py)
- [keep/providers/providers_service.py](keep/providers/providers_service.py)
- [keep/api/routes/providers.py](keep/api/routes/providers.py)
- [keep/providers/providers_factory.py](keep/providers/providers_factory.py)
- [keep/providers/prometheus_provider/prometheus_provider.py](keep/providers/prometheus_provider/prometheus_provider.py)
