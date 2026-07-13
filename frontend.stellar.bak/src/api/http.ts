import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { toast } from '@/utils/toast'
import { fetchApiConfig } from '@/utils/config'

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export function getAuthHeaders(): Record<string, string> {
  const apiKey = sessionStorage.getItem('xy-api-key')
  return apiKey ? { 'X-API-Key': apiKey } : {}
}

const _errorDebounce = new Map<string, number>()
const _pendingRetry = new Set<string>()

function debounceError(key: string): boolean {
  const now = Date.now()
  const last = _errorDebounce.get(key)
  if (last && now - last < 5000) return true
  _errorDebounce.set(key, now)
  return false
}

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

axiosInstance.interceptors.request.use((config) => {
  const apiKey = sessionStorage.getItem('xy-api-key')
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey
  }
  return config
})

axiosInstance.interceptors.response.use(
  (response) => {
    const res = response.data
    const isApiEnvelope =
      res !== null &&
      typeof res === 'object' &&
      !Array.isArray(res) &&
      'code' in res &&
      typeof (res as Record<string, unknown>).code === 'number' &&
      'data' in res
    if (isApiEnvelope) {
      return (res as ApiResponse).data as unknown as typeof response
    }
    return res as typeof response
  },
  async (error) => {
    const status = error.response?.status
    let backendError = error.response?.data
    const originalRequest = error.config

    if (backendError instanceof Blob) {
      try {
        const text = await backendError.text()
        backendError = JSON.parse(text)
      } catch {
        backendError = null
      }
    }

    if (backendError && backendError.message) {
      error.message = backendError.message
    }

    if (status === 404) {
      error.message = backendError?.message || '请求的资源不存在'
    } else if (status === 500) {
      error.message = backendError?.message || '服务器内部错误'
    } else if (status === 502 || status === 504) {
      error.message = backendError?.message || 'AI 服务暂时不可用'
    } else if (status === 401) {
      error.message = backendError?.message || '未授权访问'
    } else if (status === 403) {
      error.message = backendError?.message || '无权限访问'
    }

    if (status === 401 && originalRequest && !originalRequest._retried) {
      const requestKey = `${originalRequest.method}:${originalRequest.url}`
      if (!_pendingRetry.has(requestKey)) {
        _pendingRetry.add(requestKey)
        try {
          const newKey = await fetchApiConfig()
          if (newKey) {
            originalRequest._retried = true
            originalRequest.headers['X-API-Key'] = newKey
            return axiosInstance(originalRequest)
          }
        } finally {
          _pendingRetry.delete(requestKey)
        }
      }
    }

    const errKey = `${status}:${error.message}`
    if ((status === 401 || status === 403) && debounceError(errKey)) {
      console.warn('[API] Suppressed repeated auth error:', error.message)
      return Promise.reject(error)
    }

    if (error.code !== 'ERR_CANCELED' && !originalRequest?._silent) {
      console.error('API Error:', error.message)
      toast.error(error.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

declare module 'axios' {
  interface AxiosRequestConfig {
    _retried?: boolean
    _silent?: boolean
  }
}

const request = axiosInstance as Omit<
  AxiosInstance,
  'get' | 'post' | 'put' | 'delete' | 'patch'
> & {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
}

export default request
