'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useProjectStore } from '@/store/project-store'
import { api } from '@/lib/api-client'
import type { DemoStatus, Project } from '@/lib/api-types'
import { useApiBaseHref } from '@/lib/use-api-base-href'
import { KEEMART_PROJECT_ID, KEEMART_PROJECT_NAME } from '@/features/demo/keemart-demo-data'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Modal,
  ModalTrigger,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  ModalClose,
} from '@/components/ui/modal'
import { AlertTriangle, Plus, FolderOpen, Clock, ChevronRight, Sparkles, Trash2 } from 'lucide-react'

export default function ProjectsPage() {
  const { projects, loading, error, loadProjects, createProject, deleteProject } = useProjectStore()
  const [open, setOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null)
  const hrefFor = useApiBaseHref()
  const openCreateDialog = () => setOpen(true)

  useEffect(() => {
    loadProjects()
    api.getDemoStatus().then((response) => {
      if (response.ok && response.data) {
        setDemoStatus(response.data)
      }
    })
  }, [loadProjects])

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return
    setCreating(true)
    const project = await createProject(newProjectName.trim())
    setCreating(false)
    if (project) {
      setOpen(false)
      setNewProjectName('')
    }
  }

  const handleDeleteProject = async () => {
    if (!projectToDelete) return
    setDeleting(true)
    const deleted = await deleteProject(projectToDelete.id)
    setDeleting(false)
    if (deleted) {
      setDeleteOpen(false)
      setProjectToDelete(null)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">项目</h1>
          <p className="text-muted-foreground mt-1">
            管理你的商业分析项目。
          </p>
        </div>
        <Modal open={open} onOpenChange={setOpen}>
          <ModalTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              新建项目
            </Button>
          </ModalTrigger>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>新建项目</ModalTitle>
              <ModalDescription>
                为新的商业分析项目输入名称。
              </ModalDescription>
            </ModalHeader>
            <div className="py-4">
              <Input
                placeholder="项目名称"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                autoFocus
              />
            </div>
            <ModalFooter>
              <ModalClose asChild>
                <Button variant="outline">取消</Button>
              </ModalClose>
              <Button onClick={handleCreateProject} disabled={!newProjectName.trim() || creating}>
                {creating ? '创建中...' : '创建项目'}
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
        <Modal open={deleteOpen} onOpenChange={setDeleteOpen}>
          <ModalContent>
            <ModalHeader>
              <ModalTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                删除项目
              </ModalTitle>
              <ModalDescription>
                将删除项目“{projectToDelete?.name || ''}”及其 workspace、会话、产物和报告记录。此操作无法撤销。
              </ModalDescription>
            </ModalHeader>
            <ModalFooter>
              <ModalClose asChild>
                <Button variant="outline" disabled={deleting}>取消</Button>
              </ModalClose>
              <Button variant="destructive" onClick={handleDeleteProject} disabled={deleting || !projectToDelete}>
                {deleting ? '删除中...' : '确认删除'}
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {demoStatus?.enabled && (
        <Card className="mb-6 border-primary/30 bg-primary/5">
          <CardContent className="flex flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-primary/10 p-2">
                <Sparkles className="h-5 w-5 text-primary" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium">真实 Agent 工作区</p>
                  <span className="rounded-md bg-primary px-2 py-0.5 text-xs text-primary-foreground">LLM 驱动</span>
                </div>
                <p className="text-sm text-muted-foreground">{demoStatus.project_name}</p>
              </div>
            </div>
            <Link href={hrefFor(`/projects/${demoStatus.project_id}/agent`)}>
              <Button>
                <Sparkles className="mr-2 h-4 w-4" />
                进入真实分析
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <Card className="mb-6 border-border bg-card">
        <CardContent className="flex flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-secondary p-2">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-medium">独立报告演示</p>
              <p className="text-sm text-muted-foreground">{KEEMART_PROJECT_NAME}</p>
            </div>
          </div>
          <Link href={hrefFor(`/projects/${KEEMART_PROJECT_ID}/dashboard`)}>
            <Button variant="outline">
              <Sparkles className="mr-2 h-4 w-4" />
              打开演示看板
            </Button>
          </Link>
        </CardContent>
      </Card>

      {loading && projects.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">正在加载项目...</div>
        </div>
      ) : projects.length === 0 ? (
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle>暂无项目</CardTitle>
            <CardDescription>
              创建第一个项目，开始商业分析流程。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" onClick={openCreateDialog}>
              <Plus className="h-4 w-4 mr-2" />
              创建项目
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Card key={project.id} className="hover:border-primary/50 transition-colors h-full">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <FolderOpen className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="truncate text-lg">{project.name}</CardTitle>
                      {project.description && (
                        <CardDescription className="line-clamp-2 mt-1">
                          {project.description}
                        </CardDescription>
                      )}
                    </div>
                  </div>
                  <Link href={hrefFor(`/projects/${project.id}`)} aria-label={`进入项目 ${project.name}`}>
                    <Button variant="ghost" size="sm" className="h-8 w-8 px-0">
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {project.created_at ? new Date(project.created_at).toLocaleDateString() : '暂无'}
                    </span>
                    <span className="px-2 py-0.5 bg-secondary rounded-full">
                      {project.status}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => {
                      setProjectToDelete(project)
                      setDeleteOpen(true)
                    }}
                  >
                    <Trash2 className="mr-1.5 h-4 w-4" />
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
