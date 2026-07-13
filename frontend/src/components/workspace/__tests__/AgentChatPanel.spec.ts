/**
 * Sprint 4.5: 补全 AgentChatPanel 测试。
 *
 * 为 frontend/src/components/workspace/AgentChatPanel.vue 的
 * 渲染、发送、流式更新、历史会话补测试。
 *
 * 策略:Mock @/api/agent 的 streamAgentChat 为异步生成器函数 + mock toast。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// Mock toast
vi.mock('@/utils/toast', () => ({
  toast: {
    info: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

// Mock agent API
vi.mock('@/api/agent', () => ({
  streamAgentChat: vi.fn(),
  listConversations: vi.fn(),
  getConversation: vi.fn(),
}))

import { streamAgentChat, listConversations } from '@/api/agent'
import { toast } from '@/utils/toast'
import AgentChatPanel from '../AgentChatPanel.vue'

// ====================================================================
// Tests
// ====================================================================

describe('AgentChatPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('渲染组件,验证空状态文案"你好，我是星渊笔 AI 创作助手"', () => {
    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    expect(wrapper.text()).toContain('你好，我是星渊笔 AI 创作助手')
  })

  it('输入框为空时发送按钮 disabled', () => {
    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    const sendBtn = wrapper.find('.send-btn')
    expect(sendBtn.exists()).toBe(true)
    expect(sendBtn.attributes('disabled')).toBeDefined()
  })

  it('输入文本后发送按钮可点击(无 disabled)', async () => {
    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    await wrapper.find('.input-textarea').setValue('测试消息')

    const sendBtn = wrapper.find('.send-btn')
    expect(sendBtn.attributes('disabled')).toBeUndefined()
  })

  it('点击"新对话"清空 messages 与 conversationId', async () => {
    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    // 预设状态:有消息、有 conversationId
    const vm = wrapper.vm as any
    vm.messages = [{ role: 'user', content: '旧消息' }]
    vm.conversationId = 'old_conv'
    await wrapper.vm.$nextTick()

    // 点击"新对话"按钮(第一个 .header-btn)
    const buttons = wrapper.findAll('.header-btn')
    await buttons[0].trigger('click')

    expect(vm.messages.length).toBe(0)
    expect(vm.conversationId).toBe(null)
  })

  it('点击"历史"按钮触发 listConversations 调用并显示列表', async () => {
    vi.mocked(listConversations).mockResolvedValue([
      {
        id: 'c1',
        novel_id: 'n1',
        title: '历史会话1',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ])

    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    const buttons = wrapper.findAll('.header-btn')
    await buttons[1].trigger('click') // 第二个按钮是"历史"
    await wrapper.vm.$nextTick()

    expect(listConversations).toHaveBeenCalledWith('n1')
    expect(wrapper.text()).toContain('历史会话1')
  })

  it('sendMessage 后 messages 列表更新且 conversationId 被设置', async () => {
    vi.mocked(streamAgentChat).mockImplementation(() => {
      return (async function* () {
        yield { type: 'token', data: { delta: '你好' } }
        yield { type: 'complete', data: { conversation_id: 'c1', message_id: 'm1' } }
      })()
    })

    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    await wrapper.find('.input-textarea').setValue('测试')
    await wrapper.find('.send-btn').trigger('click')

    // 等待异步流完成
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    const vm = wrapper.vm as any
    // user 消息 + assistant 消息
    expect(vm.messages.length).toBe(2)
    expect(vm.messages[0].role).toBe('user')
    expect(vm.messages[0].content).toBe('测试')
    expect(vm.messages[1].role).toBe('assistant')
    expect(vm.messages[1].content).toBe('你好')
    expect(vm.conversationId).toBe('c1')
  })

  it('tool_call 与 tool_result 事件后 toolCalls 数组新增条目', async () => {
    vi.mocked(streamAgentChat).mockImplementation(() => {
      return (async function* () {
        yield { type: 'tool_call', data: { tool: 'stub_tool', args: { arg1: 'v1' } } }
        yield {
          type: 'tool_result',
          data: { tool: 'stub_tool', success: true, data: { result: 'ok' } },
        }
        yield { type: 'complete', data: { conversation_id: 'c1' } }
      })()
    })

    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    await wrapper.find('.input-textarea').setValue('调用工具')
    await wrapper.find('.send-btn').trigger('click')

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    const vm = wrapper.vm as any
    const assistant = vm.messages[1]
    expect(assistant.toolCalls).toBeDefined()
    expect(assistant.toolCalls.length).toBe(1)
    expect(assistant.toolCalls[0].tool).toBe('stub_tool')
    expect(assistant.toolCalls[0].success).toBe(true)
    expect(assistant.toolCalls[0].result).toEqual({ result: 'ok' })
  })

  it('error 事件后 streaming 关闭且 toast.error 被调用', async () => {
    vi.mocked(streamAgentChat).mockImplementation(() => {
      return (async function* () {
        yield { type: 'error', data: { message: '生成失败' } }
      })()
    })

    const wrapper = mount(AgentChatPanel, {
      props: { novelId: 'n1' },
    })

    await wrapper.find('.input-textarea').setValue('触发错误')
    await wrapper.find('.send-btn').trigger('click')

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(toast.error).toHaveBeenCalledWith('生成失败')
    const vm = wrapper.vm as any
    expect(vm.messages[1].streaming).toBe(false)
  })
})
