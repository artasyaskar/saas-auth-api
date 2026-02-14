import React, { useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { 
  TrendingUp, 
  Users, 
  Activity,
  Zap,
  Globe,
  Shield
} from 'lucide-react'

const ThreeDCard = ({ 
  title, 
  value, 
  change, 
  icon: Icon, 
  color, 
  delay = 0,
  is3D = true,
  glowColor = 'rgba(139, 92, 246, 0.3)'
}) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const cardRef = useRef(null)

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!cardRef.current) return
      const rect = cardRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left - rect.width / 2
      const y = e.clientY - rect.top - rect.height / 2
      setMousePosition({ x, y })
    }

    const handleMouseLeave = () => {
      setMousePosition({ x: 0, y: 0 })
    }

    const card = cardRef.current
    if (card && is3D) {
      card.addEventListener('mousemove', handleMouseMove)
      card.addEventListener('mouseleave', handleMouseLeave)
    }

    return () => {
      if (card) {
        card.removeEventListener('mousemove', handleMouseMove)
        card.removeEventListener('mouseleave', handleMouseLeave)
      }
    }
  }, [is3D])

  const tiltStyle = is3D ? {
    transform: `perspective(1000px) rotateY(${mousePosition.x * 0.1}deg) rotateX(${-mousePosition.y * 0.1}deg) scale3d(1.05, 1.05, 1.05)`,
    transition: 'transform 0.1s ease-out',
    boxShadow: `${glowColor}, 0 10px 30px rgba(0, 0, 0, 0.2)`,
  } : {}

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 50, rotateX: 15 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ 
        duration: 0.6, 
        delay,
        type: "spring",
        stiffness: 100,
        damping: 15
      }}
      whileHover={{ 
        scale: 1.02,
        boxShadow: `${glowColor}, 0 20px 40px rgba(0, 0, 0, 0.3)`
      }}
      className="relative"
      style={tiltStyle}
    >
      {/* Glass morphism background */}
      <div className="absolute inset-0 glass-morphism rounded-xl border border-dark-200/20" />
      
      {/* Gradient border animation */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-accent-50/10 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-500" />
      
      {/* Content */}
      <div className="relative z-10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className={`w-12 h-12 bg-gradient-to-r ${color} rounded-xl flex items-center justify-center shadow-lg`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          
          <motion.div 
            className={`flex items-center space-x-1 px-3 py-1 rounded-full ${
              change > 0 ? 'bg-success/20 text-success' : 
              change < 0 ? 'bg-error/20 text-error' : 
              'bg-warning/20 text-warning'
            }`}
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            {change > 0 && <TrendingUp className="w-3 h-3" />}
            <span className="text-xs font-bold">{change > 0 ? '+' : ''}{Math.abs(change)}%</span>
          </motion.div>
        </div>
        
        <motion.h3 
          className="text-2xl font-bold text-dark-200 mb-1"
          animate={{ backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"] }}
          transition={{ duration: 3, repeat: Infinity }}
          style={{
            backgroundSize: "200% 200%",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            backgroundImage: `linear-gradient(90deg, #ffffff, #a78bfa, #c4b5fd, #ffffff)`
          }}
        >
          {value}
        </motion.h3>
        
        <p className="text-sm text-dark-400">
          {title}
        </p>
        
        {/* Animated particles */}
        {is3D && (
          <div className="absolute inset-0 pointer-events-none">
            {[...Array(6)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-accent-50/30 rounded-full"
                animate={{
                  x: [0, 100, 0],
                  y: [0, Math.random() * 100 - 50, 0],
                  opacity: [0, 1, 0]
                }}
                transition={{
                  duration: 3 + i * 0.5,
                  repeat: Infinity,
                  delay: i * 0.2
                }}
                style={{
                  left: `${20 + i * 15}%`,
                  top: `${20 + i * 10}%`
                }}
              />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default ThreeDCard
