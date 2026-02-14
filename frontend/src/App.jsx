import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Admin from './pages/Admin'
import { useAuthStore } from './store/authStore'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, checkAuth } = useAuthStore()

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const pageVariants = {
    initial: { opacity: 0, y: 20 },
    in: { opacity: 1, y: 0 },
    out: { opacity: 0, y: -20 }
  }

  const pageTransition = {
    type: 'tween',
    ease: 'anticipate',
    duration: 0.3
  }

  return (
    <div className="min-h-screen bg-dark text-dark-900">
      {user && (
        <>
          <Navbar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        </>
      )}
      
      <main className={`transition-all duration-300 ${user ? 'lg:ml-64' : ''}`}>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/login" element={
              !user ? (
                <motion.div
                  initial="initial"
                  animate="in"
                  exit="out"
                  variants={pageVariants}
                  transition={pageTransition}
                >
                  <Login />
                </motion.div>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } />
            
            <Route path="/register" element={
              !user ? (
                <motion.div
                  initial="initial"
                  animate="in"
                  exit="out"
                  variants={pageVariants}
                  transition={pageTransition}
                >
                  <Register />
                </motion.div>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } />
            
            <Route path="/dashboard" element={
              user ? (
                <motion.div
                  initial="initial"
                  animate="in"
                  exit="out"
                  variants={pageVariants}
                  transition={pageTransition}
                >
                  <Dashboard />
                </motion.div>
              ) : (
                <Navigate to="/login" replace />
              )
            } />
            
            <Route path="/profile" element={
              user ? (
                <motion.div
                  initial="initial"
                  animate="in"
                  exit="out"
                  variants={pageVariants}
                  transition={pageTransition}
                >
                  <Profile />
                </motion.div>
              ) : (
                <Navigate to="/login" replace />
              )
            } />
            
            <Route path="/admin" element={
              user && user.role === 'ADMIN' ? (
                <motion.div
                  initial="initial"
                  animate="in"
                  exit="out"
                  variants={pageVariants}
                  transition={pageTransition}
                >
                  <Admin />
                </motion.div>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } />
            
            <Route path="/" element={<Navigate to={user ? "/dashboard" : "/login"} replace />} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  )
}

export default App
