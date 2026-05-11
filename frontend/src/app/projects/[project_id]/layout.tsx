'use client'

import { useEffect } from 'react'
import { useParams, usePathname, useRouter } from 'next/navigation'
import { useProjectStore } from '@/store/project-store'
import { KEEMART_PROJECT_ID, KEEMART_PROJECT_LEGACY_ID, isKeemartPromoProject } from '@/features/demo/keemart-demo-data'

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const params = useParams()
  const projectId = params.project_id as string
  const pathname = usePathname()
  const router = useRouter()
  const { selectProject, currentProject } = useProjectStore()

  useEffect(() => {
    if (projectId === KEEMART_PROJECT_LEGACY_ID) {
      router.replace(pathname.replace(`/projects/${KEEMART_PROJECT_LEGACY_ID}`, `/projects/${KEEMART_PROJECT_ID}`))
      return
    }
    if (isKeemartPromoProject(projectId)) return
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      selectProject(projectId)
    }
  }, [projectId, pathname, router, currentProject, selectProject])

  return (
    <div className="flex h-full min-w-0 flex-col">
      <div className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
