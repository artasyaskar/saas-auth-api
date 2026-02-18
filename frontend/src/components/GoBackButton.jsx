import React from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles } from 'lucide-react'

const GoBackButton = () => {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="absolute top-6 left-6 z-50"
    >
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => navigate(-1)}
        className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 p-4 shadow-2xl shadow-purple-500/30 hover:shadow-purple-500/50 transition-all duration-300 min-w-[140px]"
      >
        {/* Button Content */}
        <div className="relative flex items-center space-x-3 text-white font-bold">
          <motion.div
            animate={{ x: [0, 2, 0] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          >
            <ArrowLeft className="w-6 h-6" />
          </motion.div>
          <motion.span
            animate={{ opacity: [0.8, 1, 0.8] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="bg-gradient-to-r from-white via-purple-200 to-pink-200 bg-clip-text text-transparent text-lg"
          >
            Go Back
          </motion.span>
          
          {/* Floating Sparkle */}
          <motion.div
            animate={{ rotate: 360, scale: [1, 1.2, 1] }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="absolute -top-1 -right-1"
          >
            <Sparkles className="w-5 h-5 text-yellow-300" />
          </motion.div>
        </div>
        
        {/* Hover Glow Effect */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-400/30 via-pink-400/30 to-blue-400/30 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-300" />
        
        {/* Shimmer Border */}
        <div className="absolute inset-0 rounded-xl border-2 border-purple-400/20 group-hover:border-purple-400/40 transition-all duration-300" />
      </motion.button>
    </motion.div>
  )
}

export default GoBackButton
