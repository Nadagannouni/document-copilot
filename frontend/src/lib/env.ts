type Env = {
  apiBaseUrl: string
  supabaseUrl: string
  supabaseAnonKey: string
}

const REQUIRED_ENV_VARS = [
  'VITE_API_BASE_URL',
  'VITE_SUPABASE_URL',
  'VITE_SUPABASE_ANON_KEY',
] as const

type RequiredEnvVar = (typeof REQUIRED_ENV_VARS)[number]

function readRequiredEnvVar(name: RequiredEnvVar): string {
  const value = import.meta.env[name]

  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Missing required environment variable: ${name}`)
  }

  return value.trim()
}

function normalizeBaseUrl(value: string, name: RequiredEnvVar): string {
  let url: URL

  try {
    url = new URL(value)
  } catch {
    throw new Error(`Invalid URL for environment variable: ${name}`)
  }

  return url.toString().replace(/\/$/, '')
}

export const env: Env = {
  apiBaseUrl: normalizeBaseUrl(
    readRequiredEnvVar('VITE_API_BASE_URL'),
    'VITE_API_BASE_URL',
  ),
  supabaseUrl: normalizeBaseUrl(
    readRequiredEnvVar('VITE_SUPABASE_URL'),
    'VITE_SUPABASE_URL',
  ),
  supabaseAnonKey: readRequiredEnvVar('VITE_SUPABASE_ANON_KEY'),
}
