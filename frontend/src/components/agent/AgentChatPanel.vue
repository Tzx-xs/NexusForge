<template>
  <div class="agent-chat-panel">
    <!-- 顶部操作栏 -->
    <div class="chat-header">
      <button class="header-btn" @click="startNewConversation">新对话</button>
      <button class="header-btn" @click="toggleHistory">历史</button>
    </div>

    <!-- 历史会话列表（toggle） -->
    <div v-if="showHistory" class="history-list">
      <div v-if="conversations.length === 0" class="history-empty">暂无历史会话</div>
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="history-item"
        @click="loadConversation(conv.id)"
      >
        <div class="history-title">{{ conv.title || '未命名对话' }}</div>
        <div class="history-time">{{ formatTime(conv.updated_at) }}</div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="messagesContainer" class="messages-container">
      <div v-if="messages.length === 0" class="empty-state">
        <p class="empty-title">你好，我是星枢 AI 创作助手</p>
        <p class="empty-desc">可以帮你生成章节、审查质量、查询设定...</p>
        <div class="empty-suggestions">
          <div class="suggestion-item" @click="useSuggestion('帮我生成第3章')">帮我生成第3章</div>
          <div class="suggestion-item" @click="useSuggestion('审查当前章节')">审查当前章节</div>
          <div class="suggestion-item" @click="useSuggestion('查询人物设定')">查询人物设定</div>
        </div>
      </div>
      <div v-for="msg in messages" :key="msg.id" :class="['message', msg.role]">
        <div class="bubble">
          <span class="bubble-content">{{ msg.content }}</span>
          <span v-if="msg.streaming" class="cursor">▌</span>
        </div>
        <div v-if="msg.toolCalls?.length" class="tool-calls">
          <div v-for="tc in msg.toolCalls" :key="tc.id" class="tool-call-card">
            <div class="tool-header">
              <span class="tool-name">{{ tc.tool }}</span>
              <span
                :class="['tool-status', tc.success ? 'success' : tc.result ? 'fail' : 'pending']"
              >
                {{ tc.success ? '✓' : tc.result ? '✗' : '...' }}
              </span>
            </div>
            <details>
              <summary>参数</summary>
              <pre>{{ JSON.stringify(tc.args, null, 2) }}</pre>
            </details>
            <details v-if="tc.result">
              <summary>结果</summary>
              <pre>{{ JSON.stringify(tc.result, null, 2) }}</pre>
            </details>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
      <textarea
        v-model="inputText"
        class="input-textarea"
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        :disabled="isStreaming"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <button
        v-if="!isStreaming"
        class="send-btn"
        :disabled="!inputText.trim()"
        @click="sendMessage"
      >
        发送
      </button>
      <button v-else class="stop-btn" @click="stopGeneration">停止</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import {
  streamAgentChat,
  listConversations,
  getConversation,
  type Conversation,
  type Message,
} from '@/api/agent'

/**
 * AgentChatPanel — NexusForge Agent 聊天面板
 *
 * 移植自 StellarScribe，适配点：
 * - 用 Naive UI useMessage 替换 StellarScribe 的 toast 工具
 * - 调用 NexusForge 版 @/api/agent（已适配信封解包 + X-API-Key）
 */

interface ToolCall {
  id: string
  tool: string
  args: unknown
  result?: unknown
  success?: boolean
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
  streaming?: boolean
}

const props = defineProps<{
  novelId: string
}>()

const message = useMessage()

const messages = ref<ChatMessage[]>([])
const conversationId = ref<string | null>(null)
const inputText = ref('')
const isStreaming = ref(false)
const abortController = ref<AbortController | null>(null)
const conversations = ref<Conversation[]>([])
const showHistory = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)

let scrollPending = false

