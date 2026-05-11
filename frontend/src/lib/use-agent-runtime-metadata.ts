'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api-client'
import type { AgentRuntimeMetadata } from '@/lib/api-types'

export function useAgentRuntimeMetadata(enabled = true) {
  const [metadata, setMetadata] = useState<AgentRuntimeMetadata | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!enabled) {
      return
    }

    let cancelled = false

    Promise.resolve().then(() => {
      if (!cancelled) setLoading(true)
    })

    api.getAgentRuntimeMetadata().then((response) => {
      if (cancelled) return
      setLoading(false)
      if (response.ok && response.data) {
        setMetadata(response.data)
      }
    })

    return () => {
      cancelled = true
    }
  }, [enabled])

  return { metadata: enabled ? metadata : null, loading: enabled ? loading : false }
}
