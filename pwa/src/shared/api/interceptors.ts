import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/features/auth/store'
import { isRetriable, toApiError } from './errors'

const MAX_RETRIES = 2

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retryCount?: number
}

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export function setupInterceptors(instance: AxiosInstance): void {
  instance.interceptors.request.use((config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    async (error: unknown) => {
      if (!axios.isAxiosError(error)) {
        return Promise.reject(error)
      }

      const config = error.config as RetryableConfig | undefined
      if (config && isRetriable(error)) {
        const retryCount = config._retryCount ?? 0
        if (retryCount < MAX_RETRIES) {
          config._retryCount = retryCount + 1
          await delay(300 * 2 ** retryCount)
          return instance.request(config)
        }
      }

      if (error.response?.status === 401) {
        useAuthStore.getState().signOut()
      }

      return Promise.reject(toApiError(error))
    },
  )
}
