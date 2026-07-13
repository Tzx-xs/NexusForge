# 世界观管理器接入真实数据 Spec

## Why
世界观管理（WorldviewManager）页面此前仅展示示例网络或降级数据，用户无法看到小说项目真实的人物关系、地理/规则体系与主线规划。需要让该模块从后端 API 拉取并渲染真实数据。

## What Changes
- 保持现有 UI 设计与交互（节点拖拽、缩放、浮层、图例）几乎不变。
- 修复/确保前端在切换 tab 时正确调用 `GET /api/v1/worldview/{graph_type}?novel_id={id}`。
- 确保 `novelId` 在小说列表未加载时能被正确解析，触发小说列表加载后再请求图谱数据。
- 校验后端 `WorldviewService` 对四种 `graph_type`（characters/geography/rules/plot）返回的 `nodes` 与 `edges` 格式正确。
- 当后端返回空数据时，保持现有降级/示例数据展示。
- 不修改任何创意工作流代码（engine/pipeline/generation 等）。

## Impact
- Affected code: `frontend/src/views/dashboard/WorldviewManager.vue`、`frontend/src/api/worldview.ts`、`frontend/src/composables/useCurrentNovelId.ts`、`backend/application/services/worldview_service.py`、`backend/interfaces/api/v1/worldview.py`。
- Affected UI: Dashboard → 世界观管理。

## ADDED Requirements
### Requirement: 真实数据渲染
The system SHALL fetch real worldview graph data from the backend when the user opens the WorldviewManager or switches tabs.

#### Scenario: 人物关系图
- **WHEN** 用户点击「人物关系图」tab 或首次进入页面
- **THEN** 前端使用当前 novelId 调用 `GET /api/v1/worldview/characters?novel_id={id}`
- **AND** 后端返回该小说的人物节点与边
- **AND** 前端使用返回的 `nodes`/`edges` 渲染 SVG 图谱

#### Scenario: 地理关系图
- **WHEN** 用户点击「地理关系图」tab
- **THEN** 前端调用 `GET /api/v1/worldview/geography?novel_id={id}`
- **AND** 后端返回地理/地点/势力节点与边
- **AND** 前端渲染真实地理网络

#### Scenario: 规则体系图
- **WHEN** 用户点击「规则体系图」tab
- **THEN** 前端调用 `GET /api/v1/worldview/rules?novel_id={id}`
- **AND** 后端返回规则节点与边
- **AND** 前端渲染真实规则网络

#### Scenario: 主线规划图
- **WHEN** 用户点击「主线规划图」tab
- **THEN** 前端调用 `GET /api/v1/worldview/plot?novel_id={id}`
- **AND** 后端返回剧情节点与边
- **AND** 前端渲染真实剧情网络

### Requirement: novelId 解析与小说列表加载
- **WHEN** 当前没有选中小说（novelId 为默认值或空）
- **THEN** 前端应先加载小说列表
- **AND** 自动使用第一个小说作为当前 novelId
- **AND** 随后触发对应 tab 的图谱数据请求

## MODIFIED Requirements
### Requirement: 现有图谱渲染逻辑
- 数据请求成功且 `nodes.length > 0` 时，优先使用 API 数据。
- 请求失败或返回空时，保持现有圣经库/示例数据降级逻辑。
- 切换 tab 或 novelId 变化时重新加载数据并重新渲染。
