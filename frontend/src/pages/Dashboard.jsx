import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
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
import { useRealTimeData } from '../hooks/useRealTimeData'
import ThreeDCard from '../components/ThreeDCard'
import AnimatedBackground from '../components/AnimatedBackground'

const Dashboard = () => {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const realTimeData = useRealTimeData()
  const [animatedNumbers, setAnimatedNumbers] = useState({
    totalRequests: 87654,
    activeUsers: 3421,
    avgResponseTime: 142,
    uptime: 99.8
  })

  // Animate numbers on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedNumbers({
        totalRequests: 87654,
        activeUsers: 3421,
        avgResponseTime: 142,
        uptime: 99.8
      })
    }, 500)
    return () => clearTimeout(timer)
  }, [])

  const handleQuickAction = (action) => {
    switch(action) {
      case 'security':
        navigate('/security')
        break
      case 'users':
        if (user?.role === 'ADMIN') {
          navigate('/admin')
        } else {
          navigate('/profile')
        }
        break
      case 'analytics':
        navigate('/analytics')
        break
      case 'docs':
        window.open('http://localhost:8002/docs', '_blank')
        break
      default:
        break
    }
  }

  const statCards = [
    {
      title: 'API Requests',
      value: animatedNumbers.totalRequests.toLocaleString(),
      change: '+23%',
      icon: Activity,
      color: 'from-blue-50 to-blue-100'
    },
    {
      title: 'Active Users',
      value: animatedNumbers.activeUsers.toLocaleString(),
      change: '+15%',
      icon: Users,
      color: 'from-green-50 to-green-100'
    },
    {
      title: 'Avg Response',
      value: `${animatedNumbers.avgResponseTime}ms`,
      change: '-8%',
      icon: Clock,
      color: 'from-purple-50 to-purple-100'
    },
    {
      title: 'System Uptime',
      value: `${animatedNumbers.uptime}%`,
      change: '+0.1%',
      icon: TrendingUp,
      color: 'from-orange-50 to-orange-100'
    }
  ]

  return (
    <div className="min-h-screen bg-dark relative overflow-hidden">
      {/* Animated Background */}
      <AnimatedBackground />
      
      <div className="relative z-10">
        <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h1 className="text-4xl font-bold gradient-text mb-2">
              Welcome back, {user?.username}! �
            </h1>
            <p className="text-dark-400 text-lg">
              Real-time monitoring for {realTimeData.activeUsers.toLocaleString()} active users
            </p>
          </motion.div>

          {/* 3D Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {statCards.map((stat, index) => {
              const Icon = stat.icon
              return (
                <ThreeDCard
                  key={stat.title}
                  title={stat.title}
                  value={stat.value}
                  change={stat.change}
                  icon={Icon}
                  color={stat.color}
                  delay={index * 0.1}
                />
              )
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Live Activity Feed */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="card"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-dark-200 flex items-center">
                  <Activity className="w-5 h-5 text-accent-50 mr-2" />
                  Live Activity Feed
                  <div className="flex items-center ml-2">
                    <div className="w-2 h-2 bg-success rounded-full animate-pulse"></div>
                    <span className="text-xs text-success ml-2">LIVE</span>
                  </div>
                </h2>
              </div>
              
              <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
                {realTimeData.recentActivity.slice(0, 8).map((activity, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    className="flex items-center justify-between p-4 glass-morphism rounded-lg border-l-4 border-accent-50/50"
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${
                        activity.type === 'login' ? 'bg-success' :
                        activity.type === 'error' ? 'bg-error' :
                        activity.type === 'registration' ? 'bg-accent-50' :
                        'bg-warning'
                      }`}></div>
                      <div>
                        <p className="text-sm font-medium text-dark-200">
                          {activity.type === 'login' && `${activity.user} logged in from ${activity.location}`}
                          {activity.type === 'registration' && `${activity.user} registered from ${activity.location}`}
                          {activity.type === 'api_request' && `${activity.method} ${activity.endpoint} - ${activity.status}`}
                          {activity.type === 'error' && activity.message}
                          {activity.type === 'security' && `${activity.action} by ${activity.user}`}
                        </p>
                        <p className="text-xs text-dark-400">{activity.time}</p>
                      </div>
                    </div>
                    <div className="text-xs text-dark-500">
                      {activity.type === 'login' && '🟢'}
                      {activity.type === 'registration' && '🔵'}
                      {activity.type === 'api_request' && '📡'}
                      {activity.type === 'error' && '🔴'}
                      {activity.type === 'security' && '🛡️'}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Server Metrics */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="card"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-dark-200 flex items-center">
                  <Zap className="w-5 h-5 text-accent-50 mr-2" />
                  Server Metrics
                </h2>
              </div>
              
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Server Load</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 bg-dark-100 rounded-full h-2">
                      <motion.div
                        className="h-2 bg-gradient-to-r from-success via-warning to-error rounded-full"
                        style={{ width: `${realTimeData.serverLoad}%` }}
                        initial={{ width: 0 }}
                        animate={{ width: realTimeData.serverLoad }}
                        transition={{ duration: 1 }}
                      />
                    </div>
                    <span className="text-sm font-bold text-dark-200">{realTimeData.serverLoad}%</span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Current Requests/sec</span>
                  <motion.span 
                    className="text-2xl font-bold gradient-text"
                    animate={{ scale: 1.05 }}
                    whileHover={{ scale: 1.1 }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    {realTimeData.currentRequests}
                  </motion.span>
                </div>
                
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Network Status</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-success rounded-full animate-pulse"></div>
                    <span className="text-sm font-bold text-success">Healthy</span>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
              className="card"
            >
              <h2 className="text-xl font-semibold text-dark-200 mb-6">
                Quick Actions
              </h2>
              
              <div className="space-y-3">
                <button 
                  onClick={() => handleQuickAction('security')}
                  className="w-full btn-secondary text-left justify-start hover:scale-105 transition-all duration-300 hover:shadow-lg hover:shadow-accent-50/25"
                >
                  <Shield className="w-4 h-4 mr-3" />
                  Security Settings
                </button>
                
                <button 
                  onClick={() => handleQuickAction('users')}
                  className="w-full btn-secondary text-left justify-start hover:scale-105 transition-all duration-300 hover:shadow-lg hover:shadow-accent-50/25"
                >
                  <Users className="w-4 h-4 mr-3" />
                  {user?.role === 'ADMIN' ? 'User Management' : 'Profile Settings'}
                </button>
                
                <button 
                  onClick={() => handleQuickAction('analytics')}
                  className="w-full btn-secondary text-left justify-start hover:scale-105 transition-all duration-300 hover:shadow-lg hover:shadow-accent-50/25"
                >
                  <BarChart3 className="w-4 h-4 mr-3" />
                  View Analytics
                </button>
                
                <button 
                  onClick={() => handleQuickAction('docs')}
                  className="w-full btn-secondary text-left justify-start hover:scale-105 transition-all duration-300 hover:shadow-lg hover:shadow-accent-50/25"
                >
                  <Zap className="w-4 h-4 mr-3" />
                  API Documentation
                </button>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
