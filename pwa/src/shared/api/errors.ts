import type { AxiosError } from 'axios'

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function extractDetail(data: unknown): string | undefined {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      if (first && typeof first === 'object' && 'msg' in first) {
        return String((first as { msg: unknown }).msg)
      }
      return String(first)
    }
  }
  return undefined
}

export function toApiError(error: AxiosError): ApiError {
  const status = error.response?.status ?? 0
  const data = error.response?.data
  const detail = extractDetail(data)
  const message = detail ?? (status === 0 ? 'No se pudo conectar con el servidor.' : error.message)
  return new ApiError(status, message, data)
}

export function isRetriable(error: AxiosError): boolean {
  if (!error.response) return true
  return error.response.status >= 500 && error.response.status < 600
}
