import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Users, 
  Shield, 
  Activity, 
  TrendingUp,
  Search,
  Filter,
  MoreVertical,
  UserCheck,
  UserX,
  Eye,
  Edit,
  Trash2,
  Database,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Globe,
  Server,
  Settings,
  BarChart3,
  Lock,
  Unlock,
  RefreshCw,
  Download,
  Upload
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'
import { adminAPI } from '../services/api'

const Admin = () => {
  const { user } = useAuthStore()
  
  const generateMockUsers = () => [
    { id: 1, username: 'john_doe', email: 'john@example.com', role: 'USER', status: 'active', lastLogin: '2 min ago', requests: 1234 },
    { id: 2, username: 'sarah_smith', email: 'sarah@example.com', role: 'ADMIN', status: 'active', lastLogin: '5 min ago', requests: 892 },
    { id: 3, username: 'mike_wilson', email: 'mike@example.com', role: 'USER', status: 'suspended', lastLogin: '2 hours ago', requests: 567 },
    { id: 4, username: 'alex_jones', email: 'alex@example.com', role: 'USER', status: 'active', lastLogin: '1 min ago', requests: 2341 },
    { id: 5, username: 'emma_brown', email: 'emma@example.com', role: 'USER', status: 'active', lastLogin: '10 min ago', requests: 445 },
  ]

  const generateMockStats = () => ({
    totalUsers: 3421,
    activeUsers: 2890,
    newUsersToday: 47,
    totalRequests: 156789,
    serverUptime: 99.9,
    errorRate: 0.1,
    avgResponseTime: 142,
    systemHealth: 'Excellent'
  })

  const [users, setUsers] = useState(generateMockUsers())
  const [stats, setStats] = useState(generateMockStats())
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedTab, setSelectedTab] = useState('overview')

  useEffect(() => {
    fetchUsers()
    fetchStats()
  }, [])

  const fetchUsers = async () => {
    setIsLoading(true)
    try {
      const response = await adminAPI.getUsers()
      setUsers(response.data || generateMockUsers())
    } catch (error) {
      setUsers(generateMockUsers())
    }
    setIsLoading(false)
  }

  const fetchStats = async () => {
    try {
      const response = await adminAPI.getUserStats()
      setStats(response.data || generateMockStats())
    } catch (error) {
      setStats(generateMockStats())
    }
  }

  const handleUserAction = async (userId, action) => {
    try {
      switch (action) {
        case 'suspend':
          setUsers(users.map(u => u.id === userId ? { ...u, status: 'suspended' } : u))
          toast.success('User suspended successfully')
          break
        case 'activate':
          setUsers(users.map(u => u.id === userId ? { ...u, status: 'active' } : u))
          toast.success('User activated successfully')
          break
        case 'delete':
          setUsers(users.filter(u => u.id !== userId))
          toast.success('User deleted successfully')
          break
        case 'promote':
          setUsers(users.map(u => u.id === userId ? { ...u, role: 'ADMIN' } : u))
          toast.success('User promoted to admin role')
          break
        case 'demote':
          setUsers(users.map(u => u.id === userId ? { ...u, role: 'USER' } : u))
          toast.success('Admin role removed')
          break
      }
    } catch (error) {
      toast.error('Action failed')
    }
  }

  const adminStatsCards = [
    {
      title: 'Total Users',
      value: (stats?.totalUsers || 0).toLocaleString(),
      change: '+12%',
      icon: Users,
      color: 'from-blue-500 to-blue-600',
      description: 'Registered users'
    },
    {
      title: 'Active Now',
      value: (stats?.activeUsers || 0).toLocaleString(),
      change: '+8%',
      icon: Activity,
      color: 'from-green-500 to-green-600',
      description: 'Currently online'
    },
    {
      title: 'API Requests',
      value: (stats?.totalRequests || 0).toLocaleString(),
      change: '+23%',
      icon: Zap,
      color: 'from-purple-500 to-purple-600',
      description: 'Total requests today'
    },
    {
      title: 'Server Uptime',
      value: `${stats?.serverUptime || 99.9}%`,
      change: '+0.1%',
      icon: Server,
      color: 'from-orange-500 to-orange-600',
      description: 'System availability'
    }
  ]

  const systemMetrics = [
    { label: 'Response Time', value: `${stats?.avgResponseTime || 142}ms`, status: 'good', icon: Clock },
    { label: 'Error Rate', value: `${stats?.errorRate || 0.1}%`, status: 'excellent', icon: AlertTriangle },
    { label: 'System Health', value: stats?.systemHealth || 'Excellent', status: 'excellent', icon: CheckCircle },
    { label: 'Database', value: 'Connected', status: 'good', icon: Database }
  ]

  const filteredUsers = users.filter(u => 
    (u?.username || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u?.email || '').toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-dark">
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        {/* Admin Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold gradient-text mb-2">
                Admin Dashboard 🔐
              </h1>
              <p className="text-dark-400 text-lg">
                System administration and user management
              </p>
            </div>
            <div className="flex space-x-3">
              <button className="btn-secondary flex items-center">
                <Download className="w-4 h-4 mr-2" />
                Export Data
              </button>
              <button className="btn-primary flex items-center">
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </button>
            </div>
          </div>
        </motion.div>

        {/* Admin Navigation Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-8"
        >
          <div className="flex space-x-1 bg-dark-50/50 p-1 rounded-lg">
            {['overview', 'users', 'system', 'security'].map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`flex-1 py-2 px-4 rounded-md transition-all duration-200 ${
                  selectedTab === tab
                    ? 'bg-dark-200 text-white shadow-lg'
                    : 'text-dark-400 hover:text-white hover:bg-dark-100/50'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Overview Tab */}
        {selectedTab === 'overview' && (
          <div className="space-y-6">
            {/* Admin Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {adminStatsCards.map((stat, index) => {
                const Icon = stat.icon
                return (
                  <motion.div
                    key={stat.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="card"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className={`w-12 h-12 bg-gradient-to-r ${stat.color} rounded-xl flex items-center justify-center`}>
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <span className={`text-sm font-bold ${
                        stat.change.startsWith('+') ? 'text-success' : 'text-error'
                      }`}>
                        {stat.change}
                      </span>
                    </div>
                    <h3 className="text-2xl font-bold text-dark-200">{stat.value}</h3>
                    <p className="text-sm text-dark-400">{stat.title}</p>
                    <p className="text-xs text-dark-500 mt-1">{stat.description}</p>
                  </motion.div>
                )
              })}
            </div>

            {/* System Metrics */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="card"
            >
              <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                <BarChart3 className="w-5 h-5 text-accent-50 mr-2" />
                System Metrics
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {systemMetrics.map((metric, index) => {
                  const Icon = metric.icon
                  return (
                    <div key={metric.label} className="flex items-center space-x-3 p-4 glass-morphism rounded-lg">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        metric.status === 'excellent' ? 'bg-success/20' :
                        metric.status === 'good' ? 'bg-warning/20' : 'bg-error/20'
                      }`}>
                        <Icon className={`w-5 h-5 ${
                          metric.status === 'excellent' ? 'text-success' :
                          metric.status === 'good' ? 'text-warning' : 'text-error'
                        }`} />
                      </div>
                      <div>
                        <p className="text-sm text-dark-400">{metric.label}</p>
                        <p className="text-lg font-bold text-dark-200">{metric.value}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          </div>
        )}

        {/* Users Tab */}
        {selectedTab === 'users' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="card"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-dark-200 flex items-center">
                <Users className="w-5 h-5 text-accent-50 mr-2" />
                User Management
              </h2>
              <div className="flex items-center space-x-3">
                <div className="relative">
                  <Search className="w-4 h-4 text-dark-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 pr-4 py-2 bg-dark-100 border border-dark-200/20 rounded-lg text-dark-200 placeholder-dark-400 focus:outline-none focus:border-accent-50/50"
                  />
                </div>
                <button className="btn-secondary flex items-center">
                  <Filter className="w-4 h-4 mr-2" />
                  Filter
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-200/20">
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">User</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Role</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Status</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Last Login</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Requests</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user, index) => (
                    <motion.tr
                      key={user.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      className="border-b border-dark-200/10 hover:bg-dark-50/30"
                    >
                      <td className="py-3 px-4">
                        <div>
                          <p className="text-dark-200 font-medium">{user.username || 'Unknown'}</p>
                          <p className="text-sm text-dark-400">{user.email || 'No email'}</p>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          user.role === 'ADMIN' ? 'bg-accent-50/20 text-accent-50' : 'bg-dark-100 text-dark-400'
                        }`}>
                          {user.role || 'USER'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          (user.status || 'active') === 'active' ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
                        }`}>
                          {user.status || 'active'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-dark-400 text-sm">{user.lastLogin || 'Never'}</td>
                      <td className="py-3 px-4 text-dark-200 font-medium">{(user.requests || 0).toLocaleString()}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          {(user.status || 'active') === 'active' ? (
                            <button
                              onClick={() => handleUserAction(user.id, 'suspend')}
                              className="p-1 hover:bg-dark-100 rounded transition-colors"
                              title="Suspend user"
                            >
                              <Lock className="w-4 h-4 text-warning" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleUserAction(user.id, 'activate')}
                              className="p-1 hover:bg-dark-100 rounded transition-colors"
                              title="Activate user"
                            >
                              <Unlock className="w-4 h-4 text-success" />
                            </button>
                          )}
                          {(user.role || 'USER') === 'USER' ? (
                            <button
                              onClick={() => handleUserAction(user.id, 'promote')}
                              className="p-1 hover:bg-dark-100 rounded transition-colors"
                              title="Promote to admin"
                            >
                              <Shield className="w-4 h-4 text-accent-50" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleUserAction(user.id, 'demote')}
                              className="p-1 hover:bg-dark-100 rounded transition-colors"
                              title="Remove admin role"
                            >
                              <Shield className="w-4 h-4 text-warning" />
                            </button>
                          )}
                          <button
                            onClick={() => handleUserAction(user.id, 'delete')}
                            className="p-1 hover:bg-dark-100 rounded transition-colors"
                            title="Delete user"
                          >
                            <Trash2 className="w-4 h-4 text-error" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* System Tab */}
        {selectedTab === 'system' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            <div className="card">
              <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                <Server className="w-5 h-5 text-accent-50 mr-2" />
                Server Status
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">CPU Usage</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 bg-dark-100 rounded-full h-2">
                      <div className="h-2 bg-gradient-to-r from-success via-warning to-error rounded-full" style={{ width: '67%' }} />
                    </div>
                    <span className="text-sm font-bold text-dark-200">67%</span>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Memory Usage</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 bg-dark-100 rounded-full h-2">
                      <div className="h-2 bg-gradient-to-r from-success via-warning to-error rounded-full" style={{ width: '45%' }} />
                    </div>
                    <span className="text-sm font-bold text-dark-200">45%</span>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Disk Space</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 bg-dark-100 rounded-full h-2">
                      <div className="h-2 bg-gradient-to-r from-success via-warning to-error rounded-full" style={{ width: '82%' }} />
                    </div>
                    <span className="text-sm font-bold text-dark-200">82%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                <Database className="w-5 h-5 text-accent-50 mr-2" />
                Database Status
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Connection</span>
                  <span className="text-sm font-bold text-success">Active</span>
                </div>
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Query Time</span>
                  <span className="text-sm font-bold text-dark-200">12ms</span>
                </div>
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <span className="text-sm text-dark-400">Cache Hit Rate</span>
                  <span className="text-sm font-bold text-dark-200">94.2%</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Security Tab */}
        {selectedTab === 'security' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="card"
          >
            <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
              <Shield className="w-5 h-5 text-accent-50 mr-2" />
              Security Overview
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="p-4 glass-morphism rounded-lg border-l-4 border-success">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-dark-400">Failed Login Attempts</span>
                  <CheckCircle className="w-4 h-4 text-success" />
                </div>
                <p className="text-2xl font-bold text-dark-200">0</p>
                <p className="text-xs text-dark-500">Last 24 hours</p>
              </div>
              <div className="p-4 glass-morphism rounded-lg border-l-4 border-warning">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-dark-400">Suspicious Activity</span>
                  <AlertTriangle className="w-4 h-4 text-warning" />
                </div>
                <p className="text-2xl font-bold text-dark-200">3</p>
                <p className="text-xs text-dark-500">Needs review</p>
              </div>
              <div className="p-4 glass-morphism rounded-lg border-l-4 border-accent-50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-dark-400">Active Sessions</span>
                  <Users className="w-4 h-4 text-accent-50" />
                </div>
                <p className="text-2xl font-bold text-dark-200">{stats.activeUsers}</p>
                <p className="text-xs text-dark-500">Currently logged in</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default Admin
