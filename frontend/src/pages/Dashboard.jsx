import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Users, 
  Activity, 
  TrendingUp, 
  Shield, 
  Zap,
  Clock,
  BarChart3
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'

const Dashboard = () => {
  const { user } = useAuthStore()
  const [stats, setStats] = useState({
    totalRequests: 0,
    avgResponseTime: 0,
    activeUsers: 0,
    uptime: '99.9%'
  })

  const statCards = [
    {
      title: 'API Requests',
      value: stats.totalRequests.toLocaleString(),
      change: '+12%',
      icon: Activity,
      color: 'from-blue-50 to-blue-100'
    },
    {
      title: 'Avg Response Time',
      value: `${stats.avgResponseTime}ms`,
      change: '-8%',
      icon: Clock,
      color: 'from-green-50 to-green-100'
    },
    {
      title: 'Active Users',
      value: stats.activeUsers.toLocaleString(),
      change: '+23%',
      icon: Users,
      color: 'from-purple-50 to-purple-100'
    },
    {
      title: 'System Uptime',
      value: stats.uptime,
      change: '+0.1%',
      icon: TrendingUp,
      color: 'from-orange-50 to-orange-100'
    }
  ]

  return (
    <div className="min-h-screen bg-dark">
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold gradient-text mb-2">
            Welcome back, {user?.username}! 👋
          </h1>
          <p className="text-dark-400">
            Here's what's happening with your SaaS platform today
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((stat, index) => {
            const Icon = stat.icon
            return (
              <motion.div
                key={stat.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="card hover:scale-105 transition-transform duration-300"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 bg-gradient-to-r ${stat.color} rounded-lg flex items-center justify-center`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-sm font-medium text-success">
                    {stat.change}
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-dark-200 mb-1">
                  {stat.value}
                </h3>
                <p className="text-sm text-dark-400">
                  {stat.title}
                </p>
              </motion.div>
            )
          })}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Activity Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="lg:col-span-2 card"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-dark-200">
                API Activity
              </h2>
              <BarChart3 className="w-5 h-5 text-dark-400" />
            </div>
            
            {/* Chart Placeholder */}
            <div className="h-64 flex items-center justify-center glass-morphism rounded-lg">
              <div className="text-center">
                <Zap className="w-12 h-12 text-accent-50 mx-auto mb-4" />
                <p className="text-dark-400">Real-time activity monitoring</p>
                <p className="text-sm text-dark-500 mt-2">
                  Chart visualization coming soon
                </p>
              </div>
            </div>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="card"
          >
            <h2 className="text-xl font-semibold text-dark-200 mb-6">
              Quick Actions
            </h2>
            
            <div className="space-y-3">
              <button className="w-full btn-secondary text-left justify-start">
                <Shield className="w-4 h-4 mr-3" />
                Security Settings
              </button>
              
              <button className="w-full btn-secondary text-left justify-start">
                <Users className="w-4 h-4 mr-3" />
                User Management
              </button>
              
              <button className="w-full btn-secondary text-left justify-start">
                <BarChart3 className="w-4 h-4 mr-3" />
                View Analytics
              </button>
              
              <button className="w-full btn-secondary text-left justify-start">
                <Zap className="w-4 h-4 mr-3" />
                API Documentation
              </button>
            </div>
          </motion.div>
        </div>

        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mt-8 card"
        >
          <h2 className="text-xl font-semibold text-dark-200 mb-6">
            Recent Activity
          </h2>
          
          <div className="space-y-4">
            {[
              { action: 'User login', user: 'john_doe', time: '2 minutes ago', status: 'success' },
              { action: 'API request', user: 'jane_smith', time: '5 minutes ago', status: 'success' },
              { action: 'Password reset', user: 'bob_wilson', time: '12 minutes ago', status: 'warning' },
              { action: 'New registration', user: 'alice_brown', time: '1 hour ago', status: 'success' },
            ].map((activity, index) => (
              <div key={index} className="flex items-center justify-between p-4 glass-morphism rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    activity.status === 'success' ? 'bg-success' : 
                    activity.status === 'warning' ? 'bg-warning' : 'bg-error'
                  }`}></div>
                  <div>
                    <p className="text-sm font-medium text-dark-200">
                      {activity.action}
                    </p>
                    <p className="text-xs text-dark-400">
                      by {activity.user}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-dark-500">
                  {activity.time}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Dashboard
