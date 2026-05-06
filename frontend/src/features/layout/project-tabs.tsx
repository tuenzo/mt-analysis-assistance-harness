'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Database, Bot, Clock, LayoutDashboard, FileText, Brain } from 'lucide-react'

const tabs = [
  { id: 'home', label: 'Home', href: (projectId: string) => `/projects/${projectId}`, icon: Home },
  { id: 'data-intake', label: 'Data Intake', href: (projectId: string) => `/projects/${projectId}/data-intake`, icon: Database },
  { id: 'agent', label: 'Agent', href: (projectId: string) => `/projects/${projectId}/agent`, icon: Bot },
  { id: 'timeline', label: 'Timeline', href: (projectId: string) => `/projects/${projectId}/timeline`, icon: Clock },
  { id: 'dashboard', label: 'Dashboard', href: (projectId: string) => `/projects/${projectId}/dashboard`, icon: LayoutDashboard },
  { id: 'reports', label: 'Reports', href: (projectId: string) => `/projects/${projectId}/reports`, icon: FileText },
  { id: 'memory', label: 'Memory', href: (projectId: string) => `/projects/${projectId}/memory`, icon: Brain },
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
    <nav className="flex min-w-0 items-center gap-1 overflow-x-auto border-b bg-card px-4">
      {tabs.map((tab) => {
        const Icon = tab.icon
        const active = isActive(tab.id)

        return (
          <Link
            key={tab.id}
            href={tab.href(projectId)}
            className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
              active
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
            }`}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
