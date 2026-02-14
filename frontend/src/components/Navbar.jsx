import React from 'react'
import { motion } from 'framer-motion'
import { Menu, X, LogOut, User, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const Navbar = ({ sidebarOpen, setSidebarOpen }) => {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass-morphism border-b border-dark-200/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and menu button */}
          <div className="flex items-center">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg text-dark-400 hover:text-dark-200 hover:bg-dark-100/50 transition-colors"
            >
              {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            
            <motion.div 
              className="ml-4 flex items-center"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="w-8 h-8 bg-gradient-to-r from-accent-50 to-accent-100 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <span className="ml-2 text-xl font-bold gradient-text">SaaS Auth</span>
            </motion.div>
          </div>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-accent-50 to-accent-100 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="hidden md:block">
                <p className="text-sm font-medium text-dark-200">{user?.username}</p>
                <p className="text-xs text-dark-400">{user?.role}</p>
              </div>
            </div>
            
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleLogout}
              className="p-2 rounded-lg text-dark-400 hover:text-dark-200 hover:bg-dark-100/50 transition-colors"
            >
              <LogOut size={20} />
            </motion.button>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
