# Nexus Local 全量代码审计报告

**审计时间**：2026-07-14  
**审计范围**：nexus-local 前端项目全量源码（Vue 3 + TypeScript + Vite）  
**审计结论**：当前代码库存在 **19 个阻断级问题**、**3 个严重级问题** 和 **1 个一般级问题**，项目无法完成编译和运行。需要全面修复后才能正常使用。

---

## 一、阻断级问题（19 个）— 无法编译/启动

### 1. index.html 使用了 Webpack 模板语法

**文件**：`index.html` 第 9 行

```html
<title><%= htmlWebpackPlugin.options.title %></title>
```

**问题**：`htmlWebpackPlugin.options.title` 是 Webpack `HtmlWebpackPlugin` 的模板语法。本项目使用 Vite 构建，Vite 不支持此语法。页面标题将原样显示该字符串。

**修复**：改为静态文本或使用 Vite 的环境变量。

```html
<title>Nexus Local</title>
```

---

### 2. 缺失 views 目录及全部页面视图组件

**文件**：`src/router/index.ts` 第 7、12、17、22 行

路由引用了以下四个视图组件，但 `src/views/` 目录完全不存在：

```ts
component: () => import('@/views/HomeView.vue')    // 不存在
component: () => import('@/views/EditorView.vue')   // 不存在
component: () => import('@/views/SettingsView.vue') // 不存在
component: () => import('@/views/NotFoundView.vue') // 不存在
```

**问题**：所有路由都会失败，应用完全无法导航。

---

### 3. package.json 缺失核心依赖 pinia 和 vue-router

**文件**：`package.json`

代码中直接引用了 `pinia` 和 `vue-router`：

- `src/main.ts` 第 2-3 行：`import { createPinia } from 'pinia'` / `import router from './router'`
- `src/stores/*.ts` 全部使用 `import { defineStore } from 'pinia'`
- 多个组件使用 `import { useRouter } from 'vue-router'`

但 `package.json` 的 `dependencies` 和 `devDependencies` 中均无这两个包。

**问题**：`npm install` 后无法解析这些导入，应用无法启动。

---

### 4. editor.ts 存在重复函数声明（语法错误）

**文件**：`src/stores/editor.ts` 第 163-171 行

```ts
const redo = () => {
    if (editorView.value) {
      cmRedo(editorView.value)
    }
  }

  const redo = () => {        // ← 重复声明
    editorView.value?.dispatch({ effects: redo })
  }
```

**问题**：`redo` 被声明了两次，TypeScript 编译会直接报错（`Cannot redeclare block-scoped variable 'redo'`）。

---

### 5. editor.ts 从 @codemirror/* 包导入但这些包未安装

**文件**：`src/stores/editor.ts` 第 1-16 行

```ts
import type { Editor, MarkdownView, EditorView } from '@codemirror/view'
import { EditorState, Compartment, Extension } from '@codemirror/state'
import { ... } from '@codemirror/view'
import { markdown, markdownLanguage } from '@codemirror/lang-markdown'
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { history, undo as cmUndo, redo as cmRedo } from '@codemirror/history'
import { foldGutter, foldKeymap } from '@codemirror/fold'
import { bracketMatching } from '@codemirror/language'
import { closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete'
import { searchKeymap, completionKeymap } from '@codemirror/autocomplete'
import { defaultTabBinding, indentLess, indentMore } from '@codemirror/commands'
import { oneDark } from '@codemirror/theme-one-dark'
import { vim, vimKeymap } from '@replit/codemirror-vim'
```

**问题**：`package.json` 中没有任何 `@codemirror/*` 或 `@replit/codemirror-vim` 的依赖。而 `package.json` 中安装了 `monaco-editor`，但代码中完全没有使用它。编辑器选型与实际代码完全矛盾。

---

### 6. ai-service.ts 导入不存在的 AIResponse 类型

**文件**：`src/ai/ai-service.ts` 第 1 行

```ts
import type { AIProvider, AIResponse, AppSettings } from '../types';
```

**问题**：`src/types/index.ts` 中没有定义 `AIResponse` 类型。该类型不存在于任何类型文件中。

---

### 7. ai/index.ts 导出不存在的类型

**文件**：`src/ai/index.ts` 第 1 行

```ts
export type { AIProvider, AIService, AIResponse } from '../types';
```

