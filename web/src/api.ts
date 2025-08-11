import type { SdkReport } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const API_KEY = import.meta.env.VITE_API_KEY || ''

export type AnalyzeOptions = {
  profile?: string
  paramsJson?: string
}

export async function analyzeImage(file: File, opts: AnalyzeOptions = {}): Promise<SdkReport> {
  const form = new FormData()
  form.append('file', file)
  if (opts.profile) form.append('profile', opts.profile)
  if (opts.paramsJson) form.append('params', opts.paramsJson)

  const url = API_BASE ? `${API_BASE.replace(/\/$/, '')}/v1/analyze` : '/v1/analyze'

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      ...(API_KEY ? { 'x-api-key': API_KEY } : {}),
    },
    body: form,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API error ${res.status}: ${text || res.statusText}`)
  }
  return res.json()
}

export function resolveArtifactUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  if (path.startsWith('/')) return (API_BASE ? API_BASE.replace(/\/$/, '') : '') + path
  return (API_BASE ? API_BASE.replace(/\/$/, '') + '/' : '/') + path
}