async function scrollToBottom() {
  if (scrollPending) return
  scrollPending = true
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
  scrollPending = false
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  isStreaming.value = true
  abortController.value = new AbortController()

  const msgId = crypto.randomUUID()
  messages.value.push({ id: msgId, role: 'user', content: text })
  inputText.value = ''
  const assistantIdx = messages.value.push({
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '',
    streaming: true,
  }) - 1

  await scrollToBottom()

  try {
    const stream = streamAgentChat(
      {
        conversation_id: conversationId.value,
        message: text,
        novel_id: props.novelId,
      },
      abortController.value.signal
    )

    for await (const evt of stream) {
      const assistant = messages.value[assistantIdx]
      if (!assistant) break

      switch (evt.type) {
        case 'token': {
          const delta = (evt.data.delta as string) || ''
          if (delta) {
            assistant.content += delta
            await scrollToBottom()
          }
          break
        }
        case 'tool_call': {
          if (!assistant.toolCalls) assistant.toolCalls = []
          assistant.toolCalls.push({
            id: crypto.randomUUID(),
            tool: (evt.data.tool as string) || 'unknown',
            args: evt.data.args || {},
          })
          await scrollToBottom()
          break
        }
        case 'tool_result': {
          const toolCallId = evt.data.tool_call_id as string | undefined
          const toolName = evt.data.tool as string | undefined
          if (assistant.toolCalls) {
            let matched: ToolCall | undefined
            if (toolCallId) {
              matched = assistant.toolCalls.find((tc) => tc.id === toolCallId)
            } else if (toolName) {
              matched = assistant.toolCalls.find(
                (tc) => tc.tool === toolName && tc.result === undefined
              )
            }
            if (matched) {
              matched.result = evt.data.data
              matched.success = !!evt.data.success
            }
          }
          await scrollToBottom()
          break
        }
        case 'complete': {
          if (evt.data.conversation_id) {
            conversationId.value = evt.data.conversation_id as string
          }
          assistant.streaming = false
          break
        }
        case 'error': {
          const msg = (evt.data.message as string) || '生成失败'
          message.error(msg)
          assistant.streaming = false
          break
        }
      }
    }

    const finalAssistant = messages.value[assistantIdx]
    if (finalAssistant) finalAssistant.streaming = false
  } catch (e: unknown) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      message.info('已停止生成')
    } else if (e instanceof Error) {
      message.error(e.message || '生成失败')
    } else {
      message.error('生成失败')
    }
    const assistant = messages.value[assistantIdx]
    if (assistant) assistant.streaming = false
  } finally {
    isStreaming.value = false
    abortController.value = null
  }
}

function stopGeneration() {
  if (abortController.value) {
    abortController.value.abort()
  }
  isStreaming.value = false
}

function startNewConversation() {
  if (isStreaming.value) {
    stopGeneration()
  }
  messages.value = []
  conversationId.value = null
  inputText.value = ''
  showHistory.value = false
}

async function toggleHistory() {
  showHistory.value = !showHistory.value
  if (showHistory.value) {
    try {
      conversations.value = await listConversations(props.novelId)
    } catch (e: unknown) {
      const err = e as { message?: string }
      message.error(err?.message || '加载历史会话失败')
      conversations.value = []
    }
  }
}

async function loadConversation(id: string) {
  try {
    const data = await getConversation(id)
    conversationId.value = data.conversation.id
    messages.value = data.messages.map((m: Message) => ({
      id: crypto.randomUUID(),
      role: m.role,
      content: m.content,
      toolCalls: m.tool_calls ? safeParseToolCalls(m.tool_calls) : undefined,
      streaming: false,
    }))
    showHistory.value = false
    await scrollToBottom()
  } catch (e: unknown) {
    const err = e as { message?: string }
    message.error(err?.message || '加载会话失败')
  }
}

function safeParseToolCalls(raw: string): ToolCall[] {
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed.filter((t: unknown) => typeof (t as Record<string, unknown>)?.tool === 'string')
    if (typeof parsed?.tool === 'string') return [parsed as ToolCall]
    return []
  } catch {
    return []
  }
}

function useSuggestion(text: string) {
  inputText.value = text
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return ''
  }
}
</script>

<style scoped>
.agent-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--nexusforge-surface-1, #ffffff);
  color: var(--nexusforge-text-1, #0f172a);
}

