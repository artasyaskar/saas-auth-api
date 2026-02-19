import React, { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

const GoBackButton = () => {
  const navigate = useNavigate()
  const location = useLocation()

  // Hide on main dashboard / landing so it doesn't show on the welcome page
  const hideOnPaths = ['/dashboard', '/']
  const shouldHide = hideOnPaths.includes(location.pathname)

  if (shouldHide) return null

  const handleGoBack = () => {
    navigate(-1)
    // Delay scroll to allow page transition to complete first
    setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }, 100) // Wait 100ms for page transition
  }

  return (
    <motion.button
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={handleGoBack}
      className="group relative inline-flex items-center space-x-2 rounded-full bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 px-3 py-1.5 shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 transition-all duration-300"
    >
      {/* Arrow Icon */}
      <motion.span
        animate={{ x: [0, 2, 0] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        className="flex items-center justify-center"
      >
        <ArrowLeft className="w-4 h-4 text-white" />
      </motion.span>

      {/* Text */}
      <motion.span
        animate={{ opacity: [0.8, 1, 0.8] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        className="text-xs font-semibold text-white tracking-wide whitespace-nowrap"
      >
        Go Back
      </motion.span>

      {/* Subtle glow on hover */}
      <span className="pointer-events-none absolute inset-0 rounded-full bg-gradient-to-r from-purple-400/30 via-pink-400/30 to-blue-400/30 opacity-0 group-hover:opacity-100 blur-md transition-opacity duration-300" />
    </motion.button>
  )
}

export default GoBackButton