**问题**：`AIService` 和 `AIResponse` 在 `types/index.ts` 中均未定义。

---

### 8. openai-provider.ts 导入不存在的 AIResponse 类型

**文件**：`src/ai/openai-provider.ts` 第 1 行

```ts
import type { AIProvider, AIResponse } from '../types';
```

**问题**：同第 6 项，`AIResponse` 未在 types 中定义。此外，`AIProvider` 接口定义的字段（`id`、`name`、`models`、`isEnabled` 等）与 OpenAIProvider 类实际实现的接口（`name`、`apiKey`、`model`、`baseUrl`、`complete()` 等）完全不匹配。

---

### 9. ollama-provider.ts 导入不存在的 AIResponse 类型

**文件**：`src/ai/ollama-provider.ts` 第 1 行

```ts
import type { AIProvider, AIResponse } from '../types';
```

**问题**：同上，`AIResponse` 未定义。且 OllamaProvider 类实现的接口同样与 types 中的 `AIProvider` 不匹配。

---

### 10. EditorCore.vue 引用不存在的 settings 嵌套属性

**文件**：`src/components/editor/EditorCore.vue` 第 79、105、125 行

```ts
const typewriterMode = computed(() => settingsStore.settings.advanced.enableTypewriterMode)
// ...
if (settingsStore.settings.editor.autoClose) {
// ...
if (settingsStore.settings.editor.autoIndent) {
```

**问题**：`AppSettings` 类型（`types/index.ts`）中没有 `advanced` 和 `editor` 这两个嵌套属性。只有扁平的字段如 `enableFocusMode`、`showLineNumbers` 等。运行时必然报 `Cannot read properties of undefined`。

---

### 11. App.vue 引用不存在的 settings 属性

**文件**：`src/App.vue` 第 277-281 行

```ts
settingsStore.updateSettings({ previewMode: !settingsStore.settings.previewMode })
settingsStore.updateSettings({ focusMode: !settingsStore.settings.focusMode })
```

**问题**：`AppSettings` 类型中没有 `previewMode` 和 `focusMode` 字段。有 `enableFocusMode`，但没有 `previewMode`。

---

### 12. theme.ts 依赖 naive-ui 但未安装

**文件**：`src/stores/theme.ts` 第 3 行

```ts
import { darkTheme, lightTheme, type GlobalThemeOverrides } from 'naive-ui'
```

**问题**：`package.json` 中没有 `naive-ui` 依赖。此外，整个项目中没有任何组件使用 Naive UI，`naive-ui` 的主题配置完全是死代码。

---

### 13. 路由路径不匹配（/note/ vs /notes/）

**文件**：`src/router/index.ts` vs 多个组件

路由定义的路径：
```ts
{ path: '/', ... }            // 首页
{ path: '/note/:id', ... }    // 笔记详情（单数）
```

但组件中导航使用的路径：
- `SidebarNav.vue` 第 170 行：`router.push(\`/notes/${note.id}\`)` （复数）
- `SidebarNav.vue` 第 178 行：`router.push('/notes')` （复数）
- `SearchInput.vue` 第 171 行：`router.push(\`/notes/${note.id}\`)` （复数）
- `App.vue` 第 266 行：`router.push(\`/notes/${note.id}\`)` （复数）
- `App.vue` 第 295 行：`router.push('/notes')` （复数）

**问题**：所有导航目标都是 `/notes/...`（复数），但路由只定义了 `/` 和 `/note/:id`（单数）。导航全部会失败。

---

### 14. createNote 缺少必需字段

**文件**：`src/components/navigation/SidebarNav.vue` 第 159-168 行

```ts
const note = await notesStore.createNote({
    title: '新笔记',
    content: '',
    excerpt: '',         // ← 正确传递了
    tags: [],
    folderId: null,
    isPinned: false,
    isArchived: false,
    isDeleted: false,    // ← 正确传递了
})
```

**文件**：`src/App.vue` 第 333 行

```ts
notesStore.createNote({ title: '未命名笔记', content: '', tags: [], isPinned: false, isArchived: false })
```

**问题**：`App.vue` 中的 `createNote` 调用缺少 `excerpt`、`folderId`、`isDeleted` 三个必需字段，TypeScript 类型检查会报错。

---

### 15. Dockerfile 引用错误的前端路径

**文件**：`Dockerfile` 第 16 行

