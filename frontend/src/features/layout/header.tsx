'use client'

import { useProjectStore } from '@/store/project-store'
import { User, Bell } from 'lucide-react'

export function Header() {
  const { currentProject } = useProjectStore()

  return (
    <header className="flex min-w-0 items-center justify-between gap-4 border-b bg-card px-6 py-3">
      <div className="flex min-w-0 items-center gap-4">
        {currentProject ? (
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold">{currentProject.name}</h1>
            <p className="text-xs text-muted-foreground">
              {currentProject.status} {currentProject.current_stage && `• ${currentProject.current_stage}`}
            </p>
          </div>
        ) : (
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold">Business Analysis Companion</h1>
            <p className="text-xs text-muted-foreground">
              Workspace
            </p>
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-4">
        <button
          className="p-2 hover:bg-accent rounded-md transition-colors"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <button
          className="flex items-center gap-2 p-2 hover:bg-accent rounded-md transition-colors"
          aria-label="User menu"
        >
          <User className="h-4 w-4" />
          <span className="text-sm">User</span>
        </button>
      </div>
    </header>
  )
}
