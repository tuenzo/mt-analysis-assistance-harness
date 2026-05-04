import { create } from 'zustand'
import type { Project, ProjectState, ProjectFile } from '@/lib/api-types'
import { api } from '@/lib/api-client'

interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  projectState: ProjectState | null
  files: ProjectFile[]
  loading: boolean
  error: string | null

  loadProjects: () => Promise<void>
  selectProject: (projectId: string) => Promise<void>
  loadProjectState: (projectId: string) => Promise<void>
  loadFiles: (projectId: string) => Promise<void>
  createProject: (name: string, domain?: string, description?: string) => Promise<Project | null>
  clearError: () => void
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  currentProject: null,
  projectState: null,
  files: [],
  loading: false,
  error: null,

  loadProjects: async () => {
    set({ loading: true, error: null })
    try {
      const response = await api.listProjects()
      if (response.ok && response.data) {
        set({ projects: response.data, loading: false })
      } else {
        set({ error: response.error || 'Failed to load projects', loading: false })
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Unknown error', loading: false })
    }
  },

  selectProject: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      const response = await api.getProject(projectId)
      if (response.ok && response.data) {
        set({ currentProject: response.data, loading: false })
        // Also load project state and files
        get().loadProjectState(projectId)
        get().loadFiles(projectId)
      } else {
        set({ error: response.error || 'Failed to load project', loading: false })
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Unknown error', loading: false })
    }
  },

  loadProjectState: async (projectId: string) => {
    try {
      const response = await api.getProjectState(projectId)
      if (response.ok && response.data) {
        set({ projectState: response.data })
      }
    } catch (e) {
      console.error('Failed to load project state:', e)
    }
  },

  loadFiles: async (projectId: string) => {
    try {
      const response = await api.listFiles(projectId)
      if (response.ok && response.data) {
        set({ files: response.data })
      }
    } catch (e) {
      console.error('Failed to load files:', e)
    }
  },

  createProject: async (name: string, domain?: string, description?: string) => {
    set({ loading: true, error: null })
    try {
      const response = await api.createProject(name, domain, description)
      if (response.ok && response.data) {
        set((state) => ({
          projects: [...state.projects, response.data!],
          loading: false,
        }))
        return response.data
      } else {
        set({ error: response.error || 'Failed to create project', loading: false })
        return null
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Unknown error', loading: false })
      return null
    }
  },

  clearError: () => set({ error: null }),
}))
