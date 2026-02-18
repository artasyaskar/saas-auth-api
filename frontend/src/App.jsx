import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import ErrorBoundary from './components/ErrorBoundary'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Security from './pages/Security'
import Analytics from './pages/Analytics'
import AppSettings from './pages/Settings'
import BillingPlan from './components/BillingPlan'
import Admin from './pages/Admin'

const ProtectedRoute = ({ children }) => {
  const { user } = useAuthStore()
  return user ? children : <Navigate to="/login" />
}

const AdminRoute = ({ children }) => {
  const { user } = useAuthStore()
  return user?.role === 'ADMIN' ? children : <Navigate to="/dashboard" />
}

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  in: { opacity: 1, y: 0 },
  out: { opacity: 0, y: -20 }
}

const pageTransition = {
  type: 'tween',
  ease: 'anticipate',
  duration: 0.5
}

const App = () => {
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const { user } = useAuthStore()

  useEffect(() => {
    // Initialize auth state from localStorage
    const token = localStorage.getItem('token')
    const userData = localStorage.getItem('user')
    
    if (token && userData) {
      useAuthStore.getState().setAuth({
        token,
        user: JSON.parse(userData)
      })
    }
  }, [])

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-dark">
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#1a1a1a',
              color: '#ffffff',
              border: '1px solid #404040',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#ffffff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#ffffff',
              },
            },
          }}
        />

        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <Dashboard />
                    </motion.div>
                  </div>
                </div>
              </ProtectedRoute>
            } />
            
            <Route path="/profile" element={
              <ProtectedRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <Profile />
                    </motion.div>
                  </div>
                </div>
              </ProtectedRoute>
            } />
            
            <Route path="/security" element={
              <ProtectedRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <Security />
                    </motion.div>
                  </div>
                </div>
              </ProtectedRoute>
            } />
            
            <Route path="/analytics" element={
              <ProtectedRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <Analytics />
                    </motion.div>
                  </div>
                </div>
              </ProtectedRoute>
            } />
            
            <Route path="/settings" element={
              <ProtectedRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <AppSettings />
                    </motion.div>
                  </div>
                </div>
              </ProtectedRoute>
            } />
            
            <Route path="/billing" element={
              <ProtectedRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <BillingPlan />
                    </motion.div>
                  </div>
                </div>
              </ProtectedRoute>
            } />
            
            <Route path="/admin" element={
              <AdminRoute>
                <div className="flex">
                  <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                  <div className="flex-1">
                    <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
                    <motion.div
                      initial="initial"
                      animate="in"
                      exit="out"
                      variants={pageVariants}
                      transition={pageTransition}
                    >
                      <Admin />
                    </motion.div>
                  </div>
                </div>
              </AdminRoute>
            } />
            
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Routes>
        </AnimatePresence>
      </div>
    </ErrorBoundary>
  )
}

export default App
