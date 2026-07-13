# Tasks

- [x] Task 1: 创建 Spec 文档
  - [x] SubTask 1.1: 编写 spec.md
  - [x] SubTask 1.2: 编写 tasks.md
  - [x] SubTask 1.3: 编写 checklist.md

- [x] Task 2: 修复/确保前端数据获取与 novelId 解析
  - [x] SubTask 2.1: 确认 useCurrentNovelId 在小说列表未加载时的默认值处理
  - [x] SubTask 2.2: 在 WorldviewManager 中确保小说列表加载后再请求图谱
  - [x] SubTask 2.3: 添加 novelId 变化 watcher，切换小说时自动重载数据
  - [x] SubTask 2.4: 切换 tab 时正确调用对应 graph_type 接口

- [x] Task 3: 校验并修复后端 API 数据返回
  - [x] SubTask 3.1: 校验 `/api/v1/worldview/{graph_type}` 接口对四种 graph_type 均返回 nodes + edges
  - [x] SubTask 3.2: 后端返回格式正常，无需修改 service/route

- [x] Task 4: 前端质量检查
  - [x] SubTask 4.1: 运行 `npm run type-check` 通过
  - [x] SubTask 4.2: 运行 `npm run build` 通过
  - [x] SubTask 4.3: 运行 `npm run lint` 通过（35 个既有 warning，0 error）

- [x] Task 5: 浏览器自动化验证
  - [x] SubTask 5.1: 启动后端服务并准备测试数据
  - [x] SubTask 5.2: 运行 Playwright 脚本验证四个 tab 均能渲染节点
  - [x] SubTask 5.3: 截图保存至 scripts/wv-{tab}.png

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 can run in parallel with Task 2
- Task 4 depends on Task 2 and Task 3
- Task 5 depends on Task 4
