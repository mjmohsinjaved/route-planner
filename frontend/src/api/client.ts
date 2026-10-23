import axios, { isAxiosError } from 'axios'

// Local dev: Vite proxies /api to Django. Production: set VITE_API_URL to the backend URL + /api.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 60_000,
})

/** HTTP status of a failed request, or undefined when there was no response. */
export const statusOf = (error: unknown): number | undefined =>
  isAxiosError(error) ? error.response?.status : undefined

/** Turn any request error into one sentence the UI can show. Every API error body carries `detail`. */
export function errorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: unknown } | undefined
    if (typeof data?.detail === 'string') return data.detail
    if (error.code === 'ECONNABORTED') return 'The request took too long. Try again.'
    if (!error.response) return 'Cannot reach the server. Is the backend running?'
  }
  return 'Something went wrong. Try again.'
}
