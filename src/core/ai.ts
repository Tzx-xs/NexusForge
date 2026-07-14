import { ref } from 'vue'

export interface AiMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface AiConfig {
  provider: 'openai' | 'ollama' | 'custom'
  apiKey: string
  baseUrl: string
  model: string
  temperature: number
  maxTokens: number
}

const messages = ref<AiMessage[]>([])
const isLoading = ref(false)
const config = ref<AiConfig>({
  provider: 'openai',
  apiKey: '',
  baseUrl: 'https://api.openai.com/v1',
  model: 'gpt-3.5-turbo',
  temperature: 0.7,
  maxTokens: 1000,
})

export function useAi() {
  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading.value) return

    // Add user message
    messages.value.push({
      role: 'user',
      content,
      timestamp: Date.now(),
    })

    isLoading.value = true

    try {
      // TODO: Implement actual AI API calls
      // For now, simulate a response
      await new Promise(resolve => setTimeout(resolve, 1000))

      messages.value.push({
        role: 'assistant',
        content: `AI 服务尚未配置。请在设置中配置 API 密钥。\n\n您的消息: ${content}`,
        timestamp: Date.now(),
      })
    } catch (error) {
      console.error('AI request failed:', error)
      messages.value.push({
        role: 'assistant',
        content: '抱歉，AI 服务请求失败。请检查网络连接和 API 配置。',
        timestamp: Date.now(),
      })
    } finally {
      isLoading.value = false
    }
  }

  const clearMessages = () => {
    messages.value = []
  }

  const updateConfig = (partial: Partial<AiConfig>) => {
    config.value = { ...config.value, ...partial }
  }

  return {
    messages,
    isLoading,
    config,
    sendMessage,
    clearMessages,
    updateConfig,
  }
}
