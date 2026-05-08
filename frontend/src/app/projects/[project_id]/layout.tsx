'use client'

import { useEffect } from 'react'
import { useParams } from 'next/navigation'
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
    <div className="flex h-full min-w-0 flex-col">
      <div className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