/* 顶部操作栏 */
.chat-header {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  background: var(--nexusforge-surface-2, #f8fafc);
}

.header-btn {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  border-radius: 6px;
  background: var(--nexusforge-surface-1, #ffffff);
  color: var(--nexusforge-text-2, #475569);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.header-btn:hover {
  border-color: var(--nexusforge-brand-500, #4f46e5);
  color: var(--nexusforge-brand-500, #4f46e5);
  background: var(--nexusforge-surface-hover, rgba(0, 0, 0, 0.05));
}

/* 历史会话列表 */
.history-list {
  flex-shrink: 0;
  max-height: 200px;
  overflow-y: auto;
  border-bottom: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  background: var(--nexusforge-surface-1, #ffffff);
}

.history-empty {
  padding: 16px;
  text-align: center;
  color: var(--nexusforge-text-4, #94a3b8);
  font-size: 12px;
}

.history-item {
  padding: 8px 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  transition: background 0.15s ease;
}

.history-item:hover {
  background: var(--nexusforge-surface-hover, rgba(0, 0, 0, 0.05));
}

.history-title {
  font-size: 12px;
  color: var(--nexusforge-text-1, #0f172a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-time {
  font-size: 10px;
  color: var(--nexusforge-text-4, #94a3b8);
  margin-top: 2px;
}

/* 消息列表 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--nexusforge-text-3, #64748b);
  gap: 8px;
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--nexusforge-text-1, #0f172a);
  margin: 0;
}

.empty-desc {
  font-size: 12px;
  color: var(--nexusforge-text-3, #64748b);
  margin: 0;
}

.empty-suggestions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 14px;
  width: 100%;
  max-width: 240px;
}

.suggestion-item {
  padding: 8px 12px;
  border: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  border-radius: 6px;
  background: var(--nexusforge-surface-2, #f8fafc);
  color: var(--nexusforge-text-2, #475569);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.suggestion-item:hover {
  border-color: var(--nexusforge-brand-500, #4f46e5);
  color: var(--nexusforge-brand-500, #4f46e5);
}

/* 消息气泡 */
.message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  align-items: flex-end;
}

.message.assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.bubble {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.message.user .bubble {
  background: var(--nexusforge-brand-500, #4f46e5);
  color: #ffffff;
}

.message.assistant .bubble {
  background: var(--nexusforge-surface-2, #f8fafc);
  color: var(--nexusforge-text-1, #0f172a);
  border: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
}

.bubble-content {
  white-space: pre-wrap;
}

/* 流式光标 */
.cursor {
  display: inline-block;
  margin-left: 2px;
  color: var(--nexusforge-brand-500, #4f46e5);
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  50.01%,
  100% {
    opacity: 0;
  }
}

/* 工具调用卡片 */
.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
  width: 100%;
}

.tool-call-card {
  background: var(--nexusforge-surface-1, #ffffff);
  border: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 11px;
}

.tool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.tool-name {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-weight: 600;
  color: var(--nexusforge-brand-500, #4f46e5);
}

.tool-status {
  font-size: 11px;
  font-weight: 600;
}

.tool-status.success {
  color: #10b981;
}

.tool-status.fail {
  color: #ef4444;
}

.tool-status.pending {
  color: var(--nexusforge-text-4, #94a3b8);
}

.tool-call-card details {
  margin-top: 4px;
}

.tool-call-card summary {
  cursor: pointer;
  color: var(--nexusforge-text-3, #64748b);
  font-size: 11px;
  user-select: none;
}

.tool-call-card pre {
  margin: 4px 0 0;
  padding: 6px;
  background: var(--nexusforge-surface-1, #ffffff);
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 10px;
  color: var(--nexusforge-text-2, #475569);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 160px;
  overflow-y: auto;
}

/* 输入区 */
.input-area {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  background: var(--nexusforge-surface-2, #f8fafc);
}

.input-textarea {
  flex: 1;
  resize: none;
  height: 64px;
  padding: 8px 10px;
  border: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  border-radius: 6px;
  background: var(--nexusforge-surface-1, #ffffff);
  color: var(--nexusforge-text-1, #0f172a);
  font-size: 13px;
  font-family: inherit;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.15s ease;
}

.input-textarea:focus {
  border-color: var(--nexusforge-brand-500, #4f46e5);
}

.input-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-btn,
.stop-btn {
  flex-shrink: 0;
  width: 64px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.send-btn {
  background: var(--nexusforge-brand-500, #4f46e5);
  color: #ffffff;
}

.send-btn:hover:not(:disabled) {
  filter: brightness(1.05);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.stop-btn {
  background: #ef4444;
  color: #fff;
}

.stop-btn:hover {
  filter: brightness(1.05);
}
</style>
