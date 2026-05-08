'use client'

import { Bell, ChevronDown, CircleHelp, User } from 'lucide-react'
import { useProjectStore } from '@/store/project-store'

export function Header() {
  const { currentProject } = useProjectStore()
  const projectStatus = currentProject
    ? [currentProject.status, currentProject.current_stage].filter(Boolean).join(' · ')
    : '工作区'

  return (
    <header className="flex min-h-[70px] min-w-0 items-center justify-between gap-4 border-b border-border bg-gradient-to-r from-white via-[#fffaf0] to-white px-4 py-3 md:px-7">
      <div className="flex min-w-0 items-center gap-4">
        {currentProject ? (
          <div className="min-w-0">
            <h1 className="truncate text-lg font-bold tracking-normal">{currentProject.name}</h1>
            <p className="mt-1 text-xs font-medium text-muted-foreground">
              {projectStatus}
            </p>
          </div>
        ) : (
          <div className="min-w-0">
            <h1 className="truncate text-lg font-bold tracking-normal">商业分析伴随式工作区</h1>
            <p className="mt-1 text-xs font-medium text-muted-foreground">
              {projectStatus}
            </p>
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          className="relative rounded-lg p-2 text-[#111827] transition-colors hover:bg-white"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-destructive" />
        </button>
        <button
          className="hidden items-center gap-1 rounded-lg p-2 text-sm font-semibold text-[#111827] transition-colors hover:bg-white sm:flex"
          aria-label="Help"
        >
          <CircleHelp className="h-4 w-4" />
          <span>帮助</span>
        </button>
        <button
          className="flex items-center gap-2 rounded-lg p-1.5 text-sm font-bold transition-colors hover:bg-white"
          aria-label="User menu"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#d8e5ff] text-xs text-[#315991]">
            <User className="h-4 w-4" />
          </span>
          <span className="hidden sm:inline">用户</span>
          <ChevronDown className="hidden h-3.5 w-3.5 text-muted-foreground sm:block" />
        </button>
      </div>
    </header>
  )
}
