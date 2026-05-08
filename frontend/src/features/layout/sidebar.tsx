'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect } from 'react'
import {
  BarChart3,
  BellRing,
  Bot,
  Brain,
  CalendarClock,
  FileText,
  FolderOpen,
  Home,
  Inbox,
  LayoutDashboard,
  Plus,
  Settings,
} from 'lucide-react'
import { useApiBaseHref } from '@/lib/use-api-base-href'
import { useProjectStore } from '@/store/project-store'

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
  { id: 'demo-project', name: 'Keemart 促销增长全流程演示 Demo' },
  { id: 'demo-project-2', name: '新项目演示2' },
  { id: 'demo-project-3', name: '新项目' },
]

function getProjectIdFromPathname(pathname: string) {
  const match = pathname.match(/^\/projects\/([^/]+)/)
  return match?.[1] ?? ''
}

export function Sidebar() {
  const pathname = usePathname()
  const hrefFor = useApiBaseHref()
  const { projects, loadProjects } = useProjectStore()
  const projectId = getProjectIdFromPathname(pathname) || projects[0]?.id || ''
  const recentProjects = projects.length > 0 ? projects.slice(0, 4) : fallbackRecentProjects

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-white text-[#1f2937] shadow-[8px_0_30px_rgba(31,41,55,0.04)] md:flex">
      <div className="border-b border-border px-4 py-5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-[#241a00] shadow-sm">
            <BarChart3 className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <span className="block truncate text-sm font-bold">商业分析工作区</span>
            <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">活动评估与决策看板</span>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
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
                className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition ${
                  active
                    ? 'bg-secondary text-[#6f5200] shadow-sm'
                    : 'text-[#4b5563] hover:bg-[#f7f8fa] hover:text-[#111827]'
                }`}
              >
                {active && <span className="absolute left-0 top-2 h-6 w-1 rounded-r-full bg-primary" />}
                <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-[#d39a00]' : 'text-[#6b7280] group-hover:text-[#111827]'}`} />
                <span className="truncate">{item.label}</span>
              </Link>
            )
          })}
        </div>

        <div className="mt-6">
          <div className="px-3 text-xs font-bold text-muted-foreground">最近项目</div>
          <div className="mt-2 space-y-1">
            {recentProjects.map((project) => {
              const active = pathname.startsWith(`/projects/${project.id}`)
              return (
                <Link
                  key={project.id}
                  href={hrefFor(`/projects/${project.id}/agent`)}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs transition ${
                    active
                      ? 'border border-[#f2cf4a] bg-secondary text-[#1f2937]'
                      : 'text-[#4b5563] hover:bg-[#f7f8fa] hover:text-[#111827]'
                  }`}
                  title={project.name}
                >
                  <FolderOpen className="h-3.5 w-3.5 shrink-0 text-[#6b7280]" />
                  <span className="truncate">{project.name}</span>
                </Link>
              )
            })}
          </div>
        </div>
      </nav>

      <div className="border-t border-border bg-white p-3">
        <div className="rounded-xl border border-border bg-[#fbfcfe] p-3">
          <div className="flex items-start gap-2">
            <BellRing className="mt-0.5 h-4 w-4 shrink-0 text-[#d39a00]" />
            <div className="min-w-0">
              <p className="text-xs font-semibold">项目状态同步</p>
              <p className="mt-1 text-[11px] leading-4 text-muted-foreground">结果、报告与记忆候选保持在项目内。</p>
            </div>
          </div>
        </div>
        <div className="mt-3 space-y-2">
          <Link
            href={hrefFor('/projects')}
            className="flex h-10 items-center justify-center gap-2 rounded-lg border border-[#f2cf4a] bg-white px-3 text-sm font-bold text-[#1f2937] transition hover:bg-secondary"
            title="新建项目"
          >
            <Plus className="h-4 w-4 text-[#d49700]" />
            <span>新建项目</span>
          </Link>
          <button
            className="flex h-10 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold text-muted-foreground transition hover:bg-[#f7f8fa] hover:text-[#111827]"
            title="设置"
          >
            <Settings className="h-4 w-4" />
            <span>设置</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
