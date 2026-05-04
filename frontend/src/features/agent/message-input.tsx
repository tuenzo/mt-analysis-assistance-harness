'use client'

import { useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Square, Loader2 } from 'lucide-react'

interface MessageInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onInterrupt?: () => void
  disabled?: boolean
  isRunning?: boolean
}

export function MessageInput({
  value,
  onChange,
  onSend,
  onInterrupt,
  disabled,
  isRunning,
}: MessageInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="border-t p-4 bg-card">
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          disabled={disabled || isRunning}
          className="flex-1 min-h-[40px] max-h-[200px] resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          rows={1}
        />
        {isRunning ? (
          <Button
            onClick={onInterrupt}
            variant="destructive"
            disabled={!onInterrupt}
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            onClick={onSend}
            disabled={!value.trim() || disabled}
          >
            <Send className="h-4 w-4 mr-2" />
            Send
          </Button>
        )}
      </div>
      {isRunning && (
        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Agent is thinking...
        </div>
      )}
    </div>
  )
}
