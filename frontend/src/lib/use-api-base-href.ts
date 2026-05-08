'use client'

import { useCallback, useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { preserveApiBaseParam, readApiBaseQueryFromLocation } from './navigation'

export function useApiBaseHref(): (href: string) => string {
  const pathname = usePathname()
  const [apiBaseQuery, setApiBaseQuery] = useState('')

  useEffect(() => {
    const syncApiBase = () => setApiBaseQuery(readApiBaseQueryFromLocation())
    syncApiBase()
    window.addEventListener('popstate', syncApiBase)
    return () => window.removeEventListener('popstate', syncApiBase)
  }, [pathname])

  return useCallback(
    (href: string) => preserveApiBaseParam(href, apiBaseQuery),
    [apiBaseQuery],
  )
}
