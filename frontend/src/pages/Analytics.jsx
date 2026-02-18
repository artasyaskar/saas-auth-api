import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Activity,
  Calendar,
  Clock,
  Zap,
  Eye,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  Sparkles,
  Flame
} from 'lucide-react'

const Analytics = () => {
  const [timeRange, setTimeRange] = useState('7d')
  const [isLoading, setIsLoading] = useState(false)

  const timeRanges = [
    { value: '24h', label: '24 Hours' },
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' }
  ]

  const stats = {
    '24h': {
      requests: 12543,
      users: 892,
      avgResponse: 142,
      uptime: 99.9,
      change: { requests: 12, users: 8, response: -5 }
    },
    '7d': {
      requests: 87654,
      users: 3421,
      avgResponse: 138,
      uptime: 99.8,
      change: { requests: 23, users: 15, response: -8 }
    },
    '30d': {
      requests: 376543,
      users: 12456,
      avgResponse: 145,
      uptime: 99.7,
      change: { requests: 45, users: 32, response: -12 }
    },
    '90d': {
      requests: 1209876,
      users: 45678,
      avgResponse: 151,
      uptime: 99.6,
      change: { requests: 67, users: 54, response: -18 }
    }
  }

  const currentStats = stats[timeRange]

  const chartData = [
    { name: 'Mon', requests: 12000, users: 800 },
    { name: 'Tue', requests: 15000, users: 950 },
    { name: 'Wed', requests: 18000, users: 1100 },
    { name: 'Thu', requests: 14000, users: 900 },
    { name: 'Fri', requests: 22000, users: 1400 },
    { name: 'Sat', requests: 16000, users: 1000 },
    { name: 'Sun', requests: 13000, users: 850 }
  ]

  const topEndpoints = [
    { endpoint: '/auth/login', requests: 45321, avgResponse: 120 },
    { endpoint: '/users/profile', requests: 32145, avgResponse: 95 },
    { endpoint: '/auth/register', requests: 28765, avgResponse: 145 },
    { endpoint: '/admin/users', requests: 19876, avgResponse: 110 },
    { endpoint: '/users/usage', requests: 15432, avgResponse: 85 }
  ]

  const recentActivity = [
    { time: '2 min ago', event: 'High traffic detected', type: 'warning' },
    { time: '15 min ago', event: 'New user registration spike', type: 'success' },
    { time: '1 hour ago', event: 'API response time optimized', type: 'info' },
    { time: '2 hours ago', event: 'Database backup completed', type: 'success' },
    { time: '3 hours ago', event: 'Rate limit triggered', type: 'warning' }
  ]

  const statCards = [
    {
      title: 'API Requests',
      value: currentStats.requests.toLocaleString(),
      change: currentStats.change.requests,
      icon: Activity,
      color: 'from-blue-50 to-blue-100'
    },
    {
      title: 'Active Users',
      value: currentStats.users.toLocaleString(),
      change: currentStats.change.users,
      icon: Users,
      color: 'from-green-50 to-green-100'
    },
    {
      title: 'Avg Response',
      value: `${currentStats.avgResponse}ms`,
      change: currentStats.change.response,
      icon: Clock,
      color: 'from-purple-50 to-purple-100'
    },
    {
      title: 'Uptime',
      value: `${currentStats.uptime}%`,
      change: 0.1,
      icon: Zap,
      color: 'from-orange-50 to-orange-100'
    }
  ]

  return (
    <div className="min-h-screen bg-dark">
      <style jsx>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 50%;
          }
          100% {
            background-position: 200% 50%;
          }
        }
      `}</style>
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        {/* Stunning Go Back Button */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="absolute top-8 left-4"
        >
          <motion.button
            whileHover={{ scale: 1.05, rotate: [0, -5, 5, -5] }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate(-1)}
            className="group relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 p-1 shadow-2xl shadow-purple-500/25 hover:shadow-purple-500/40 transition-all duration-300"
          >
            {/* Animated Background */}
            <div className="absolute inset-0 bg-gradient-to-r from-white/20 via-transparent to-white/20 opacity-0 group-hover:opacity-30 transition-opacity duration-300" />
            
            {/* Floating Particles */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              className="absolute -top-1 -left-1 w-3 h-3"
            >
              <Sparkles className="w-full h-full text-yellow-300" />
            </motion.div>
            
            <motion.div
              animate={{ rotate: -360 }}
              transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
              className="absolute -bottom-1 -right-1 w-2 h-2"
            >
              <Flame className="w-full h-full text-orange-400" />
            </motion.div>
            
            {/* Button Content */}
            <div className="relative flex items-center space-x-2 text-white font-bold">
              <motion.div
                animate={{ x: [0, 3, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              >
                <ArrowLeft className="w-5 h-5" />
              </motion.div>
              <motion.span
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="text-transparent bg-clip-text text-transparent bg-gradient-to-r from-white via-purple-200 to-pink-200 bg-clip-text"
              >
                Go Back
              </motion.span>
            </div>
            
            {/* Hover Glow Effect */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-purple-400/20 via-pink-400/20 to-blue-400/20 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-300" />
            
            {/* Border Animation */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              className="absolute inset-0 rounded-2xl border-2 border-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 opacity-30 group-hover:opacity-60"
              style={{
                background: 'linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.1), transparent, rgba(236, 72, 153, 0.1), transparent)',
                backgroundSize: '200% 200%',
                backgroundPosition: '0% 50%',
                animation: 'shimmer 2s infinite'
              }}
            />
          </motion.button>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold gradient-text mb-2">
                Analytics Dashboard
              </h1>
              <p className="text-dark-400">
                Monitor your API performance and usage patterns
              </p>
            </div>
            
            {/* Time Range Selector */}
            <div className="flex items-center space-x-2">
              <Calendar className="w-5 h-5 text-dark-400" />
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-dark-50/50 border border-dark-200/30 rounded-lg px-4 py-2 text-dark-200 focus:outline-none focus:ring-2 focus:ring-accent-50/50 focus:border-accent-50 transition-all duration-300"
              >
                {timeRanges.map(range => (
                  <option key={range.value} value={range.value}>
                    {range.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {statCards.map((stat, index) => {
              const Icon = stat.icon
              const isPositive = stat.change >= 0
              
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
                    <div className={`flex items-center space-x-1 text-sm font-medium ${
                      isPositive ? 'text-success' : 'text-error'
                    }`}>
                      {isPositive ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                      <span>{Math.abs(stat.change)}%</span>
                    </div>
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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Chart */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="card"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-dark-200">
                  Request Trends
                </h2>
                <BarChart3 className="w-5 h-5 text-dark-400" />
              </div>
              
              <div className="h-64 flex items-center justify-center glass-morphism rounded-lg">
                <div className="text-center">
                  <BarChart3 className="w-12 h-12 text-accent-50 mx-auto mb-4" />
                  <p className="text-dark-400">Interactive chart visualization</p>
                  <p className="text-sm text-dark-500 mt-2">
                    Chart library integration coming soon
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Top Endpoints */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="card"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-dark-200">
                  Top Endpoints
                </h2>
                <Eye className="w-5 h-5 text-dark-400" />
              </div>
              
              <div className="space-y-3">
                {topEndpoints.map((endpoint, index) => (
                  <div key={endpoint.endpoint} className="flex items-center justify-between p-3 glass-morphism rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-dark-200">
                        {endpoint.endpoint}
                      </p>
                      <p className="text-xs text-dark-400">
                        {endpoint.avgResponse}ms avg response
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-accent-50">
                        {endpoint.requests.toLocaleString()}
                      </p>
                      <p className="text-xs text-dark-400">requests</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="card"
          >
            <div className="flex items-center mb-6">
              <Activity className="w-5 h-5 text-accent-50 mr-2" />
              <h2 className="text-xl font-semibold text-dark-200">
                Recent Activity
              </h2>
            </div>
            
            <div className="space-y-3">
              {recentActivity.map((activity, index) => (
                <div key={index} className="flex items-center justify-between p-4 glass-morphism rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${
                      activity.type === 'success' ? 'bg-success' : 
                      activity.type === 'warning' ? 'bg-warning' : 'bg-accent-50'
                    }`}></div>
                    <div>
                      <p className="text-sm font-medium text-dark-200">
                        {activity.event}
                      </p>
                      <p className="text-xs text-dark-400">
                        {activity.time}
                      </p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    activity.type === 'success' ? 'bg-success/20 text-success' : 
                    activity.type === 'warning' ? 'bg-warning/20 text-warning' : 'bg-accent-50/20 text-accent-50'
                  }`}>
                    {activity.type}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

export default Analytics
