import React from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, Flame } from 'lucide-react'

const GoBackButton = () => {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="absolute top-8 left-4 z-50"
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
  )
}

export default GoBackButton
