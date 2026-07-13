import request from './http'
import type { AxiosRequestConfig } from 'axios'

export type SettingsData = Record<string, string>

export function getSettings() {
  return request.get<SettingsData>('/settings')
}

export function updateSettings(
  data: Partial<{
    ai_provider: string
    default_model: string
    api_base_url: string
    api_key: string
    temperature: string
    max_tokens: string
    target_words: string
    auto_review: string
    review_threshold: string
    max_retries: string
    language: string
    theme: string
  }>
) {
  return request.put<SettingsData>('/settings', data)
}

export function resetSettings() {
  return request.post<SettingsData>('/settings/reset')
}

export interface TestConnectionResult {
  ok: boolean
  response?: string
}

export function testConnection(config?: AxiosRequestConfig) {
  return request.post<TestConnectionResult>('/settings/test-connection', undefined, config)
}
