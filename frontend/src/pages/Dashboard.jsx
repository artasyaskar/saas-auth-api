import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  Users, 
  Activity, 
  TrendingUp, 
  Zap, 
  Shield, 
  Clock,
  AlertTriangle,
  BarChart3,
  Settings,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useRealTimeData } from '../hooks/useRealTimeData'
import { useRateLimit } from '../hooks/useRateLimit'
import ThreeDCard from '../components/ThreeDCard'
import AnimatedBackground from '../components/AnimatedBackground'
import toast from 'react-hot-toast'

const Dashboard = () => {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const realTimeData = useRealTimeData()
  const userPlan = user?.plan || 'FREE'
  const { rateLimitStatus, usageStats, makeRequest, planConfig } = useRateLimit(userPlan)
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
      value: usageStats.totalRequests.toLocaleString(),
      change: '+23%',
      icon: Activity,
      color: 'from-blue-50 to-blue-100'
    },
    {
      title: 'Rate Limit',
      value: `${rateLimitStatus.requestsRemaining}/${planConfig.requestsPerMinute}`,
      change: rateLimitStatus.isRateLimited ? '-100%' : 'OK',
      icon: Zap,
      color: rateLimitStatus.isRateLimited ? 'from-red-50 to-red-100' : 'from-green-50 to-green-100'
    },
    {
      title: 'Monthly Quota',
      value: `${rateLimitStatus.quotaRemaining.toLocaleString()}`,
      change: `${Math.round((rateLimitStatus.quotaRemaining / planConfig.monthlyQuota) * 100)}%`,
      icon: CreditCard,
      color: rateLimitStatus.quotaRemaining < planConfig.monthlyQuota * 0.2 ? 'from-orange-50 to-orange-100' : 'from-purple-50 to-purple-100'
    },
    {
      title: 'Current Plan',
      value: userPlan,
      change: userPlan === 'FREE' ? 'Upgrade' : 'Active',
      icon: Shield,
      color: userPlan === 'PRO' ? 'from-yellow-50 to-yellow-100' : 'from-gray-50 to-gray-100'
    }
  ]

  return (
    <div className="min-h-screen bg-dark relative overflow-hidden">
      {/* Animated Background */}
      <AnimatedBackground />
      
      <div className="relative z-10">
        <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto relative">
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

          {/* Rate Limiting & Billing Status */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* Rate Limiting Status */}
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-dark-200 flex items-center">
                  <Zap className="w-5 h-5 text-accent-50 mr-2" />
                  Rate Limiting Status
                </h2>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  rateLimitStatus.isRateLimited ? 'bg-error/20 text-error' :
                  rateLimitStatus.requestsRemaining < 10 ? 'bg-warning/20 text-warning' :
                  'bg-success/20 text-success'
                }`}>
                  {rateLimitStatus.isRateLimited ? 'LIMITED' :
                   rateLimitStatus.requestsRemaining < 10 ? 'LOW' :
                   'OK'}
                </span>
              </div>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-dark-400">Requests This Minute</span>
                    <span className="text-sm font-bold text-dark-200">
                      {planConfig.requestsPerMinute - rateLimitStatus.requestsRemaining}/{planConfig.requestsPerMinute}
                    </span>
                  </div>
                  <div className="w-full bg-dark-100 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${
                        rateLimitStatus.isRateLimited ? 'bg-error' :
                        rateLimitStatus.requestsRemaining < 10 ? 'bg-warning' :
                        'bg-success'
                      }`}
                      style={{ 
                        width: `${((planConfig.requestsPerMinute - rateLimitStatus.requestsRemaining) / planConfig.requestsPerMinute) * 100}%` 
                      }}
                    />
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-dark-400">Monthly Quota</span>
                    <span className="text-sm font-bold text-dark-200">
                      {((planConfig.monthlyQuota - rateLimitStatus.quotaRemaining) / planConfig.monthlyQuota * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-dark-100 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${
                        rateLimitStatus.quotaRemaining < planConfig.monthlyQuota * 0.2 ? 'bg-error' :
                        rateLimitStatus.quotaRemaining < planConfig.monthlyQuota * 0.5 ? 'bg-warning' :
                        'bg-success'
                      }`}
                      style={{ 
                        width: `${((planConfig.monthlyQuota - rateLimitStatus.quotaRemaining) / planConfig.monthlyQuota) * 100}%` 
                      }}
                    />
                  </div>
                </div>
                
                {rateLimitStatus.resetTime && (
                  <div className="flex items-center space-x-2 text-sm text-dark-400">
                    <Clock className="w-4 h-4" />
                    <span>Resets in: {Math.ceil((rateLimitStatus.resetTime - Date.now()) / 1000)}s</span>
                  </div>
                )}
              </div>
            </div>

            {/* Plan Status & Upgrade */}
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-dark-200 flex items-center">
                  <CreditCard className="w-5 h-5 text-accent-50 mr-2" />
                  Plan Status
                </h2>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  userPlan === 'PRO' ? 'bg-yellow-50/20 text-yellow-50' : 'bg-gray-50/20 text-gray-400'
                }`}>
                  {userPlan}
                </span>
              </div>
              
              <div className="space-y-4">
                <div className="p-4 glass-morphism rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-dark-200">Current Plan</span>
                    <span className="text-lg font-bold text-dark-200">{userPlan}</span>
                  </div>
                  <div className="text-sm text-dark-400">
                    {userPlan === 'FREE' ? '1,000 requests/month' : '10,000 requests/month'}
                  </div>
                </div>
                
                {userPlan === 'FREE' && rateLimitStatus.quotaRemaining < planConfig.monthlyQuota * 0.3 && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg border border-purple-500/30"
                  >
                    <div className="flex items-center space-x-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-purple-400" />
                      <span className="text-sm font-medium text-purple-300">Running low on quota!</span>
                    </div>
                    <p className="text-xs text-purple-400 mb-3">
                      Upgrade to Pro for 10x more requests and advanced features.
                    </p>
                    <button
                      onClick={() => navigate('/billing')}
                      className="w-full py-2 px-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                    >
                      Upgrade to Pro
                    </button>
                  </motion.div>
                )}
                
                <button
                  onClick={() => navigate('/upgrade-plans')}
                  className="w-full py-2 px-4 btn-secondary flex items-center justify-center"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Manage Plan
                </button>
              </div>
            </div>
          </motion.div>

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
