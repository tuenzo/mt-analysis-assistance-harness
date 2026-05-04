'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import type { SSEEvent } from './api-types'
import { api } from './api-client'

interface UseAgentEventsOptions {
  onEvent?: (event: SSEEvent) => void
  onError?: (error: Error) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

interface UseAgentEventsResult {
  connected: boolean
  error: Error | null
  reconnect: () => void
}

export function useAgentEvents(
  sessionId: string | null,
  options: UseAgentEventsOptions = {}
): UseAgentEventsResult {
  const { onEvent, onError, onConnect, onDisconnect } = options
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [lastTurnId, setLastTurnId] = useState<string | null>(null)
  const lastTurnIdRef = useRef<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!sessionId) return

    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const eventSource = new EventSource(api.getSessionEventsUrl(sessionId, lastTurnIdRef.current))
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setConnected(true)
      setError(null)
      onConnect?.()
    }

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)
        if (data.turn_id) {
          setLastTurnId(data.turn_id)
        }
        onEvent?.(data)
      } catch (e) {
        console.error('Failed to parse SSE event:', e)
      }
    }

    eventSource.onerror = (e) => {
      setConnected(false)
      const err = new Error('SSE connection error')
      setError(err)
      onError?.(err)
      onDisconnect?.()

      // Auto reconnect after 3 seconds
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      reconnectTimeoutRef.current = setTimeout(() => {
        if (sessionId) {
          connect()
        }
      }, 3000)
    }
  }, [sessionId, onEvent, onError, onConnect, onDisconnect])

  useEffect(() => {
    lastTurnIdRef.current = lastTurnId
  }, [lastTurnId])

  useEffect(() => {
    if (sessionId) {
      connect()
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      setConnected(false)
    }
  }, [sessionId, connect])

  const reconnect = useCallback(() => {
    if (sessionId) {
      connect()
    }
  }, [sessionId, connect])

  return { connected, error, reconnect }
}

interface UseProjectStateResult {
  state: import('./api-types').ProjectState | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

export function useProjectState(
  projectId: string | null,
  pollInterval: number = 0
): UseProjectStateResult {
  const [state, setState] = useState<import('./api-types').ProjectState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchState = useCallback(async () => {
    if (!projectId) return

    setLoading(true)
    try {
      const response = await api.getProjectState(projectId)
      if (response.ok && response.data) {
        setState(response.data)
        setError(null)
      } else {
        setError(new Error(response.error || 'Failed to fetch project state'))
      }
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (projectId) {
      fetchState()

      if (pollInterval > 0) {
        intervalRef.current = setInterval(fetchState, pollInterval)
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [projectId, pollInterval, fetchState])

  return { state, loading, error, refetch: fetchState }
}
