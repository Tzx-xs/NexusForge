# 星渊笔前端UI修复与优化 - 产品需求文档

## Overview
- **Summary**: 针对星渊笔前端UI进行全面修复与优化，包括默认模块调整、小说打开方式改为浮动界面、可视化图谱样式优化、Workspace界面重新设计
- **Purpose**: 解决用户反馈的主界面默认页面问题、小说打开方式问题、图谱样式问题，提升整体用户体验
- **Target Users**: 星渊笔小说创作平台用户

## Goals
- [x] 将主界面默认模块从"新建小说"改为"我的小说"
- [x] 将小说项目打开方式改为浮动界面（XyDrawer）
- [x] 优化可视化图谱样式，消除闪烁，提升视觉效果
- [x] 重新设计Workspace界面，使其更整洁有序

## Non-Goals (Out of Scope)
- 不修改后端API接口
- 不改变核心数据模型
- 不引入新的第三方UI库
- 不调整编辑器内核（ProseMirror）

## Background & Context
当前系统使用 Vue 3 + TypeScript + Vite + Pinia + NaiveUI，已自封装 XyDrawer/XyDialog/XyBottomSheet 浮层组件。用户反馈的问题集中在：
1. Dashboard 默认显示新建小说，不符合用户预期
2. 点击小说后跳转到独立页面，打断工作流
3. 可视化图谱样式单调且有闪烁
4. Workspace 界面布局较乱

## Functional Requirements
- **FR-1**: 修改 Dashboard 默认模块为"我的小说"
- **FR-2**: 创建小说详情浮动抽屉组件
- **FR-3**: 修改 MyNovels 点击行为为打开浮动抽屉
- **FR-4**: 优化 OutlineDag 图谱样式和动画
- **FR-5**: 重构 WorkspaceShell 顶部导航栏布局
- **FR-6**: 统一浮动界面设计风格

## Non-Functional Requirements
- **NFR-1**: 浮动抽屉打开/关闭动画流畅，无闪烁
- **NFR-2**: 图谱渲染性能优化，节点拖拽流畅
- **NFR-3**: 响应式设计，适配不同屏幕尺寸
- **NFR-4**: 保持与 Abyss 设计系统一致性

## Constraints
- **Technical**: Vue 3 + TypeScript，使用现有组件库
- **Business**: 保持现有功能完整性
- **Dependencies**: 依赖 XyDrawer、XyDialog 等自封装组件

## Assumptions
- 用户希望快速访问已有小说列表
- 浮动界面能提升工作效率
- 图谱需要更丰富的视觉层次

## Acceptance Criteria

### AC-1: 默认模块改为"我的小说"
- **Given**: 用户打开应用首页
- **When**: 页面加载完成
- **Then**: 默认显示"我的小说"模块内容
- **Verification**: `programmatic`

### AC-2: 小说以浮动界面打开
- **Given**: 用户在"我的小说"中点击小说卡片
- **When**: 点击事件触发
- **Then**: 在当前页面右侧打开浮动抽屉，显示小说详情和写作界面
- **Verification**: `human-judgment`

### AC-3: 图谱样式优化
- **Given**: 用户打开世界观管理模块
- **When**: 图谱渲染完成
- **Then**: 图谱具有丰富的视觉层次，无闪烁，节点样式差异化
- **Verification**: `human-judgment`

### AC-4: Workspace 界面重新设计
- **Given**: 用户进入写作界面
- **When**: 界面渲染完成
- **Then**: 顶部导航栏布局整洁，功能按钮组织有序
- **Verification**: `human-judgment`

## Open Questions
- [ ] 浮动抽屉是否需要支持全屏模式？
- [ ] 图谱是否需要支持不同布局算法？
- [ ] Workspace 是否需要增加更多工具栏选项？