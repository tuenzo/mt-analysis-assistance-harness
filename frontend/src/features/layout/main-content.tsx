'use client'

import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

function isDashboardPath(pathname: string) {
  return /^\/projects\/[^/]+\/dashboard(?:\/|$)/.test(pathname)
}

export function MainContent({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const shouldScaleFonts = !isDashboardPath(pathname)

  return (
    <main className={`flex-1 overflow-x-hidden overflow-y-auto bg-background ${shouldScaleFonts ? 'app-font-scale-80' : ''}`}>
      {children}
    </main>
  )
}
