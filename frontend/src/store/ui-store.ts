import { create } from 'zustand'
import type { Notification } from '@/lib/api-types'

interface UIStore {
  sidebarCollapsed: boolean
  currentView: string
  notifications: Notification[]

  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setCurrentView: (view: string) => void
  addNotification: (notification: Omit<Notification, 'id' | 'created_at'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarCollapsed: false,
  currentView: 'home',
  notifications: [],

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSidebarCollapsed: (collapsed: boolean) =>
    set({ sidebarCollapsed: collapsed }),

  setCurrentView: (view: string) =>
    set({ currentView: view }),

  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        {
          ...notification,
          id: `notif_${Date.now()}`,
          created_at: new Date().toISOString(),
        },
      ],
    })),

  removeNotification: (id: string) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () =>
    set({ notifications: [] }),
}))
