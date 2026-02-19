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
  Upload,
  Key,
  CreditCard,
  Mail,
  Calendar,
  MapPin,
  Phone,
  UserPlus,
  UserMinus,
  ShieldAlert,
  FileText,
  DollarSign,
  ActivityIcon,
  Cpu,
  HardDrive,
  Wifi,
  AlertCircle,
  Ban,
  CheckSquare,
  Sparkles,
  Flame
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'
import { adminAPI } from '../services/api'

const Admin = () => {
  const { user } = useAuthStore()
  
  const generateMockUsers = () => [
    { 
      id: 1, 
      username: 'john_doe', 
      email: 'john@example.com', 
      role: 'USER', 
      status: 'active', 
      lastLogin: '2 min ago', 
      requests: 1234, 
      plan: 'PRO',
      firstName: 'John',
      lastName: 'Doe',
      phone: '+1-555-0123',
      location: 'New York, USA',
      joinDate: '2024-01-15',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=john',
      apiKeys: ['pk_live_123456', 'pk_test_789012'],
      lastActivity: 'API call to /users',
      mfaEnabled: true,
      emailVerified: true,
      subscriptionStatus: 'active',
      billingCycle: 'monthly'
    },
    { 
      id: 2, 
      username: 'sarah_smith', 
      email: 'sarah@example.com', 
      role: 'ADMIN', 
      status: 'active', 
      lastLogin: '5 min ago', 
      requests: 892, 
      plan: 'PRO',
      firstName: 'Sarah',
      lastName: 'Smith',
      phone: '+1-555-0456',
      location: 'London, UK',
      joinDate: '2024-02-20',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=sarah',
      apiKeys: ['pk_live_234567'],
      lastActivity: 'Dashboard login',
      mfaEnabled: true,
      emailVerified: true,
      subscriptionStatus: 'active',
      billingCycle: 'yearly'
    },
    { 
      id: 3, 
      username: 'mike_wilson', 
      email: 'mike@example.com', 
      role: 'USER', 
      status: 'suspended', 
      lastLogin: '2 hours ago', 
      requests: 567, 
      plan: 'FREE',
      firstName: 'Mike',
      lastName: 'Wilson',
      phone: '+1-555-0789',
      location: 'Toronto, Canada',
      joinDate: '2024-03-10',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=mike',
      apiKeys: ['pk_test_345678'],
      lastActivity: 'Failed login attempt',
      mfaEnabled: false,
      emailVerified: false,
      subscriptionStatus: 'cancelled',
      billingCycle: 'monthly'
    },
    { 
      id: 4, 
      username: 'alex_jones', 
      email: 'alex@example.com', 
      role: 'USER', 
      status: 'active', 
      lastLogin: '1 min ago', 
      requests: 2341, 
      plan: 'PRO',
      firstName: 'Alex',
      lastName: 'Jones',
      phone: '+1-555-0901',
      location: 'Sydney, Australia',
      joinDate: '2024-01-05',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=alex',
      apiKeys: ['pk_live_456789', 'pk_test_567890', 'pk_live_678901'],
      lastActivity: 'API call to /analytics',
      mfaEnabled: true,
      emailVerified: true,
      subscriptionStatus: 'active',
      billingCycle: 'monthly'
    },
    { 
      id: 5, 
      username: 'emma_brown', 
      email: 'emma@example.com', 
      role: 'USER', 
      status: 'active', 
      lastLogin: '10 min ago', 
      requests: 445, 
      plan: 'FREE',
      firstName: 'Emma',
      lastName: 'Brown',
      phone: '+1-555-0234',
      location: 'Berlin, Germany',
      joinDate: '2024-04-01',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=emma',
      apiKeys: ['pk_test_789012'],
      lastActivity: 'Profile update',
      mfaEnabled: false,
      emailVerified: true,
      subscriptionStatus: 'trial',
      billingCycle: 'monthly'
    },
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
  const [selectedUser, setSelectedUser] = useState(null)
  const [showUserModal, setShowUserModal] = useState(false)
  const [showSystemSettings, setShowSystemSettings] = useState(false)
  const [showAuditLogs, setShowAuditLogs] = useState(false)
  const [showRevenueAnalytics, setShowRevenueAnalytics] = useState(false)

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
          <div className="flex space-x-1 bg-dark-50/50 p-1 rounded-lg overflow-x-auto">
            {[
              { id: 'overview', label: 'Overview', icon: BarChart3 },
              { id: 'users', label: 'Users', icon: Users },
              { id: 'billing', label: 'Billing', icon: CreditCard },
              { id: 'system', label: 'System', icon: Server },
              { id: 'security', label: 'Security', icon: Shield },
              { id: 'audit', label: 'Audit', icon: FileText },
              { id: 'settings', label: 'Settings', icon: Settings }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id)}
                className={`flex items-center space-x-2 py-2 px-4 rounded-md transition-all duration-200 whitespace-nowrap ${
                  selectedTab === tab.id
                    ? 'bg-dark-200 text-white shadow-lg'
                    : 'text-dark-400 hover:text-white hover:bg-dark-100/50'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
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
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Plan</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Usage</th>
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
                          (user.plan || 'FREE') === 'PRO' ? 'bg-yellow-50/20 text-yellow-50' : 'bg-gray-50/20 text-gray-400'
                        }`}>
                          {user.plan || 'FREE'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <div className="w-16 bg-dark-100 rounded-full h-2">
                            <div 
                              className="h-2 bg-gradient-to-r from-success via-warning to-error rounded-full"
                              style={{ width: `${Math.min(100, ((user.requests || 0) / ((user.plan === 'PRO' ? 10000 : 1000))) * 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-dark-400">
                            {Math.round(((user.requests || 0) / ((user.plan === 'PRO' ? 10000 : 1000))) * 100)}%
                          </span>
                        </div>
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

        {/* Billing Tab */}
        {selectedTab === 'billing' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            {/* Revenue Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-green-600 rounded-xl flex items-center justify-center">
                    <DollarSign className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-sm font-bold text-success">+23%</span>
                </div>
                <h3 className="text-2xl font-bold text-dark-200">$12,847</h3>
                <p className="text-sm text-dark-400">Monthly Revenue</p>
              </div>
              
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
                    <Users className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-sm font-bold text-success">+15%</span>
                </div>
                <h3 className="text-2xl font-bold text-dark-200">1,234</h3>
                <p className="text-sm text-dark-400">Active Subscriptions</p>
              </div>
              
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-yellow-600 rounded-xl flex items-center justify-center">
                    <TrendingUp className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-sm font-bold text-warning">+8%</span>
                </div>
                <h3 className="text-2xl font-bold text-dark-200">$29.00</h3>
                <p className="text-sm text-dark-400">Avg Revenue/User</p>
              </div>
              
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
                    <ActivityIcon className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-sm font-bold text-success">+12%</span>
                </div>
                <h3 className="text-2xl font-bold text-dark-200">94.2%</h3>
                <p className="text-sm text-dark-400">Retention Rate</p>
              </div>
            </div>

            {/* Plan Distribution */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="card">
                <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                  <CreditCard className="w-5 h-5 text-accent-50 mr-2" />
                  Plan Distribution
                </h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-gray-500 rounded-lg flex items-center justify-center">
                        <span className="text-white text-xs font-bold">F</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-dark-200">Free Plan</p>
                        <p className="text-xs text-dark-400">1,234 users</p>
                      </div>
                    </div>
                    <span className="text-sm font-bold text-dark-200">45.2%</span>
                  </div>
                  
                  <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-yellow-500 rounded-lg flex items-center justify-center">
                        <span className="text-white text-xs font-bold">P</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-dark-200">Pro Plan</p>
                        <p className="text-xs text-dark-400">892 users</p>
                      </div>
                    </div>
                    <span className="text-sm font-bold text-dark-200">32.7%</span>
                  </div>
                  
                  <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                        <span className="text-white text-xs font-bold">E</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-dark-200">Enterprise</p>
                        <p className="text-xs text-dark-400">156 users</p>
                      </div>
                    </div>
                    <span className="text-sm font-bold text-dark-200">5.7%</span>
                  </div>
                </div>
              </div>

              {/* Recent Transactions */}
              <div className="card">
                <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                  <DollarSign className="w-5 h-5 text-accent-50 mr-2" />
                  Recent Transactions
                </h2>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {[
                    { user: 'John Doe', plan: 'Pro', amount: '$29.00', status: 'completed', date: '2 hours ago' },
                    { user: 'Sarah Smith', plan: 'Pro', amount: '$290.00', status: 'completed', date: '5 hours ago' },
                    { user: 'Alex Jones', plan: 'Enterprise', amount: '$299.00', status: 'pending', date: '1 day ago' },
                    { user: 'Emma Brown', plan: 'Free', amount: '$0.00', status: 'completed', date: '2 days ago' },
                    { user: 'Mike Wilson', plan: 'Pro', amount: '$29.00', status: 'failed', date: '3 days ago' }
                  ].map((transaction, index) => (
                    <div key={index} className="flex items-center justify-between p-3 glass-morphism rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          transaction.status === 'completed' ? 'bg-success/20' :
                          transaction.status === 'pending' ? 'bg-warning/20' :
                          'bg-error/20'
                        }`}>
                          <DollarSign className={`w-4 h-4 ${
                            transaction.status === 'completed' ? 'text-success' :
                            transaction.status === 'pending' ? 'text-warning' :
                            'text-error'
                          }`} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-dark-200">{transaction.user}</p>
                          <p className="text-xs text-dark-400">{transaction.plan} • {transaction.date}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-dark-200">{transaction.amount}</p>
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          transaction.status === 'completed' ? 'bg-success/20 text-success' :
                          transaction.status === 'pending' ? 'bg-warning/20 text-warning' :
                          'bg-error/20 text-error'
                        }`}>
                          {transaction.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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

        {/* Audit Tab */}
        {selectedTab === 'audit' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="card"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-dark-200 flex items-center">
                <FileText className="w-5 h-5 text-accent-50 mr-2" />
                Audit Logs
              </h2>
              <div className="flex space-x-3">
                <button className="btn-secondary flex items-center">
                  <Download className="w-4 h-4 mr-2" />
                  Export Logs
                </button>
                <button className="btn-primary flex items-center">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </button>
              </div>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {[
                { id: 1, user: 'John Doe', action: 'API Key Created', resource: '/api/users', timestamp: '2 min ago', ip: '192.168.1.1', status: 'success' },
                { id: 2, user: 'Sarah Smith', action: 'Login Attempt', resource: '/auth/login', timestamp: '5 min ago', ip: '192.168.1.2', status: 'success' },
                { id: 3, user: 'Mike Wilson', action: 'Failed Login', resource: '/auth/login', timestamp: '10 min ago', ip: '192.168.1.3', status: 'failed' },
                { id: 4, user: 'Alex Jones', action: 'Plan Upgraded', resource: '/billing/upgrade', timestamp: '15 min ago', ip: '192.168.1.4', status: 'success' },
                { id: 5, user: 'Emma Brown', action: 'Password Reset', resource: '/auth/reset', timestamp: '20 min ago', ip: '192.168.1.5', status: 'success' },
                { id: 6, user: 'System', action: 'Rate Limit Exceeded', resource: '/api/data', timestamp: '25 min ago', ip: '192.168.1.6', status: 'warning' },
                { id: 7, user: 'John Doe', action: 'User Suspended', resource: '/admin/users/3', timestamp: '30 min ago', ip: '192.168.1.1', status: 'success' },
                { id: 8, user: 'Sarah Smith', action: 'API Key Deleted', resource: '/api/keys/pk_live_234567', timestamp: '35 min ago', ip: '192.168.1.2', status: 'success' }
              ].map((log, index) => (
                <div key={log.id} className="flex items-center justify-between p-4 glass-morphism rounded-lg border-l-4 border-l-transparent hover:border-l-accent-50/50 transition-colors">
                  <div className="flex items-center space-x-4">
                    <div className={`w-2 h-2 rounded-full ${
                      log.status === 'success' ? 'bg-success' :
                      log.status === 'failed' ? 'bg-error' :
                      'bg-warning'
                    }`} />
                    <div>
                      <p className="text-sm font-medium text-dark-200">{log.action}</p>
                      <p className="text-xs text-dark-400">{log.user} • {log.resource} • {log.ip}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-dark-400">{log.timestamp}</p>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      log.status === 'success' ? 'bg-success/20 text-success' :
                      log.status === 'failed' ? 'bg-error/20 text-error' :
                      'bg-warning/20 text-warning'
                    }`}>
                      {log.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Settings Tab */}
        {selectedTab === 'settings' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* System Settings */}
            <div className="card">
              <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                <Settings className="w-5 h-5 text-accent-50 mr-2" />
                System Settings
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-dark-200">Maintenance Mode</p>
                    <p className="text-xs text-dark-400">Temporarily disable platform</p>
                  </div>
                  <button className="w-12 h-6 bg-dark-100 rounded-full relative transition-colors">
                    <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 left-0.5 transition-transform" />
                  </button>
                </div>
                
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-dark-200">API Rate Limiting</p>
                    <p className="text-xs text-dark-400">Enable rate limiting</p>
                  </div>
                  <button className="w-12 h-6 bg-success rounded-full relative transition-colors">
                    <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 right-0.5 transition-transform" />
                  </button>
                </div>
                
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-dark-200">Email Notifications</p>
                    <p className="text-xs text-dark-400">Send system alerts</p>
                  </div>
                  <button className="w-12 h-6 bg-success rounded-full relative transition-colors">
                    <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 right-0.5 transition-transform" />
                  </button>
                </div>
                
                <div className="flex justify-between items-center p-3 glass-morphism rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-dark-200">Auto Backup</p>
                    <p className="text-xs text-dark-400">Daily database backup</p>
                  </div>
                  <button className="w-12 h-6 bg-success rounded-full relative transition-colors">
                    <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 right-0.5 transition-transform" />
                  </button>
                </div>
              </div>
            </div>

            {/* User Settings */}
            <div className="card">
              <h2 className="text-xl font-semibold text-dark-200 mb-6 flex items-center">
                <Users className="w-5 h-5 text-accent-50 mr-2" />
                User Settings
              </h2>
              <div className="space-y-4">
                <div className="p-3 glass-morphism rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm font-medium text-dark-200">Default User Plan</p>
                    <select className="bg-dark-100 border border-dark-200/20 rounded-lg text-dark-200 px-3 py-1 text-sm">
                      <option>FREE</option>
                      <option>PRO</option>
                      <option>ENTERPRISE</option>
                    </select>
                  </div>
                  <p className="text-xs text-dark-400">New users start with this plan</p>
                </div>
                
                <div className="p-3 glass-morphism rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm font-medium text-dark-200">Max API Keys</p>
                    <input type="number" defaultValue="5" className="bg-dark-100 border border-dark-200/20 rounded-lg text-dark-200 px-3 py-1 text-sm w-20" />
                  </div>
                  <p className="text-xs text-dark-400">Maximum keys per user</p>
                </div>
                
                <div className="p-3 glass-morphism rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm font-medium text-dark-200">Session Timeout</p>
                    <input type="number" defaultValue="24" className="bg-dark-100 border border-dark-200/20 rounded-lg text-dark-200 px-3 py-1 text-sm w-20" />
                  </div>
                  <p className="text-xs text-dark-400">Hours before logout</p>
                </div>
                
                <div className="p-3 glass-morphism rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm font-medium text-dark-200">Require MFA</p>
                    <button className="w-12 h-6 bg-warning rounded-full relative transition-colors">
                      <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 left-0.5 transition-transform" />
                    </button>
                  </div>
                  <p className="text-xs text-dark-400">Force 2FA for all users</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default Admin
