'use client'

import { Bell, Bot, ChevronDown, CircleHelp, User } from 'lucide-react'
import { usePathname } from 'next/navigation'
import { useProjectStore } from '@/store/project-store'
import { KEEMART_PROJECT_NAME, isKeemartPromoProject } from '@/features/demo/keemart-demo-data'
import { KEEMART_SHOWCASE_MODEL_NAME, MODEL_LOADING_LABEL } from '@/lib/model-display'
import { useAgentRuntimeMetadata } from '@/lib/use-agent-runtime-metadata'

export function Header() {
  const pathname = usePathname()
  const { currentProject } = useProjectStore()
  const isProjectRoute = pathname.startsWith('/projects/')
  const projectId = pathname.match(/^\/projects\/([^/]+)/)?.[1]
  const isKeemartProject = isKeemartPromoProject(projectId)
  const { metadata: runtimeMetadata } = useAgentRuntimeMetadata(!isKeemartProject)
  const modelName = isKeemartProject ? KEEMART_SHOWCASE_MODEL_NAME : runtimeMetadata?.model || MODEL_LOADING_LABEL
  const projectName =
    isKeemartProject
      ? KEEMART_PROJECT_NAME
      : currentProject?.name ?? (isProjectRoute ? 'Keemart 促销增长全流程项目' : '商业分析伴随式工作区')
  const projectStatus = isKeemartProject
    ? 'report_ready · analysis_ready'
    : currentProject
      ? [currentProject.status, currentProject.current_stage].filter(Boolean).join(' · ')
      : isProjectRoute
        ? 'report_ready · report_ready'
        : '工作区'

  return (
    <header className="app-font-scale-80 flex h-[56px] min-w-0 shrink-0 items-center justify-between gap-4 border-b border-border bg-gradient-to-r from-white via-[#fffaf0] to-white px-4 py-1 md:px-7">
      <div className="flex min-w-0 items-center gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-bold tracking-normal">{projectName}</h1>
          <p className="mt-1 text-xs font-medium text-muted-foreground">
            {projectStatus}
          </p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <div
          className="flex items-center gap-2 rounded-xl border border-[#f2cf4a] bg-[#fff7d6] px-3 py-1.5 text-xs font-bold text-[#5f4a00] shadow-sm"
          title={`当前推理模型：${modelName}`}
        >
          <Bot className="h-4 w-4" />
          <span className="hidden text-[10px] uppercase tracking-wide text-[#8a6b00] sm:inline">Model</span>
          <span>{modelName}</span>
        </div>
        <button
          className="relative rounded-lg p-2 text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          aria-label="通知"
          title="通知"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-destructive" />
        </button>
        <button
          className="hidden items-center gap-1 rounded-lg p-2 text-sm font-semibold text-foreground transition-colors hover:bg-accent hover:text-accent-foreground sm:flex"
          aria-label="帮助"
          title="帮助"
        >
          <CircleHelp className="h-4 w-4" />
          <span>帮助</span>
        </button>
        <button
          className="flex items-center gap-2 rounded-lg p-1.5 text-sm font-bold transition-colors hover:bg-accent"
          aria-label="用户菜单"
          title="用户菜单"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#d8e5ff] text-xs text-[#315991]">
            <User className="h-4 w-4" />
          </span>
          <span className="hidden sm:inline">辛苦了</span>
          <ChevronDown className="hidden h-3.5 w-3.5 text-muted-foreground sm:block" />
        </button>
      </div>
    </header>
  )
}
