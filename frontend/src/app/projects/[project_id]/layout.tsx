'use client'

import { useEffect } from 'react'
import { useParams } from 'next/navigation'
import { ProjectTabs } from '@/features/layout/project-tabs'
import { useProjectStore } from '@/store/project-store'

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const params = useParams()
  const projectId = params.project_id as string
  const { selectProject, currentProject } = useProjectStore()

  useEffect(() => {
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      selectProject(projectId)
    }
  }, [projectId, currentProject, selectProject])

  return (
    <div className="flex flex-col h-full">
      <ProjectTabs projectId={projectId} />
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  )
}
