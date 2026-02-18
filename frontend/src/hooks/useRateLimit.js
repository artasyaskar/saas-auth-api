import { useState, useCallback, useEffect } from 'react'
import toast from 'react-hot-toast'

const RATE_LIMIT_CONFIG = {
  FREE: {
    requestsPerMinute: 60,
    monthlyQuota: 1000,
    currentRequests: 0,
    monthlyUsage: 0
  },
  PRO: {
    requestsPerMinute: 300,
    monthlyQuota: 10000,
    currentRequests: 0,
    monthlyUsage: 0
  }
}

export const useRateLimit = (userPlan = 'FREE') => {
  const [rateLimitStatus, setRateLimitStatus] = useState({
    requestsRemaining: RATE_LIMIT_CONFIG[userPlan].requestsPerMinute,
    quotaRemaining: RATE_LIMIT_CONFIG[userPlan].monthlyQuota,
    resetTime: null,
    isRateLimited: false,
    isQuotaExceeded: false
  })

  const [requestHistory, setRequestHistory] = useState([])
  const [usageStats, setUsageStats] = useState({
    totalRequests: 0,
    requestsThisMinute: 0,
    requestsToday: 0,
    requestsThisMonth: 0,
    topEndpoints: []
  })

  // Simulate real-time rate limiting
  const checkRateLimit = useCallback(() => {
    const now = Date.now()
    const oneMinuteAgo = now - 60000
    const recentRequests = requestHistory.filter(timestamp => timestamp > oneMinuteAgo)
    
    const config = RATE_LIMIT_CONFIG[userPlan]
    const requestsRemaining = Math.max(0, config.requestsPerMinute - recentRequests.length)
    const isRateLimited = recentRequests.length >= config.requestsPerMinute
    
    // Simulate monthly quota (in real app, this would come from backend)
    const monthlyUsage = Math.floor(Math.random() * config.monthlyQuota * 0.8) // Simulate 80% usage
    const quotaRemaining = Math.max(0, config.monthlyQuota - monthlyUsage)
    const isQuotaExceeded = monthlyUsage >= config.monthlyQuota
    
    setRateLimitStatus({
      requestsRemaining,
      quotaRemaining,
      resetTime: isRateLimited ? new Date(oneMinuteAgo + 60000) : null,
      isRateLimited,
      isQuotaExceeded
    })
    
    return { isRateLimited, isQuotaExceeded, requestsRemaining, quotaRemaining }
  }, [requestHistory, userPlan])

  // Simulate API call
  const makeRequest = useCallback(async (endpoint, method = 'GET') => {
    const { isRateLimited, isQuotaExceeded } = checkRateLimit()
    
    if (isRateLimited) {
      toast.error('Rate limit exceeded. Please wait a moment.')
      throw new Error('RATE_LIMIT_EXCEEDED')
    }
    
    if (isQuotaExceeded) {
      toast.error('Monthly quota exceeded. Please upgrade your plan.')
      throw new Error('QUOTA_EXCEEDED')
    }
    
    // Record the request
    const now = Date.now()
    setRequestHistory(prev => [...prev, now])
    
    // Update usage stats
    setUsageStats(prev => ({
      ...prev,
      totalRequests: prev.totalRequests + 1,
      requestsThisMinute: prev.requestsThisMinute + 1,
      requestsToday: prev.requestsToday + 1,
      requestsThisMonth: prev.requestsThisMonth + 1
    }))
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 200))
    
    return { success: true, data: { message: 'Request successful' } }
  }, [checkRateLimit])

  // Clean up old request history
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      const oneMinuteAgo = now - 60000
      setRequestHistory(prev => prev.filter(timestamp => timestamp > oneMinuteAgo))
    }, 10000) // Clean every 10 seconds
    
    return () => clearInterval(interval)
  }, [])

  // Update rate limit status periodically
  useEffect(() => {
    const interval = setInterval(() => {
      checkRateLimit()
    }, 1000) // Update every second
    
    return () => clearInterval(interval)
  }, [checkRateLimit])

  return {
    rateLimitStatus,
    usageStats,
    makeRequest,
    checkRateLimit,
    planConfig: RATE_LIMIT_CONFIG[userPlan]
  }
}
