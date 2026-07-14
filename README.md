# Nexus - Local-first AI Knowledge Management System

A modern, local-first AI knowledge management system built with Vue 3, TypeScript, and Tailwind CSS. Nexus provides a seamless experience for creating, organizing, and searching your personal knowledge base with AI assistance.

## 🚀 Features

### Core Features
- **Local-first Storage**: All data stored locally using IndexedDB with zero server dependency
- **AI Integration**: Connect to multiple AI providers (OpenAI, Ollama, Custom)
- **Smart Editor**: Rich Markdown editor with syntax highlighting and live preview
- **Intelligent Search**: Full-text search powered by Fuse.js with fuzzy matching
- **Note Management**: Create, edit, archive, and organize notes with tags

### AI Capabilities
- **AI Chat**: Interactive chat with context from your notes
- **Content Generation**: AI-powered writing assistance
- **Smart Tagging**: Automatic tag suggestions
- **Content Analysis**: Summarization and insights

### User Experience
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Dark Mode**: Eye-friendly dark theme (default)
- **Responsive Design**: Works on desktop and tablet
- **Focus Mode**: Distraction-free writing environment
- **Quick Access**: Cmd/Ctrl + K command palette

## 🛠️ Tech Stack

- **Frontend Framework**: Vue 3 + Composition API
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Pinia
- **Routing**: Vue Router 4
- **Local Storage**: Dexie.js (IndexedDB wrapper)
- **AI Integration**: Vercel AI SDK
- **Markdown**: Markdown-it + Highlight.js
- **Search**: Fuse.js
- **Utilities**: VueUse

## 📁 Project Structure

```
nexus-local/
├── src/
│   ├── api/           # AI provider integrations
│   ├── assets/        # Static assets
│   ├── components/    # Vue components
│   │   ├── editor/    # Monaco editor components
│   │   ├── layout/    # Layout components
│   │   ├── modals/    # Modal dialogs
│   │   ├── navigation/# Navigation components
│   │   ├── notes/     # Note-related components
│   │   ├── search/    # Search components
│   │   └── ui/        # Reusable UI components
│   ├── composables/   # Vue composables
│   ├── db/            # Database schema and operations
│   ├── router/        # Vue Router configuration
│   ├── stores/        # Pinia stores
│   ├── types/         # TypeScript types
│   ├── utils/         # Utility functions
│   ├── views/         # Page components
│   ├── App.vue        # Root component
│   ├── main.ts        # Entry point
│   └── style.css      # Global styles
├── index.html         # HTML entry point
├── package.json       # Dependencies
├── tsconfig.json      # TypeScript config
├── vite.config.ts     # Vite config
└── tailwind.config.js # Tailwind config
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn or pnpm

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nexus-local.git
cd nexus-local
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

4. Open http://localhost:3000 in your browser

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# AI Provider Configuration
VITE_AI_PROVIDER=openai
VITE_OPENAI_API_KEY=your-api-key
VITE_OPENAI_MODEL=gpt-4

# Or use Ollama (local)
VITE_AI_PROVIDER=ollama
VITE_OLLAMA_BASE_URL=http://localhost:11434
VITE_OLLAMA_MODEL=llama2
```

### AI Provider Setup

#### OpenAI
1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
2. Set `VITE_AI_PROVIDER=openai`
3. Set `VITE_OPENAI_API_KEY=your-key`

#### Ollama (Local)
1. Install [Ollama](https://ollama.ai)
2. Pull a model: `ollama pull llama2`
3. Set `VITE_AI_PROVIDER=ollama`
4. Set `VITE_OLLAMA_BASE_URL=http://localhost:11434`

#### Custom Provider
1. Implement the AI provider interface
2. Register it in the API module
3. Set `VITE_AI_PROVIDER=custom`

## 📝 Usage

### Creating Notes
- Click the **+** button or press `Cmd/Ctrl + N`
- Start typing in the editor
- Add tags for organization

### Searching Notes
- Press `Cmd/Ctrl + K` to open search
- Type to search across all notes
- Use fuzzy matching for approximate searches

### AI Features
- Click the **Chat** button to start an AI conversation
- Select text and ask AI to explain, expand, or rewrite
- Use AI to generate content or suggest tags

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + N` | New note |
| `Cmd/Ctrl + S` | Save note |
| `Cmd/Ctrl + K` | Search |
| `Cmd/Ctrl + B` | Toggle sidebar |
| `Cmd/Ctrl + \` | Toggle right panel |
| `Cmd/Ctrl + Enter` | Toggle preview |
| `Cmd/Ctrl + Shift + F` | Focus mode |
| `Escape` | Exit focus mode |

## 🧪 Development

### Linting
```bash
npm run lint
```

### Type Checking
```bash
npm run type-check
```

### Testing
```bash
npm run test
```

## 📦 Deployment

### Build
```bash
npm run build
```

### Deploy to Static Hosting
The built files in `dist/` can be deployed to any static hosting service:
- Vercel
- Netlify
- GitHub Pages
- AWS S3

### Deploy as Desktop App
Use Electron to package as a desktop application:

```bash
npm install electron --save-dev
npm run build
# Configure electron-builder
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Vue.js](https://vuejs.org/) - The Progressive JavaScript Framework
- [Vite](https://vitejs.dev/) - Next Generation Frontend Tooling
- [Tailwind CSS](https://tailwindcss.com/) - A utility-first CSS framework
- [Pinia](https://pinia.vuejs.org/) - The intuitive store for Vue.js
- [Dexie.js](https://dexie.org/) - A Wrapper Library for IndexedDB
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) - The editor that powers VS Code
- [Fuse.js](https://www.fuse.io/) - Lightweight fuzzy-search

## 📞 Support

- Create an [Issue](https://github.com/yourusername/nexus-local/issues)
- Email: your.email@example.com
- Twitter: @yourusername

---

**Nexus** - Your personal knowledge, amplified by AI.