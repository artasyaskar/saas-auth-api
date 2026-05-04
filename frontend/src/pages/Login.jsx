import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Shield, ArrowRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'

const Login = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    const result = await login(formData)
    
    if (result.success) {
      toast.success('Welcome back! 🎉')
      navigate('/dashboard')
    } else {
      toast.error(result.error)
    }
    
    setIsLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dark via-dark-50 to-dark-100 p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-accent-50/20 rounded-full blur-3xl animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent-100/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '3s' }}></div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="glass-morphism rounded-2xl p-8 shadow-2xl border border-dark-200/20">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              className="w-16 h-16 bg-gradient-to-r from-accent-50 to-accent-100 rounded-2xl flex items-center justify-center"
            >
              <Shield className="w-8 h-8 text-white" />
            </motion.div>
          </div>

          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold gradient-text mb-2">Welcome Back</h1>
            <p className="text-dark-400">Sign in to your account to continue</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Username
              </label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                className="input-field"
                placeholder="Enter your username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="input-field pr-12"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dark-400 hover:text-dark-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="btn-primary w-full relative overflow-hidden group"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="loading-spinner mr-2"></div>
                  Signing in...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <span>Sign In</span>
                  <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-1" />
                </div>
              )}
            </motion.button>
          </form>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-dark-400">
              Don't have an account?{' '}
              <Link 
                to="/register" 
                className="text-accent-50 hover:text-accent-100 font-medium transition-colors"
              >
                Sign up
              </Link>
            </p>
          </div>

          {/* Demo credentials hint */}
          <div className="mt-6 p-4 glass-morphism rounded-lg border border-accent-50/20">
            <p className="text-xs text-dark-400 text-center">
              <span className="font-medium text-dark-300">Demo Admin:</span> admin / admin123
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default Login