```dockerfile
COPY --chown=appuser:appuser frontend/dist/ ./frontend/dist/
```

**问题**：项目根目录就是前端（Vite 项目），没有 `frontend/` 子目录。`frontend/dist/` 路径不存在。此外 `edgeone.json` 的 `static_assets.directory` 也写的是 `"frontend/dist"`，同样错误。

---

### 16. vite.config.ts 引用未安装的优化依赖

**文件**：`vite.config.ts` 第 31-41 行

```ts
optimizeDeps: {
    include: [
      'markdown-it',
      'highlight.js',
      'marked',
      'dompurify',
      'fuse.js',
      'uuid',
      // ...
    ]
}
```

**问题**：`package.json` 中没有 `markdown-it`、`highlight.js`、`marked`、`dompurify`、`fuse.js`、`uuid` 中的任何一个依赖。Vite 在预构建时会失败。

---

### 17. TypeScript 编译器选项与 Tailwind CSS v4 不匹配

**文件**：`tailwind.config.js` + `src/style.css`

`package.json` 安装了 `tailwindcss: ^4.0.15` 和 `@tailwindcss/vite: ^4.0.15`（Tailwind CSS v4），但：

- 存在 `tailwind.config.js` 配置文件（v4 使用 CSS-first 配置，不再需要 JS 配置文件）
- `src/style.css` 使用 `@tailwind base; @tailwind components; @tailwind utilities;`（v3 语法，v4 应使用 `@import "tailwindcss"`）

**问题**：Tailwind CSS v4 与 v3 的配置和语法完全不同，当前配置会导致样式全部失效。

---

### 18. CI 中引用的测试工具未安装

**文件**：`.github/workflows/ci.yml` 第 67-71 行

```yaml
- name: Vitest unit tests
  run: npx vitest run
- name: Type check (vue-tsc)
  run: npx vue-tsc --noEmit
```

**问题**：`package.json` 中没有 `vitest` 和 `vue-tsc` 作为 devDependency。CI 运行时会失败（虽然可以 `npx` 下载，但这不是正确的依赖管理方式）。

---

### 19. build-windows.yml 引用不存在的 src-tauri 目录

**文件**：`.github/workflows/build-windows.yml` 第 38-39、103、111-112 行

```yaml
workspaces: src-tauri -> target
# ...
run: npx tauri build --bundles nsis
# ...
path: src-tauri/target/release/nexusforge.exe
```

**问题**：项目中没有 `src-tauri` 目录（未配置 Tauri）。Windows NSIS 构建流水线无法运行。

---

## 二、严重级问题（3 个）— 逻辑错误/数据不一致

### 20. AIProvider 接口定义与实际实现不匹配

**文件**：`src/types/index.ts` 第 71-79 行 vs `src/ai/openai-provider.ts` / `ollama-provider.ts`

types 中定义的 `AIProvider`：
```ts
interface AIProvider {
  id: string;
  name: string;
  type: 'openai' | 'ollama' | 'custom';
  baseUrl?: string;
  apiKey?: string;
  models: AIModel[];
  isEnabled: boolean;
}
```

实际 OpenAIProvider 类实现的接口：
```ts
class OpenAIProvider implements AIProvider {
  name = 'openai';
  apiKey: string;
  model: string;
  baseUrl: string;
  async complete(prompt, context?): Promise<AIResponse>  // types 中无此方法
  async summarize(text): Promise<AIResponse>
  async expand(text): Promise<AIResponse>
  async rewrite(text): Promise<AIResponse>
  async improve(text): Promise<AIResponse>
  async explain(text): Promise<AIResponse>
  async translate(text, lang): Promise<AIResponse>
}
```

**问题**：缺少 `id`、`type`、`models`、`isEnabled` 字段；缺少 `complete()` 等方法签名。类型系统形同虚设。

---

### 21. stores/index.ts 导出不完整

**文件**：`src/stores/index.ts`

```ts
export { useNotesStore } from './notes';
export { useFoldersStore } from './folders';
export { useTagsStore } from './tags';
export { useSettingsStore } from './settings';
export { useUIStore } from './ui';
```

**问题**：缺少 `useThemeStore`（来自 `./theme`）和 `useEditorStore`（来自 `./editor`）的导出。这两个 store 在项目中存在但未通过统一入口导出。

---

