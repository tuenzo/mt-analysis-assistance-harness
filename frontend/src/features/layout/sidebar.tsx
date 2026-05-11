'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  Bot,
  Brain,
  CalendarClock,
  FileText,
  FolderOpen,
  Home,
  Inbox,
  LayoutDashboard,
  FolderCog,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
} from 'lucide-react'
import { useApiBaseHref } from '@/lib/use-api-base-href'
import { useProjectStore } from '@/store/project-store'
import { KEEMART_PROJECT_ID, KEEMART_PROJECT_NAME } from '@/features/demo/keemart-demo-data'

const navItems = [
  { key: 'overview', label: '概览', route: (projectId: string) => `/projects/${projectId}`, icon: Home },
  { key: 'data-ingestion', label: '数据接入', route: (projectId: string) => `/projects/${projectId}/data-intake`, icon: Inbox },
  { key: 'agent-analysis', label: 'Agent 分析', route: (projectId: string) => `/projects/${projectId}/agent`, icon: Bot },
  { key: 'dashboard', label: '结果看板', route: (projectId: string) => `/projects/${projectId}/dashboard`, icon: LayoutDashboard },
  { key: 'timeline', label: '时间线', route: (projectId: string) => `/projects/${projectId}/timeline`, icon: CalendarClock },
  { key: 'report', label: '报告', route: (projectId: string) => `/projects/${projectId}/reports`, icon: FileText },
  { key: 'memory', label: '记忆', route: (projectId: string) => `/projects/${projectId}/memory`, icon: Brain },
]

const fallbackRecentProjects = [
  { id: KEEMART_PROJECT_ID, name: KEEMART_PROJECT_NAME },
  { id: 'promo-growth-project', name: 'Keemart 促销增长全流程项目' },
  { id: 'monthly-review-project', name: '月末促销复盘项目' },
]

function displayProjectName(name: string) {
  return name
    .replace(/\s*Demo\b/gi, '')
    .replace(/演示\s*/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function getProjectIdFromPathname(pathname: string) {
  const match = pathname.match(/^\/projects\/([^/]+)/)
  return match?.[1] ?? ''
}

export function Sidebar() {
  const pathname = usePathname()
  const hrefFor = useApiBaseHref()
  const { projects, loadProjects } = useProjectStore()
  const [collapsed, setCollapsed] = useState(() =>
    typeof window !== 'undefined' && window.localStorage.getItem('baa.sidebarCollapsed') === 'true',
  )
  const projectId = getProjectIdFromPathname(pathname) || projects[0]?.id || ''
  const recentProjects =
    projects.length > 0
      ? [
          { id: KEEMART_PROJECT_ID, name: KEEMART_PROJECT_NAME },
          ...projects.filter((project) => project.id !== KEEMART_PROJECT_ID),
        ].slice(0, 4)
      : fallbackRecentProjects

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  function toggleCollapsed() {
    setCollapsed((current) => {
      const next = !current
      window.localStorage.setItem('baa.sidebarCollapsed', String(next))
      return next
    })
  }

  return (
    <aside className={`app-font-scale-80 hidden shrink-0 flex-col border-r border-border bg-card text-card-foreground shadow-[8px_0_30px_rgba(31,41,55,0.04)] transition-[width] duration-200 md:flex ${collapsed ? 'w-20' : 'w-60'}`}>
      <div className={`border-b border-border py-5 ${collapsed ? 'px-2' : 'px-3'}`}>
        <div className={`flex min-w-0 items-center gap-2 ${collapsed ? 'flex-col justify-center gap-2' : ''}`}>
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-[0.72rem] font-black tracking-tight text-[#241a00] shadow-sm">
            美团
          </span>
          {!collapsed && (
            <div className="min-w-0">
              <span className="block truncate text-sm font-bold">商业分析工作区</span>
              <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">活动评估与决策看板</span>
            </div>
          )}
          <button
            type="button"
            onClick={toggleCollapsed}
            className={`ml-auto rounded-lg p-2 text-muted-foreground transition hover:bg-accent hover:text-accent-foreground ${collapsed ? 'ml-0' : ''}`}
            aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
            title={collapsed ? '展开侧边栏' : '折叠侧边栏'}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <nav className={`flex-1 overflow-y-auto py-4 ${collapsed ? 'px-2' : 'px-3'}`}>
        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const href = projectId ? item.route(projectId) : '/projects'
            const active =
              item.key === 'overview'
                ? pathname === href
                : Boolean(projectId && pathname.startsWith(item.route(projectId)))

            return (
              <Link
                key={item.key}
                href={hrefFor(href)}
                title={item.label}
                className={`group relative flex items-center gap-3 rounded-lg py-2.5 text-sm font-semibold transition ${collapsed ? 'justify-center px-2' : 'px-3'} ${
                  active
                    ? 'bg-secondary text-secondary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                {active && <span className="absolute left-0 top-2 h-6 w-1 rounded-r-full bg-primary" />}
                <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-primary' : 'text-muted-foreground group-hover:text-accent-foreground'}`} />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            )
          })}
        </div>

        {!collapsed && (
          <div className="mt-6">
            <div className="px-3 text-xs font-bold text-muted-foreground">最近项目</div>
            <div className="mt-2 space-y-1">
          {recentProjects.map((project) => {
            const active = pathname.startsWith(`/projects/${project.id}`)
            const projectName = displayProjectName(project.name)
            return (
              <Link
                key={project.id}
                href={hrefFor(`/projects/${project.id}/agent`)}
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs transition ${
                      active
                        ? 'border border-[#f2cf4a] bg-secondary text-secondary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    }`}
                title={projectName}
              >
                <FolderOpen className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{projectName}</span>
              </Link>
            )
          })}
            </div>
          </div>
        )}
      </nav>

      <div className="border-t border-border bg-card p-3">
        <div className="space-y-2">
          <Link
            href={hrefFor('/projects')}
            className="flex h-10 items-center justify-center gap-2 rounded-lg border border-[#f2cf4a] bg-card px-3 text-sm font-bold text-card-foreground transition hover:bg-secondary"
            title="项目管理"
          >
            <FolderCog className="h-4 w-4 text-[#d49700]" />
            {!collapsed && <span>项目管理</span>}
          </Link>
          <button
            className="flex h-10 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold text-muted-foreground transition hover:bg-accent hover:text-accent-foreground"
            title="设置"
          >
            <Settings className="h-4 w-4" />
            {!collapsed && <span>设置</span>}
          </button>
        </div>
      </div>
    </aside>
  )
}
