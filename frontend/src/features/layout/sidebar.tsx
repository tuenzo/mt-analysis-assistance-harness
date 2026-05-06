'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useProjectStore } from '@/store/project-store'
import { useUIStore } from '@/store/ui-store'
import { preserveApiBaseParam, readApiBaseQueryFromLocation } from '@/lib/navigation'
import { ChevronLeft, ChevronRight, FolderOpen, Plus, Settings } from 'lucide-react'
import { useEffect, useState } from 'react'

export function Sidebar() {
  const pathname = usePathname()
  const { projects, loadProjects } = useProjectStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const [apiBaseQuery, setApiBaseQuery] = useState('')
  const hrefFor = (href: string) => preserveApiBaseParam(href, apiBaseQuery)

  useEffect(() => {
    setApiBaseQuery(readApiBaseQueryFromLocation())
  }, [pathname])

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  const isProjectRoute = pathname.startsWith('/projects/')

  return (
    <aside
      className={`hidden shrink-0 flex-col border-r border-[#e7b900] bg-[#ffd100] text-[#241a00] transition-all duration-300 md:flex ${
        sidebarCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex items-center justify-between border-b border-[#e7b900] p-4">
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold">商业分析工作区</span>
            <span className="block truncate text-[11px] font-medium text-[#6f5600]">活动评估与决策看板</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded p-1 text-[#4f3a00] transition-colors hover:bg-white/35 hover:text-[#1f2329]"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto bg-white p-2">
        <div className="space-y-1">
          {!sidebarCollapsed && (
            <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-[#646a73]">
              最近项目
            </div>
          )}

          {projects.map((project) => (
            <Link
              key={project.id}
              href={hrefFor(`/projects/${project.id}`)}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                isProjectRoute && pathname.includes(project.id)
                  ? 'bg-[#fff7cc] text-[#1f2329] shadow-sm ring-1 ring-[#f2cf4a]'
                  : 'text-[#4f5560] hover:bg-[#fff7cc] hover:text-[#1f2329]'
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
            <div className="px-3 py-4 text-center text-xs text-[#8a8f99]">
              暂无项目
            </div>
          )}
        </div>
      </nav>

      <div className="border-t border-[#e6e8eb] bg-white p-2">
        <Link
          href={hrefFor('/projects')}
          className="flex items-center gap-2 rounded-md border border-[#f2cf4a] bg-white px-3 py-2 text-sm font-semibold text-[#1f2329] transition-colors hover:bg-[#fff7cc]"
          title="新建项目"
        >
          <Plus className="h-4 w-4 text-[#d49700]" />
          {!sidebarCollapsed && <span>新建项目</span>}
        </Link>
        <button
          className="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-[#646a73] transition-colors hover:bg-[#f7f8fa] hover:text-[#1f2329]"
          title="设置"
        >
          <Settings className="h-4 w-4" />
          {!sidebarCollapsed && <span>设置</span>}
        </button>
      </div>
    </aside>
  )
}
