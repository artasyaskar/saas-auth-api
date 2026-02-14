import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  LayoutDashboard, 
  User, 
  Shield, 
  BarChart3, 
  Settings,
  X
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'

const Sidebar = ({ sidebarOpen, setSidebarOpen }) => {
  const location = useLocation()
  const { user } = useAuthStore()

  const menuItems = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
    },
    {
      name: 'Profile',
      path: '/profile',
      icon: User,
    },
    {
      name: 'Security',
      path: '/security',
      icon: Shield,
    },
    {
      name: 'Analytics',
      path: '/analytics',
      icon: BarChart3,
    },
  ]

  if (user?.role === 'ADMIN') {
    menuItems.push({
      name: 'Admin Panel',
      path: '/admin',
      icon: Shield,
    })
  }

  const sidebarVariants = {
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 400,
        damping: 40
      }
    },
    closed: {
      x: '-100%',
      transition: {
        type: 'spring',
        stiffness: 400,
        damping: 40
      }
    }
  }

  return (
    <>
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <motion.aside
        variants={sidebarVariants}
        initial="closed"
        animate={sidebarOpen ? "open" : "closed"}
        className="fixed top-0 left-0 z-50 w-64 h-full glass-morphism border-r border-dark-200/20 lg:translate-x-0 lg:static lg:inset-0"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-dark-200/20">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-gradient-to-r from-accent-50 to-accent-100 rounded-xl flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <span className="ml-3 text-xl font-bold gradient-text">SaaS Auth</span>
            </div>
            
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-lg text-dark-400 hover:text-dark-200 hover:bg-dark-100/50 transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-3 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-accent-50/20 text-accent-50 border border-accent-50/30'
                        : 'text-dark-400 hover:text-dark-200 hover:bg-dark-100/50'
                    }`
                  }
                >
                  <Icon size={20} className="flex-shrink-0" />
                  <span className="ml-3 font-medium">{item.name}</span>
                  
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute right-2 w-2 h-2 bg-accent-50 rounded-full"
                      initial={false}
                      transition={{
                        type: 'spring',
                        stiffness: 500,
                        damping: 30
                      }}
                    />
                  )}
                </NavLink>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-dark-200/20">
            <div className="glass-morphism rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-accent-50 to-accent-100 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-dark-200 truncate">
                    {user?.username}
                  </p>
                  <p className="text-xs text-dark-400">
                    {user?.subscription_plan} Plan
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.aside>
    </>
  )
}

export default Sidebar
