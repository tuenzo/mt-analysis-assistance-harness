'use client'

import { useProjectStore } from '@/store/project-store'
import { Bell, User } from 'lucide-react'

export function Header() {
  const { currentProject } = useProjectStore()
  const projectStatus = currentProject
    ? [currentProject.status, currentProject.current_stage].filter(Boolean).join(' - ')
    : '工作区'

  return (
    <header className="flex min-w-0 items-center justify-between gap-3 border-b border-[#f2cf4a]/60 border-t-2 border-t-primary bg-[#ffd100]/20 px-3 py-2 shadow-sm shadow-[#d6a500]/10 backdrop-blur md:px-5">
      <div className="flex min-w-0 items-center gap-4">
        {currentProject ? (
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold">{currentProject.name}</h1>
            <p className="text-[11px] text-muted-foreground">
              {projectStatus}
            </p>
          </div>
        ) : (
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold">商业分析伴随式工作区</h1>
            <p className="text-[11px] text-muted-foreground">
              {projectStatus}
            </p>
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1.5 md:gap-2">
        <button
          className="rounded-md p-1.5 transition-colors hover:bg-accent"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <button
          className="flex items-center gap-2 rounded-md p-1.5 transition-colors hover:bg-accent"
          aria-label="User menu"
        >
          <User className="h-4 w-4" />
          <span className="hidden text-sm sm:inline">用户</span>
        </button>
      </div>
    </header>
  )
}
