import { useState, useEffect, useCallback } from 'react'

const useRealTimeData = () => {
  const [realTimeStats, setRealTimeStats] = useState({
    activeUsers: 3421,
    currentRequests: 0,
    avgResponseTime: 142,
    serverLoad: 67,
    uptime: 99.8,
    recentActivity: []
  })

  const generateRealisticActivity = useCallback(() => {
    const activities = [
      { type: 'login', user: 'john_doe', location: 'New York', time: 'just now' },
      { type: 'api_request', endpoint: '/auth/login', method: 'POST', status: 200, time: '2 seconds ago' },
      { type: 'registration', user: 'sarah_smith', location: 'London', time: '5 seconds ago' },
      { type: 'api_request', endpoint: '/users/profile', method: 'GET', status: 200, time: '8 seconds ago' },
      { type: 'error', message: 'Rate limit exceeded', user: 'mike_wilson', time: '12 seconds ago' },
      { type: 'login', user: 'alex_jones', location: 'Tokyo', time: '15 seconds ago' },
      { type: 'api_request', endpoint: '/admin/users', method: 'GET', status: 200, time: '18 seconds ago' },
      { type: 'security', action: 'Password changed', user: 'emma_brown', time: '25 seconds ago' },
      { type: 'api_request', endpoint: '/analytics/data', method: 'GET', status: 200, time: '30 seconds ago' },
      { type: 'registration', user: 'chris_davis', location: 'Paris', time: '35 seconds ago' },
    ]
    
    return activities[Math.floor(Math.random() * activities.length)]
  }, [])

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setRealTimeStats(prev => {
        // Simulate fluctuating metrics
        const userChange = Math.floor((Math.random() - 0.5) * 10)
        const requestChange = Math.floor((Math.random() - 0.5) * 50)
        const responseChange = (Math.random() - 0.5) * 10
        const loadChange = (Math.random() - 0.5) * 15
        
        const newActivity = generateRealisticActivity()
        
        return {
          activeUsers: Math.max(100, prev.activeUsers + userChange),
          currentRequests: Math.max(0, prev.currentRequests + requestChange),
          avgResponseTime: Math.max(50, Math.min(300, prev.avgResponseTime + responseChange)),
          serverLoad: Math.max(10, Math.min(100, prev.serverLoad + loadChange)),
          uptime: Math.min(99.9, prev.uptime + (Math.random() - 0.5) * 0.1),
          recentActivity: [newActivity, ...prev.recentActivity.slice(0, 9)]
        }
      })
    }, 2000) // Update every 2 seconds

    return () => clearInterval(interval)
  }, [generateRealisticActivity])

  return realTimeStats
}

export default useRealTimeData
