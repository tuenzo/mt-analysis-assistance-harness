const API_BASE_QUERY_KEYS = ['api_base', 'apiBase'] as const
export const API_BASE_STORAGE_KEY = 'business-analysis-api-base'

export function getApiBaseQueryFromSearch(search: string): string {
  const searchParams = new URLSearchParams(search)
  const nextParams = new URLSearchParams()
  for (const key of API_BASE_QUERY_KEYS) {
    const value = searchParams.get(key)
    if (value?.trim()) {
      nextParams.set(key, value)
    }
  }

  return nextParams.toString()
}

export function readApiBaseQueryFromLocation(): string {
  if (typeof window === 'undefined') {
    return ''
  }

  const query = getApiBaseQueryFromSearch(window.location.search)
  if (query) {
    return query
  }

  try {
    const stored = window.sessionStorage.getItem(API_BASE_STORAGE_KEY)
    if (stored?.trim()) {
      return new URLSearchParams({ api_base: stored.trim() }).toString()
    }
  } catch {
    // Ignore storage failures and leave links on the default API base.
  }

  return ''
}

export function preserveApiBaseParam(href: string, apiBaseQuery: string): string {
  const query = apiBaseQuery.trim()
  if (!query) {
    return href
  }

  return `${href}${href.includes('?') ? '&' : '?'}${query}`
}
