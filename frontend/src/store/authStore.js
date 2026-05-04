import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authAPI } from '../services/api'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      
      login: async (credentials) => {
        set({ isLoading: true })
        try {
          const response = await authAPI.login(credentials)
          const { access_token, refresh_token } = response.data
          
          // Get user info
          const userResponse = await authAPI.getCurrentUser(access_token)
          
          set({
            user: userResponse.data,
            token: access_token,
            refreshToken: refresh_token,
            isLoading: false
          })
          
          return { success: true }
        } catch (error) {
          set({ isLoading: false })
          return { 
            success: false, 
            error: error.response?.data?.detail || 'Login failed' 
          }
        }
      },
      
      register: async (userData) => {
        set({ isLoading: true })
        try {
          await authAPI.register(userData)
          set({ isLoading: false })
          return { success: true }
        } catch (error) {
          set({ isLoading: false })
          return { 
            success: false, 
            error: error.response?.data?.detail || 'Registration failed' 
          }
        }
      },
      
      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null
        })
      },
      
      checkAuth: async () => {
        const { token } = get()
        if (!token) return
        
        try {
          const response = await authAPI.getCurrentUser(token)
          set({ user: response.data })
        } catch (error) {
          // Token is invalid, logout
          get().logout()
        }
      },
      
      updateUser: (userData) => {
        set(state => ({
          user: { ...state.user, ...userData }
        }))
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken
      })
    }
  )
)

export { useAuthStore }
