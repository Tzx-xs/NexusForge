# 星渊笔前端UI修复与优化 - 实施计划

## [x] Task 1: 修改 Dashboard 默认模块为"我的小说"
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 修改 `Dashboard.vue` 中的 `DEFAULT_MODULE` 从 `'new-novel'` 改为 `'my-novels'`
  - 确保导航菜单中"我的小说"高亮显示
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-1.1: 访问首页时 URL query 参数 module 默认为 my-novels
  - `programmatic` TR-1.2: 页面加载完成后显示 MyNovels 组件内容
- **Notes**: 简单配置修改，风险低

## [x] Task 2: 创建小说写作浮动抽屉组件
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 创建 `NovelDrawer.vue` 组件，基于 XyDrawer 扩展
  - 集成 WritingSidebar 和 EditorPanel，实现完整的写作功能
  - 支持关闭时保存状态
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `human-judgment` TR-2.1: 抽屉打开/关闭动画流畅
  - `human-judgment` TR-2.2: 写作功能完整可用
  - `human-judgment` TR-2.3: 抽屉宽度自适应屏幕
- **Notes**: 需要处理组件间通信和状态管理

## [x] Task 3: 修改 MyNovels 点击行为
- **Priority**: high
- **Depends On**: Task 2
- **Description**: 
  - 修改 `MyNovels.vue` 的 `openNovel` 函数
  - 将路由跳转改为打开浮动抽屉
  - 更新相关类型定义和 store 方法
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `human-judgment` TR-3.1: 点击小说卡片打开浮动抽屉
  - `human-judgment` TR-3.2: 不触发页面跳转
  - `human-judgment` TR-3.3: 关闭抽屉后返回原页面状态
- **Notes**: 需要确保抽屉状态与 Dashboard 页面状态同步

## [x] Task 4: 优化 OutlineDag 图谱样式
- **Priority**: medium
- **Depends On**: None
- **Description**: 
  - 修改背景样式，使用设计系统变量
  - 优化节点样式，增加视觉层次和悬停效果
  - 修复闪烁问题，优化 SVG 渲染性能
  - 增加连线动画效果
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `human-judgment` TR-4.1: 图谱背景与设计系统一致
  - `human-judgment` TR-4.2: 节点样式丰富，有差异化
  - `human-judgment` TR-4.3: 拖拽节点流畅无卡顿
  - `human-judgment` TR-4.4: 无明显闪烁现象
- **Notes**: 需要优化 SVG 渲染，减少重绘次数

## [x] Task 5: 重构 WorkspaceShell 顶部导航栏
- **Priority**: medium
- **Depends On**: None
- **Description**: 
  - 重新组织顶部导航栏布局
  - 将功能按钮分组，减少视觉混乱
  - 优化 KPI 指标显示方式
  - 统一按钮样式和间距
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `human-judgment` TR-5.1: 顶部导航栏布局整洁
  - `human-judgment` TR-5.2: 功能按钮组织有序
  - `human-judgment` TR-5.3: KPI 指标清晰易读
  - `human-judgment` TR-5.4: 响应式适配良好
- **Notes**: 需要平衡功能完整性和视觉简洁性

## [x] Task 6: 统一浮动界面设计风格
- **Priority**: medium
- **Depends On**: Task 2, Task 5
- **Description**: 
  - 统一所有浮动抽屉的头部样式
  - 标准化操作按钮布局
  - 确保与 Abyss 设计系统一致性
  - 优化关闭按钮交互体验
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `human-judgment` TR-6.1: 所有浮动界面风格统一
  - `human-judgment` TR-6.2: 符合设计系统规范
  - `human-judgment` TR-6.3: 交互体验一致
- **Notes**: 需要检查所有使用 XyDrawer 的组件