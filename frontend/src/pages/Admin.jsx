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
  Trash2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'
import { adminAPI } from '../services/api'

const Admin = () => {
  const { user } = useAuthStore()
  const [users, setUsers] = useState([])
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    newUsersToday: 0,
    totalRequests: 0
  })
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchUsers()
    fetchStats()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await adminAPI.getUsers()
      setUsers(response.data)
    } catch (error) {
      toast.error('Failed to fetch users')
    }
    setIsLoading(false)
  }

  const fetchStats = async () => {
    try {
      const response = await adminAPI.getUserStats()
      setStats(response.data)
    } catch (error) {
      toast.error('Failed to fetch stats')
    }
  }

  const handleSuspendUser = async (userId) => {
    try {
      await adminAPI.suspendUser(userId)
      toast.success('User suspended successfully')
      fetchUsers()
    } catch (error) {
      toast.error('Failed to suspend user')
    }
  }

  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const statCards = [
    {
      title: 'Total Users',
      value: stats.totalUsers.toLocaleString(),
      change: '+12%',
      icon: Users,
      color: 'from-blue-50 to-blue-100'
    },
    {
      title: 'Active Users',
      value: stats.activeUsers.toLocaleString(),
      change: '+8%',
      icon: UserCheck,
      color: 'from-green-50 to-green-100'
    },
    {
      title: 'New Today',
      value: stats.newUsersToday.toLocaleString(),
      change: '+23%',
      icon: TrendingUp,
      color: 'from-purple-50 to-purple-100'
    },
    {
      title: 'Total Requests',
      value: stats.totalRequests.toLocaleString(),
      change: '+15%',
      icon: Activity,
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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold gradient-text mb-2">
                Admin Dashboard
              </h1>
              <p className="text-dark-400">
                Manage users and monitor system activity
              </p>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className="w-10 h-10 bg-gradient-to-r from-accent-50 to-accent-100 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <span className="text-sm font-medium text-dark-300">
                {user?.username}
              </span>
            </div>
          </div>
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

        {/* Users Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-dark-200">
              User Management
            </h2>
            
            <div className="flex items-center space-x-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-dark-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-dark-50/50 border border-dark-200/30 rounded-lg text-dark-200 placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-accent-50/50 focus:border-accent-50 transition-all duration-300"
                />
              </div>
              
              {/* Filter */}
              <button className="p-2 rounded-lg text-dark-400 hover:text-dark-200 hover:bg-dark-100/50 transition-colors">
                <Filter className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-200/20">
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-400">User</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-400">Role</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-400">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-400">Plan</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-400">Joined</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan="6" className="text-center py-8">
                      <div className="flex items-center justify-center">
                        <div className="loading-spinner mr-2"></div>
                        Loading users...
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((user, index) => (
                    <motion.tr
                      key={user.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      className="border-b border-dark-200/10 hover:bg-dark-50/20 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-gradient-to-r from-accent-50 to-accent-100 rounded-full flex items-center justify-center">
                            <Users className="w-4 h-4 text-white" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-dark-200">
                              {user.username}
                            </p>
                            <p className="text-xs text-dark-400">
                              {user.email}
                            </p>
                          </div>
                        </div>
                      </td>
                      
                      <td className="py-4 px-4">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          user.role === 'ADMIN' 
                            ? 'bg-accent-50/20 text-accent-50' 
                            : 'bg-dark-100/50 text-dark-400'
                        }`}>
                          <Shield className="w-3 h-3 mr-1" />
                          {user.role}
                        </span>
                      </td>
                      
                      <td className="py-4 px-4">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          user.is_active 
                            ? 'bg-success/20 text-success' 
                            : 'bg-error/20 text-error'
                        }`}>
                          <div className={`w-2 h-2 rounded-full mr-1 ${
                            user.is_active ? 'bg-success' : 'bg-error'
                          }`}></div>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      
                      <td className="py-4 px-4">
                        <span className="text-sm text-dark-400">
                          {user.subscription_plan}
                        </span>
                      </td>
                      
                      <td className="py-4 px-4">
                        <span className="text-sm text-dark-400">
                          {new Date(user.created_at).toLocaleDateString()}
                        </span>
                      </td>
                      
                      <td className="py-4 px-4">
                        <div className="flex items-center space-x-2">
                          <button className="p-1 rounded text-dark-400 hover:text-dark-200 hover:bg-dark-100/50 transition-colors">
                            <Eye className="w-4 h-4" />
                          </button>
                          
                          <button className="p-1 rounded text-dark-400 hover:text-dark-200 hover:bg-dark-100/50 transition-colors">
                            <Edit className="w-4 h-4" />
                          </button>
                          
                          <button
                            onClick={() => handleSuspendUser(user.id)}
                            className="p-1 rounded text-dark-400 hover:text-error hover:bg-error/20 transition-colors"
                          >
                            <UserX className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Admin
