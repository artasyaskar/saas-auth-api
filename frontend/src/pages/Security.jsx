import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  Shield, 
  Key, 
  Smartphone, 
  Mail, 
  Eye, 
  EyeOff,
  Save,
  AlertTriangle,
  CheckCircle
} from 'lucide-react'
import toast from 'react-hot-toast'

const Security = () => {
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  })
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false)
  const [emailNotifications, setEmailNotifications] = useState(true)

  const handlePasswordChange = (e) => {
    setPasswordData({
      ...passwordData,
      [e.target.name]: e.target.value
    })
  }

  const handlePasswordSubmit = (e) => {
    e.preventDefault()
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    
    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    
    // Simulate password change
    toast.success('Password changed successfully! 🔒')
    setPasswordData({
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    })
    setShowPasswordForm(false)
  }

  const toggleTwoFactor = () => {
    setTwoFactorEnabled(!twoFactorEnabled)
    toast.success(!twoFactorEnabled ? '2FA enabled! 🛡️' : '2FA disabled')
  }

  const toggleEmailNotifications = () => {
    setEmailNotifications(!emailNotifications)
    toast.success(!emailNotifications ? 'Email notifications enabled 📧' : 'Email notifications disabled')
  }

  const securityFeatures = [
    {
      icon: Key,
      title: 'Password',
      description: 'Change your account password',
      action: () => setShowPasswordForm(!showPasswordForm),
      status: 'Last changed 30 days ago'
    },
    {
      icon: Smartphone,
      title: 'Two-Factor Authentication',
      description: 'Add an extra layer of security',
      action: toggleTwoFactor,
      status: twoFactorEnabled ? 'Enabled' : 'Disabled',
      enabled: twoFactorEnabled
    },
    {
      icon: Mail,
      title: 'Email Notifications',
      description: 'Get notified about account activity',
      action: toggleEmailNotifications,
      status: emailNotifications ? 'Enabled' : 'Disabled',
      enabled: emailNotifications
    }
  ]

  return (
    <div className="min-h-screen bg-dark">
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold gradient-text mb-2">
              Security Settings
            </h1>
            <p className="text-dark-400">
              Manage your account security and privacy settings
            </p>
          </div>

          {/* Security Overview */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="card mb-8"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-dark-200">
                Security Overview
              </h2>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-success" />
                <span className="text-sm text-success">Good Security</span>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 glass-morphism rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-success/20 rounded-lg flex items-center justify-center">
                    <Shield className="w-5 h-5 text-success" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-dark-200">Account Protected</p>
                    <p className="text-xs text-dark-400">2FA available</p>
                  </div>
                </div>
              </div>
              
              <div className="p-4 glass-morphism rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-warning/20 rounded-lg flex items-center justify-center">
                    <AlertTriangle className="w-5 h-5 text-warning" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-dark-200">Password Update</p>
                    <p className="text-xs text-dark-400">Consider updating</p>
                  </div>
                </div>
              </div>
              
              <div className="p-4 glass-morphism rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-accent-50/20 rounded-lg flex items-center justify-center">
                    <Mail className="w-5 h-5 text-accent-50" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-dark-200">Email Verified</p>
                    <p className="text-xs text-dark-400">Verified</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Security Features */}
          <div className="space-y-4">
            {securityFeatures.map((feature, index) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 + index * 0.1 }}
                  className="card"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        feature.enabled 
                          ? 'bg-success/20' 
                          : 'bg-dark-100/50'
                      }`}>
                        <Icon className={`w-6 h-6 ${
                          feature.enabled ? 'text-success' : 'text-dark-400'
                        }`} />
                      </div>
                      <div>
                        <h3 className="text-lg font-medium text-dark-200">
                          {feature.title}
                        </h3>
                        <p className="text-sm text-dark-400">
                          {feature.description}
                        </p>
                        <p className="text-xs text-dark-500 mt-1">
                          Status: {feature.status}
                        </p>
                      </div>
                    </div>
                    
                    <button
                      onClick={feature.action}
                      className={`px-4 py-2 rounded-lg font-medium transition-all duration-300 ${
                        feature.enabled
                          ? 'bg-success/20 text-success hover:bg-success/30'
                          : 'bg-dark-100 text-dark-400 hover:bg-dark-200'
                      }`}
                    >
                      {feature.title === 'Password' ? 'Change' : 
                       feature.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </motion.div>
              )
            })}
          </div>

          {/* Password Change Form */}
          {showPasswordForm && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-6 card"
            >
              <h3 className="text-lg font-semibold text-dark-200 mb-6">
                Change Password
              </h3>
              
              <form onSubmit={handlePasswordSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPasswords.current ? 'text' : 'password'}
                      name="currentPassword"
                      value={passwordData.currentPassword}
                      onChange={handlePasswordChange}
                      required
                      className="input-field pr-12"
                      placeholder="Enter current password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords({
                        ...showPasswords,
                        current: !showPasswords.current
                      })}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dark-400 hover:text-dark-300 transition-colors"
                    >
                      {showPasswords.current ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPasswords.new ? 'text' : 'password'}
                      name="newPassword"
                      value={passwordData.newPassword}
                      onChange={handlePasswordChange}
                      required
                      className="input-field pr-12"
                      placeholder="Enter new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords({
                        ...showPasswords,
                        new: !showPasswords.new
                      })}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dark-400 hover:text-dark-300 transition-colors"
                    >
                      {showPasswords.new ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPasswords.confirm ? 'text' : 'password'}
                      name="confirmPassword"
                      value={passwordData.confirmPassword}
                      onChange={handlePasswordChange}
                      required
                      className="input-field pr-12"
                      placeholder="Confirm new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords({
                        ...showPasswords,
                        confirm: !showPasswords.confirm
                      })}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dark-400 hover:text-dark-300 transition-colors"
                    >
                      {showPasswords.confirm ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                <div className="flex space-x-4">
                  <button
                    type="submit"
                    className="btn-primary flex items-center"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Update Password
                  </button>
                  
                  <button
                    type="button"
                    onClick={() => setShowPasswordForm(false)}
                    className="px-6 py-3 bg-dark-100 text-dark-400 rounded-lg hover:bg-dark-200 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default Security
