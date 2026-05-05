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
  turnId: string | null,
  options: UseAgentEventsOptions = {}
): UseAgentEventsResult {
  const { onEvent, onError, onConnect, onDisconnect } = options
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [lastTurnId, setLastTurnId] = useState<string | null>(null)
  const [reconnectNonce, setReconnectNonce] = useState(0)
  const lastTurnIdRef = useRef<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const didReceiveTerminalEventRef = useRef(false)
  const onEventRef = useRef(onEvent)
  const onErrorRef = useRef(onError)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)

  useEffect(() => {
    onEventRef.current = onEvent
    onErrorRef.current = onError
    onConnectRef.current = onConnect
    onDisconnectRef.current = onDisconnect
  }, [onEvent, onError, onConnect, onDisconnect])

  const connect = useCallback(() => {
    if (!sessionId) return

    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
    didReceiveTerminalEventRef.current = false

    const resumeTurnId = turnId || lastTurnIdRef.current
    const eventSource = new EventSource(api.getSessionEventsUrl(sessionId, resumeTurnId))
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setConnected(true)
      setError(null)
      onConnectRef.current?.()
    }

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)
        if (data.turn_id) {
          lastTurnIdRef.current = data.turn_id
          setLastTurnId(data.turn_id)
        }
        onEventRef.current?.(data)
        if (data.type === 'final_answer' || data.type === 'error' || data.type === 'runtime_error') {
          didReceiveTerminalEventRef.current = true
          eventSource.close()
          if (eventSourceRef.current === eventSource) {
            eventSourceRef.current = null
          }
          setConnected(false)
        }
      } catch (e) {
        console.error('Failed to parse SSE event:', e)
      }
    }

    eventSource.onerror = () => {
      if (didReceiveTerminalEventRef.current) {
        eventSource.close()
        if (eventSourceRef.current === eventSource) {
          eventSourceRef.current = null
        }
        setConnected(false)
        onDisconnectRef.current?.()
        return
      }

      setConnected(false)
      const err = new Error('SSE connection error')
      setError(err)
      onErrorRef.current?.(err)
      onDisconnectRef.current?.()

      // Auto reconnect after 3 seconds
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      reconnectTimeoutRef.current = setTimeout(() => {
        if (sessionId) {
          setReconnectNonce((value) => value + 1)
        }
      }, 3000)
    }
  }, [sessionId, turnId])

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
  }, [sessionId, turnId, reconnectNonce, connect])

  const reconnect = useCallback(() => {
    if (sessionId) {
      setReconnectNonce((value) => value + 1)
    }
  }, [sessionId])

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
    let initialFetchTimeout: NodeJS.Timeout | null = null

    if (projectId) {
      initialFetchTimeout = setTimeout(() => {
        void fetchState()
      }, 0)

      if (pollInterval > 0) {
        intervalRef.current = setInterval(fetchState, pollInterval)
      }
    }

    return () => {
      if (initialFetchTimeout) {
        clearTimeout(initialFetchTimeout)
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [projectId, pollInterval, fetchState])

  return { state, loading, error, refetch: fetchState }
}
