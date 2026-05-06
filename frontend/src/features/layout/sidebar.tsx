'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useProjectStore } from '@/store/project-store'
import { useUIStore } from '@/store/ui-store'
import { ChevronLeft, ChevronRight, FolderOpen, Plus, Settings } from 'lucide-react'
import { useEffect } from 'react'

export function Sidebar() {
  const pathname = usePathname()
  const { projects, loadProjects } = useProjectStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  const isProjectRoute = pathname.startsWith('/projects/')

  return (
    <aside
      className={`flex shrink-0 flex-col border-r bg-card transition-all duration-300 ${
        sidebarCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex items-center justify-between border-b p-4">
        {!sidebarCollapsed && (
          <span className="font-semibold text-sm">Projects</span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1 hover:bg-accent rounded"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {!sidebarCollapsed && (
            <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Recent Projects
            </div>
          )}

          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                isProjectRoute && pathname.includes(project.id)
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title={project.name}
            >
              <FolderOpen className="h-4 w-4 flex-shrink-0" />
              {!sidebarCollapsed && (
                <span className="truncate">{project.name}</span>
              )}
            </Link>
          ))}

          {projects.length === 0 && !sidebarCollapsed && (
            <div className="px-3 py-4 text-center text-xs text-muted-foreground">
              No projects yet
            </div>
          )}
        </div>
      </nav>

      <div className="border-t p-2">
        <Link
          href="/projects"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          title="New Project"
        >
          <Plus className="h-4 w-4" />
          {!sidebarCollapsed && <span>New Project</span>}
        </Link>
        <button
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          title="Settings"
        >
          <Settings className="h-4 w-4" />
          {!sidebarCollapsed && <span>Settings</span>}
        </button>
      </div>
    </aside>
  )
}
