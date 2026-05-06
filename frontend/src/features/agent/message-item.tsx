'use client'

import type { AgentMessage } from '@/lib/api-types'
import { Card, CardContent } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'
import { User, Bot } from 'lucide-react'

interface MessageItemProps {
  message: AgentMessage
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
          <Bot className="h-4 w-4 text-primary" />
        </div>
      )}

      <Card
        className={`max-w-[80%] ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-card'
        }`}
      >
        <CardContent className="p-3">
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm">{message.content}</p>
          ) : (
            <MarkdownView content={message.content} compact />
          )}
          {message.created_at && (
            <p
              className={`text-xs mt-2 ${
                isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
              }`}
            >
              {new Date(message.created_at).toLocaleTimeString()}
            </p>
          )}
        </CardContent>
      </Card>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
          <User className="h-4 w-4 text-primary-foreground" />
        </div>
      )}
    </div>
  )
}
