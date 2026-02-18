import React from 'react'
import { motion } from 'framer-motion'
import { Check, X, Zap, Shield, Crown, Star } from 'lucide-react'

const PLANS = {
  FREE: {
    name: 'Free',
    price: '$0',
    period: 'month',
    icon: Star,
    color: 'from-gray-500 to-gray-600',
    features: [
      '1,000 API requests/month',
      '60 requests/minute',
      'Basic usage tracking',
      'Community support',
      'Standard endpoints'
    ],
    limitations: [
      'No advanced analytics',
      'No priority support',
      'Limited endpoints'
    ],
    popular: false
  },
  PRO: {
    name: 'Pro',
    price: '$29',
    period: 'month',
    icon: Crown,
    color: 'from-purple-500 to-pink-500',
    features: [
      '10,000 API requests/month',
      '300 requests/minute',
      'Advanced analytics',
      'Priority support',
      'All endpoints access',
      'Custom rate limits',
      'API key management',
      'Webhook support'
    ],
    limitations: [],
    popular: true
  },
  ENTERPRISE: {
    name: 'Enterprise',
    price: 'Custom',
    period: 'pricing',
    icon: Shield,
    color: 'from-blue-500 to-cyan-500',
    features: [
      'Unlimited API requests',
      'Custom rate limits',
      'Dedicated support',
      'SLA guarantee',
      'Custom endpoints',
      'Advanced security',
      'White-label options',
      'On-premise deployment'
    ],
    limitations: [],
    popular: false
  }
}

const BillingPlan = ({ currentPlan = 'FREE', onUpgrade, onCancel }) => {
  return (
    <div className="min-h-screen bg-dark pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl font-bold gradient-text mb-4">
          Choose Your Plan
        </h1>
        <p className="text-xl text-dark-400 max-w-2xl mx-auto">
          Scale your API usage with our flexible pricing plans. Upgrade anytime to unlock more features.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        {Object.entries(PLANS).map(([planKey, plan], index) => {
          const Icon = plan.icon
          const isCurrentPlan = planKey === currentPlan
          
          return (
            <motion.div
              key={planKey}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className={`relative ${
                plan.popular ? 'scale-105' : ''
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-1 rounded-full text-sm font-bold">
                    MOST POPULAR
                  </span>
                </div>
              )}
              
              <div className={`card h-full ${
                plan.popular ? 'border-2 border-purple-500/50' : ''
              } ${isCurrentPlan ? 'ring-2 ring-success/50' : ''}`}>
                <div className="text-center mb-8">
                  <div className={`w-16 h-16 bg-gradient-to-r ${plan.color} rounded-xl flex items-center justify-center mx-auto mb-4`}>
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-dark-200 mb-2">{plan.name}</h3>
                  <div className="flex items-baseline justify-center">
                    <span className="text-4xl font-bold text-dark-200">{plan.price}</span>
                    <span className="text-dark-400 ml-2">/{plan.period}</span>
                  </div>
                </div>

                <div className="space-y-4 mb-8">
                  {plan.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-start space-x-3">
                      <Check className="w-5 h-5 text-success mt-0.5 flex-shrink-0" />
                      <span className="text-dark-300 text-sm">{feature}</span>
                    </div>
                  ))}
                  
                  {plan.limitations.map((limitation, limitIndex) => (
                    <div key={limitIndex} className="flex items-start space-x-3 opacity-60">
                      <X className="w-5 h-5 text-error mt-0.5 flex-shrink-0" />
                      <span className="text-dark-400 text-sm">{limitation}</span>
                    </div>
                  ))}
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    if (isCurrentPlan) {
                      onCancel?.()
                    } else if (planKey === 'ENTERPRISE') {
                      // Contact sales
                      window.open('mailto:sales@yourcompany.com?subject=Enterprise Plan Inquiry')
                    } else {
                      onUpgrade?.(planKey)
                    }
                  }}
                  className={`w-full py-3 px-6 rounded-lg font-medium transition-all duration-200 ${
                    isCurrentPlan
                      ? 'bg-success/20 text-success border border-success/50'
                      : plan.popular
                      ? 'btn-primary'
                      : 'btn-secondary'
                  }`}
                >
                  {isCurrentPlan ? 'Current Plan' : 
                   planKey === 'ENTERPRISE' ? 'Contact Sales' : 
                   `Upgrade to ${plan.name}`}
                </motion.button>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* FAQ Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="card"
      >
        <h2 className="text-2xl font-bold text-dark-200 mb-6 text-center">
          Frequently Asked Questions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-dark-200 mb-2">Can I change plans anytime?</h3>
            <p className="text-dark-400">Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately.</p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-dark-200 mb-2">What happens if I exceed my quota?</h3>
            <p className="text-dark-400">You'll receive a 429 status code and can upgrade your plan to continue making requests.</p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-dark-200 mb-2">Do you offer refunds?</h3>
            <p className="text-dark-400">We offer a 30-day money-back guarantee for all paid plans.</p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-dark-200 mb-2">Can I cancel anytime?</h3>
            <p className="text-dark-400">Yes, you can cancel your subscription at any time. Your plan remains active until the end of the billing period.</p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default BillingPlan