### 22. .gitignore 未忽略 .env 文件

**文件**：`.gitignore`

当前只忽略了 `*.local` 和 `*.local.*`，未忽略 `.env`、`.env.local` 等标准环境变量文件。

**问题**：`API_KEY`、`ENCRYPTION_KEY`、`DATABASE_URL` 等敏感配置可能被意外提交到版本控制。

---

## 三、一般级问题（1 个）

### 23. App.vue 中 settingsStore.updateSettings 调用不一致

**文件**：`src/App.vue` 第 345 行

```ts
settingsStore.updateSettings({ enableFocusMode: false })
```

这行使用了正确的字段名 `enableFocusMode`，但第 277 行使用了不存在的 `previewMode`。同一组件中对同一 store 的使用方式不一致，说明开发过程中字段命名发生过变更但未完全同步。

---

## 四、问题汇总表

| 序号 | 级别 | 文件 | 问题摘要 |
|------|------|------|----------|
| 1 | 阻断 | index.html | Webpack 模板语法，Vite 不支持 |
| 2 | 阻断 | src/router/index.ts | 引用不存在的 views/ 目录（4 个文件） |
| 3 | 阻断 | package.json | 缺失 pinia、vue-router 核心依赖 |
| 4 | 阻断 | src/stores/editor.ts | redo 函数重复声明 |
| 5 | 阻断 | src/stores/editor.ts | @codemirror/* 和 @replit/codemirror-vim 未安装 |
| 6 | 阻断 | src/ai/ai-service.ts | 导入不存在的 AIResponse 类型 |
| 7 | 阻断 | src/ai/index.ts | 导出不存在的 AIService、AIResponse 类型 |
| 8 | 阻断 | src/ai/openai-provider.ts | 导入不存在的 AIResponse，接口不匹配 |
| 9 | 阻断 | src/ai/ollama-provider.ts | 导入不存在的 AIResponse，接口不匹配 |
| 10 | 阻断 | src/components/editor/EditorCore.vue | 引用 settings.advanced、settings.editor 不存在属性 |
| 11 | 阻断 | src/App.vue | 引用 settings.previewMode、settings.focusMode 不存在 |
| 12 | 阻断 | src/stores/theme.ts | naive-ui 未安装 |
| 13 | 阻断 | 路由路径 | /notes/ vs /note/ 路径不匹配 |
| 14 | 阻断 | src/App.vue | createNote 缺少必需字段 |
| 15 | 阻断 | Dockerfile | frontend/dist/ 路径不存在 |
| 16 | 阻断 | vite.config.ts | optimizeDeps 引用未安装的包 |
| 17 | 阻断 | Tailwind 配置 | v4 安装但使用 v3 语法和配置 |
| 18 | 阻断 | .github/workflows/ci.yml | vitest、vue-tsc 未作为 devDependency |
| 19 | 阻断 | .github/workflows/build-windows.yml | src-tauri 目录不存在 |
| 20 | 严重 | src/types/index.ts | AIProvider 接口与实际实现不匹配 |
| 21 | 严重 | src/stores/index.ts | 缺少 useThemeStore、useEditorStore 导出 |
| 22 | 严重 | .gitignore | 未忽略 .env 文件 |
| 23 | 一般 | src/App.vue | settings 字段名使用不一致 |

---

## 五、修复优先级建议

**第一优先级（解除阻断）**：

1. 补全 `package.json` 缺失依赖（pinia、vue-router、naive-ui、@codemirror/* 等）
2. 创建 `src/views/` 目录及 4 个视图组件
3. 修复 `index.html` 的 Webpack 模板语法
4. 补全 `AIResponse` 类型定义
5. 修复路由路径不一致（统一为 `/note/:id` 或 `/notes/:id`）
6. 修复 Tailwind CSS v4 配置
7. 删除 editor.ts 中重复的 `redo` 声明

**第二优先级（消除严重问题）**：

8. 统一 AIProvider 接口定义与实现
9. 补全 stores/index.ts 导出
10. 修复 EditorCore.vue 和 App.vue 中引用的不存在 settings 属性
11. 更新 .gitignore 和 Dockerfile 路径

**第三优先级（一般问题）**：

12. 完善 CI 依赖管理
13. 处理 Tauri 构建配置
14. 清理 naive-ui 死代码（如果不需要则移除 theme.ts）
