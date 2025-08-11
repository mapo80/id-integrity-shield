export type CheckResult = {
  score?: number
  threshold?: number
  weight?: number
  decision?: boolean
  artifacts?: Record<string, string>
  [k: string]: any
}

export type SdkReport = {
  profile_id?: string
  tamper_score?: number
  confidence?: number
  decision?: { metric?: string; threshold?: number; verdict?: boolean } | boolean
  checks?: Record<string, CheckResult>
  artifacts?: Record<string, string>
  metrics?: any
  runtime?: any
  [k: string]: any
}
