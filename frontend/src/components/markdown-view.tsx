'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownViewProps {
  content: string
  compact?: boolean
  className?: string
}

export function MarkdownView({ content, compact = false, className = '' }: MarkdownViewProps) {
  const baseText = compact ? 'text-sm leading-6' : 'text-sm leading-7'

  return (
    <div className={`markdown-view overflow-x-auto ${baseText} ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (props) => (
            <h1 {...props} className="mb-3 mt-1 text-xl font-semibold leading-tight" />
          ),
          h2: (props) => (
            <h2 {...props} className="mb-2 mt-5 text-lg font-semibold leading-tight" />
          ),
          h3: (props) => (
            <h3 {...props} className="mb-2 mt-4 text-base font-semibold leading-tight" />
          ),
          p: (props) => (
            <p {...props} className="mb-3 last:mb-0" />
          ),
          ul: (props) => (
            <ul {...props} className="mb-3 list-disc space-y-1 pl-5" />
          ),
          ol: (props) => (
            <ol {...props} className="mb-3 list-decimal space-y-1 pl-5" />
          ),
          li: (props) => (
            <li {...props} className="pl-1" />
          ),
          blockquote: (props) => (
            <blockquote {...props} className="my-3 border-l-2 border-primary/40 pl-3 text-muted-foreground" />
          ),
          code: ({ children, ...props }) => (
            <code {...props} className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[0.85em]">
              {children}
            </code>
          ),
          pre: (props) => (
            <pre {...props} className="my-3 overflow-x-auto rounded-md bg-secondary p-3 text-xs leading-5" />
          ),
          table: (props) => (
            <table {...props} className="my-3 min-w-full border-collapse text-left text-xs" />
          ),
          thead: (props) => (
            <thead {...props} className="bg-secondary" />
          ),
          th: (props) => (
            <th {...props} className="border px-3 py-2 font-semibold" />
          ),
          td: (props) => (
            <td {...props} className="border px-3 py-2 align-top" />
          ),
          a: (props) => (
            <a {...props} className="font-medium text-primary underline underline-offset-2" />
          ),
          hr: (props) => (
            <hr {...props} className="my-4 border-border" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
