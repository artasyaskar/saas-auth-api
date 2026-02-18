import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  User, 
  Mail, 
  Shield, 
  Calendar,
  Edit3,
  Save,
  Activity,
  ArrowLeft,
  Sparkles,
  Flame
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'
import { userAPI } from '../services/api'

const Profile = () => {
  const { user, updateUser } = useAuthStore()
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || ''
  })
  const [isLoading, setIsLoading] = useState(false)

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSave = async () => {
    setIsLoading(true)
    try {
      await userAPI.updateProfile(formData)
      updateUser(formData)
      setIsEditing(false)
      toast.success('Profile updated successfully! 🎉')
    } catch (error) {
      toast.error('Failed to update profile')
    }
    setIsLoading(false)
  }

  const handleCancel = () => {
    setFormData({
      username: user?.username || '',
      email: user?.email || ''
    })
    setIsEditing(false)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

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
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
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
          <div className="mb-8">
            <h1 className="text-3xl font-bold gradient-text mb-2">
              Profile Settings
            </h1>
            <p className="text-dark-400">
              Manage your account information and preferences
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Profile Card */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="lg:col-span-1"
            >
              <div className="card text-center">
                <div className="w-24 h-24 bg-gradient-to-r from-accent-50 to-accent-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <User className="w-12 h-12 text-white" />
                </div>
                
                <h2 className="text-xl font-bold text-dark-200 mb-2">
                  {user?.username}
                </h2>
                
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-center text-dark-400">
                    <Mail className="w-4 h-4 mr-2" />
                    {user?.email}
                  </div>
                  
                  <div className="flex items-center justify-center text-dark-400">
                    <Shield className="w-4 h-4 mr-2" />
                    {user?.role}
                  </div>
                  
                  <div className="flex items-center justify-center text-dark-400">
                    <Calendar className="w-4 h-4 mr-2" />
                    Joined {formatDate(user?.created_at)}
                  </div>
                </div>

                <div className="mt-6 p-4 glass-morphism rounded-lg">
                  <p className="text-xs text-dark-400 mb-2">Subscription</p>
                  <p className="text-lg font-bold gradient-text">
                    {user?.subscription_plan}
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Form */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="lg:col-span-2"
            >
              <div className="card">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-dark-200">
                    Account Information
                  </h2>
                  
                  {!isEditing ? (
                    <button
                      onClick={() => setIsEditing(true)}
                      className="flex items-center space-x-2 px-4 py-2 bg-accent-50/20 text-accent-50 rounded-lg hover:bg-accent-50/30 transition-colors"
                    >
                      <Edit3 className="w-4 h-4" />
                      <span>Edit</span>
                    </button>
                  ) : (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={handleSave}
                        disabled={isLoading}
                        className="flex items-center space-x-2 px-4 py-2 bg-success/20 text-success rounded-lg hover:bg-success/30 transition-colors disabled:opacity-50"
                      >
                        <Save className="w-4 h-4" />
                        <span>{isLoading ? 'Saving...' : 'Save'}</span>
                      </button>
                      
                      <button
                        onClick={handleCancel}
                        className="px-4 py-2 bg-dark-100 text-dark-400 rounded-lg hover:bg-dark-200 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      disabled={!isEditing}
                      className="input-field disabled:opacity-50 disabled:cursor-not-allowed"
                      placeholder="Enter your username"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      disabled={!isEditing}
                      className="input-field disabled:opacity-50 disabled:cursor-not-allowed"
                      placeholder="Enter your email"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-dark-300 mb-2">
                        Account Status
                      </label>
                      <div className="flex items-center space-x-2">
                        <div className={`w-3 h-3 rounded-full ${
                          user?.is_active ? 'bg-success' : 'bg-error'
                        }`}></div>
                        <span className="text-dark-400">
                          {user?.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-dark-300 mb-2">
                        Account Type
                      </label>
                      <div className="flex items-center space-x-2">
                        <Shield className="w-4 h-4 text-accent-50" />
                        <span className="text-dark-400 capitalize">
                          {user?.role?.toLowerCase()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Activity Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-8 card"
          >
            <div className="flex items-center mb-6">
              <Activity className="w-5 h-5 text-accent-50 mr-2" />
              <h2 className="text-xl font-semibold text-dark-200">
                Recent Activity
              </h2>
            </div>
            
            <div className="space-y-4">
              {[
                { action: 'Profile updated', time: '2 hours ago', status: 'success' },
                { action: 'Password changed', time: '3 days ago', status: 'success' },
                { action: 'Email verified', time: '1 week ago', status: 'success' },
                { action: 'Account created', time: formatDate(user?.created_at), status: 'info' },
              ].map((activity, index) => (
                <div key={index} className="flex items-center justify-between p-4 glass-morphism rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${
                      activity.status === 'success' ? 'bg-success' : 
                      activity.status === 'info' ? 'bg-accent-50' : 'bg-warning'
                    }`}></div>
                    <div>
                      <p className="text-sm font-medium text-dark-200">
                        {activity.action}
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
        </motion.div>
      </div>
    </div>
  )
}

export default Profile
