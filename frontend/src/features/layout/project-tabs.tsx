'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Database, Bot, Clock, LayoutDashboard, FileText, Brain } from 'lucide-react'

const overviewTab = { id: 'home', label: '概览', href: (projectId: string) => `/projects/${projectId}`, icon: Home }

const primaryTabs = [
  { id: 'data-intake', label: '数据接入', href: (projectId: string) => `/projects/${projectId}/data-intake`, icon: Database },
  { id: 'agent', label: 'Agent 分析', href: (projectId: string) => `/projects/${projectId}/agent`, icon: Bot },
  { id: 'dashboard', label: '结果看板', href: (projectId: string) => `/projects/${projectId}/dashboard`, icon: LayoutDashboard },
]

const reviewTabs = [
  { id: 'timeline', label: '时间线', href: (projectId: string) => `/projects/${projectId}/timeline`, icon: Clock },
  { id: 'reports', label: '报告', href: (projectId: string) => `/projects/${projectId}/reports`, icon: FileText },
  { id: 'memory', label: '记忆', href: (projectId: string) => `/projects/${projectId}/memory`, icon: Brain },
]

interface ProjectTabsProps {
  projectId: string
}

export function ProjectTabs({ projectId }: ProjectTabsProps) {
  const pathname = usePathname()

  const isActive = (tabId: string) => {
    if (tabId === 'home') {
      return pathname === `/projects/${projectId}`
    }
    return pathname.startsWith(`/projects/${projectId}/${tabId}`)
  }

  return (
    <nav className="border-b bg-card px-3 py-2">
      <div className="flex min-w-0 items-center gap-2 overflow-x-auto">
        <Link
          href={overviewTab.href(projectId)}
          className={`flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2 text-sm font-medium transition-colors ${
            isActive(overviewTab.id)
              ? 'bg-secondary text-secondary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          }`}
          title={overviewTab.label}
        >
          <Home className="h-4 w-4" />
          <span className="hidden sm:inline">{overviewTab.label}</span>
        </Link>

        <div className="flex shrink-0 items-center gap-1">
          {primaryTabs.map((tab) => {
            const Icon = tab.icon
            const active = isActive(tab.id)

            return (
              <Link
                key={tab.id}
                href={tab.href(projectId)}
                className={`flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold transition-colors ${
                  active
                    ? 'border-[#d9af00] bg-primary text-primary-foreground shadow-sm'
                    : 'border-transparent text-foreground hover:border-primary/40 hover:bg-secondary'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </Link>
            )
          })}
        </div>

        <div className="h-6 w-px shrink-0 bg-border" />

        <div className="flex shrink-0 items-center gap-1">
          {reviewTabs.map((tab) => {
            const Icon = tab.icon
            const active = isActive(tab.id)

            return (
              <Link
                key={tab.id}
                href={tab.href(projectId)}
                className={`flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-secondary text-secondary-foreground ring-1 ring-primary/50'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
