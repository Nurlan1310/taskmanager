import { create } from 'zustand'
import api from '@/lib/api'
import { Employee } from '@/types/task'

interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_superuser?: boolean
  employee?: Employee
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (username: string, password: string) => {
    try {
      const response = await api.post('/auth/login/', { username, password })
      // API возвращает данные пользователя напрямую, а не в поле user
      set({ user: response.data, isAuthenticated: true })
    } catch (error) {
      throw error
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout/')
      set({ user: null, isAuthenticated: false })
    } catch (error) {
      console.error('Logout error:', error)
    }
  },

  checkAuth: async () => {
    try {
      const response = await api.get('/auth/me/')
      set({ user: response.data, isAuthenticated: true, isLoading: false })
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },
}))

