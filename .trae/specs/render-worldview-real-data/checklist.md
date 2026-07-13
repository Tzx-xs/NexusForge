# Checklist

- [x] 前端在切换 tab 时调用正确的 `/api/v1/worldview/{graph_type}?novel_id={id}` 接口
- [x] 当前 novelId 为空或默认值时，前端会先加载小说列表并选取有效 novelId
- [x] novelId 变化时，当前 tab 的图谱数据自动重载
- [x] 后端对 characters / geography / rules / plot 四种 graph_type 均返回包含 nodes 和 edges 的 JSON
- [x] 返回的 nodes 字段包含 id, name, role, type, identity, connections, chapters, x, y
- [x] 返回的 edges 字段包含 from, to, label, type
- [x] 前端使用 API 数据成功渲染 SVG 节点与连线
- [x] 后端数据为空时，前端仍展示示例网络（降级逻辑保留）
- [x] UI 设计、颜色、布局、交互与修改前保持一致
- [x] `npm run type-check` 通过
- [x] `npm run build` 通过
- [x] `npm run lint` 通过
- [x] 浏览器自动化验证四个 tab 均出现 `.graph-node` 与 `line` 元素
