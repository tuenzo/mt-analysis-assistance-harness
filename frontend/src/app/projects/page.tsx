'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useProjectStore } from '@/store/project-store'
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
import { Plus, FolderOpen, Clock, ChevronRight } from 'lucide-react'

export default function ProjectsPage() {
  const { projects, loading, error, loadProjects, createProject } = useProjectStore()
  const [open, setOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    loadProjects()
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

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground mt-1">
            Manage your business analysis projects
          </p>
        </div>
        <Modal open={open} onOpenChange={setOpen}>
          <ModalTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </ModalTrigger>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>Create New Project</ModalTitle>
              <ModalDescription>
                Enter a name for your new business analysis project.
              </ModalDescription>
            </ModalHeader>
            <div className="py-4">
              <Input
                placeholder="Project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                autoFocus
              />
            </div>
            <ModalFooter>
              <ModalClose asChild>
                <Button variant="outline">Cancel</Button>
              </ModalClose>
              <Button onClick={handleCreateProject} disabled={!newProjectName.trim() || creating}>
                {creating ? 'Creating...' : 'Create Project'}
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

      {loading && projects.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">Loading projects...</div>
        </div>
      ) : projects.length === 0 ? (
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle>No projects yet</CardTitle>
            <CardDescription>
              Create your first project to get started with business analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Modal open={open} onOpenChange={setOpen}>
              <ModalTrigger asChild>
                <Button className="w-full">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              </ModalTrigger>
              <ModalContent>
                <ModalHeader>
                  <ModalTitle>Create New Project</ModalTitle>
                  <ModalDescription>
                    Enter a name for your new business analysis project.
                  </ModalDescription>
                </ModalHeader>
                <div className="py-4">
                  <Input
                    placeholder="Project name"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                    autoFocus
                  />
                </div>
                <ModalFooter>
                  <ModalClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </ModalClose>
                  <Button onClick={handleCreateProject} disabled={!newProjectName.trim() || creating}>
                    {creating ? 'Creating...' : 'Create Project'}
                  </Button>
                </ModalFooter>
              </ModalContent>
            </Modal>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <FolderOpen className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{project.name}</CardTitle>
                        {project.description && (
                          <CardDescription className="line-clamp-2 mt-1">
                            {project.description}
                          </CardDescription>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {project.created_at ? new Date(project.created_at).toLocaleDateString() : 'N/A'}
                    </span>
                    <span className="px-2 py-0.5 bg-secondary rounded-full">
                      {project.status}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
