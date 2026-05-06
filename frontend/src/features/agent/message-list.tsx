'use client'

import { useRef, useEffect } from 'react'
import type { AgentMessage } from '@/lib/api-types'
import { MessageItem } from './message-item'

interface MessageListProps {
  messages: AgentMessage[]
  isRunning?: boolean
}

export function MessageList({ messages, isRunning }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    containerRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="p-4 bg-primary/10 rounded-full mb-4">
          <svg
            className="h-8 w-8 text-primary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium mb-2">开始一次分析对话</h3>
        <p className="text-muted-foreground max-w-md">
          向 Agent 描述你的分析目标。它会根据项目状态协助接入数据、运行分析 pipeline，并生成可复核的结论和报告。
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
      {isRunning && (
        <div className="flex gap-3 justify-start">
          <div className="bg-card border rounded-lg px-4 py-3">
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span>Agent 正在分析...</span>
            </div>
          </div>
        </div>
      )}
      <div ref={containerRef} />
    </div>
  )
}
