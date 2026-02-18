import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  Check, 
  X, 
  Zap, 
  Shield, 
  Crown, 
  Star,
  CreditCard,
  Lock,
  Users,
  Database,
  Globe,
  Headphones,
  Mail,
  Phone,
  MessageSquare,
  ArrowRight,
  TrendingUp,
  Award,
  Clock,
  CheckCircle,
  ArrowLeft,
  Sparkles,
  Flame
} from 'lucide-react'
import toast from 'react-hot-toast'

const PLANS = [
  {
    name: 'Starter',
    price: 0,
    period: 'month',
    description: 'Perfect for individuals and small projects',
    icon: Star,
    color: 'from-gray-600 to-gray-700',
    features: [
      '1,000 API requests/month',
      '60 requests/minute',
      'Basic authentication',
      'Community support',
      'Standard endpoints',
      'SSL encryption'
    ],
    limitations: [
      'No advanced analytics',
      'No priority support',
      'Limited rate limits'
    ],
    popular: false,
    buttonText: 'Get Started'
  },
  {
    name: 'Professional',
    price: 29,
    period: 'month',
    description: 'Ideal for growing businesses and teams',
    icon: Zap,
    color: 'from-blue-600 to-purple-600',
    features: [
      '10,000 API requests/month',
      '300 requests/minute',
      'Advanced authentication',
      'Priority support',
      'All premium endpoints',
      'Advanced analytics',
      'Custom rate limits',
      'API key management',
      'Webhook support',
      'SSO integration'
    ],
    limitations: [],
    popular: true,
    buttonText: 'Upgrade Now',
    badge: 'MOST POPULAR'
  },
  {
    name: 'Enterprise',
    price: 99,
    period: 'month',
    description: 'For large organizations with custom needs',
    icon: Crown,
    color: 'from-purple-600 to-pink-600',
    features: [
      'Unlimited API requests',
      'Custom rate limits',
      'Dedicated support',
      'All features included',
      'Custom endpoints',
      'Advanced security',
      'SLA guarantee',
      'White-label options',
      'On-premise deployment',
      'Custom integrations',
      'Priority queue access'
    ],
    limitations: [],
    popular: false,
    buttonText: 'Contact Sales',
    enterprise: true
  }
]

const FAQ_ITEMS = [
  {
    question: 'Can I change plans anytime?',
    answer: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately and we\'ll prorate any differences.'
  },
  {
    question: 'What happens if I exceed my API limits?',
    answer: 'You\'ll receive a 429 status code and can upgrade your plan to continue making requests. We also send email notifications when you\'re approaching your limits.'
  },
  {
    question: 'Do you offer refunds?',
    answer: 'We offer a 30-day money-back guarantee for all paid plans. If you\'re not satisfied, contact our support team for a full refund.'
  },
  {
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit cards, debit cards, and PayPal. Enterprise customers can also pay via invoice or wire transfer.'
  },
  {
    question: 'Is my data secure?',
    answer: 'Absolutely! We use bank-level 256-bit SSL encryption, comply with GDPR and SOC 2, and perform regular security audits.'
  }
]

const UpgradePlans = () => {
  const [selectedPlan, setSelectedPlan] = useState('Professional')
  const [billingCycle, setBillingCycle] = useState('monthly')
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const navigate = useNavigate()

  const handlePlanSelect = (plan) => {
    console.log('Plan clicked:', plan) // Debug log
    if (plan.enterprise) {
      navigate('/contact-sales')
    } else {
      console.log('Setting payment modal for:', plan.name) // Debug log
      setSelectedPlan(plan.name)
      setShowPaymentModal(true)
    }
  }

  const calculateAnnualSavings = (monthlyPrice) => {
    const annualPrice = monthlyPrice * 12
    const discountedPrice = annualPrice * 0.8 // 20% discount for annual
    return annualPrice - discountedPrice
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
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-dark via-dark-50 to-dark pt-20 pb-16">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900/10 to-purple-900/10" />
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
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
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6">
              <Zap className="w-4 h-4 text-purple-400 mr-2" />
              <span className="text-sm font-medium text-purple-300">Limited Time: 20% off Annual Plans</span>
            </div>
            
            <h1 className="text-5xl font-bold text-white mb-6">
              Choose Your Perfect Plan
            </h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto mb-8">
              Scale your API usage with flexible pricing designed for businesses of all sizes. 
              Start free and upgrade as you grow.
            </p>

            {/* Billing Toggle */}
            <div className="flex items-center justify-center space-x-4 mb-12">
              <span className={`text-lg ${billingCycle === 'monthly' ? 'text-white' : 'text-gray-400'}`}>
                Monthly
              </span>
              <button
                onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'annual' : 'monthly')}
                className="relative w-14 h-8 bg-gray-700 rounded-full transition-colors"
              >
                <div 
                  className={`absolute top-1 w-6 h-6 bg-white rounded-full transition-transform ${
                    billingCycle === 'annual' ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className={`text-lg ${billingCycle === 'annual' ? 'text-white' : 'text-gray-400'}`}>
                Annual
                <span className="ml-2 text-sm text-green-400 font-medium">
                  (Save 20%)
                </span>
              </span>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {PLANS.map((plan, index) => {
            const Icon = plan.icon
            const displayPrice = billingCycle === 'annual' && plan.price > 0 
              ? (plan.price * 12 * 0.8) / 12 
              : plan.price
            
            return (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className={`relative ${
                  plan.popular ? 'md:scale-105' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-10">
                    <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-1 rounded-full text-sm font-bold">
                      {plan.badge}
                    </div>
                  </div>
                )}
                
                <div className={`card h-full ${
                  plan.popular ? 'border-2 border-purple-500/50' : ''
                } ${selectedPlan === plan.name ? 'ring-2 ring-blue-500' : ''}`}>
                  <div className="text-center mb-8">
                    <div className={`w-16 h-16 bg-gradient-to-r ${plan.color} rounded-xl flex items-center justify-center mx-auto mb-4`}>
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    
                    <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                    <p className="text-gray-400 mb-6">{plan.description}</p>
                    
                    <div className="mb-6">
                      <div className="flex items-baseline justify-center">
                        <span className="text-4xl font-bold text-white">${displayPrice}</span>
                        <span className="text-gray-400 ml-2">/{plan.period}</span>
                      </div>
                      {billingCycle === 'annual' && plan.price > 0 && (
                        <div className="flex items-center justify-center mt-2">
                          <span className="text-sm text-gray-400 line-through">
                            ${plan.price * 12}/year
                          </span>
                          <span className="ml-2 text-sm text-green-400 font-medium">
                            Save ${calculateAnnualSavings(plan.price)}/year
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4 mb-8">
                    {plan.features.map((feature, featureIndex) => (
                      <div key={featureIndex} className="flex items-start space-x-3">
                        <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-300 text-sm">{feature}</span>
                      </div>
                    ))}
                    
                    {plan.limitations.map((limitation, limitIndex) => (
                      <div key={limitIndex} className="flex items-start space-x-3 opacity-60">
                        <X className="w-5 h-5 text-gray-500 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-500 text-sm">{limitation}</span>
                      </div>
                    ))}
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handlePlanSelect(plan)}
                    className={`w-full py-3 px-6 rounded-lg font-medium transition-all duration-200 ${
                      plan.enterprise
                        ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:opacity-90'
                        : plan.popular
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:opacity-90'
                        : 'bg-dark-100 text-white hover:bg-dark-200'
                    }`}
                  >
                    {plan.buttonText}
                  </motion.button>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* Features Comparison */}
      <div className="bg-dark-50 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Compare All Features
            </h2>
            <p className="text-xl text-gray-300">
              Everything you need to make the right decision for your business
            </p>
          </motion.div>

          <div className="overflow-x-auto">
            <table className="w-full card">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-4 px-6 text-gray-400 font-medium">Feature</th>
                  <th className="text-center py-4 px-6 text-gray-400 font-medium">Starter</th>
                  <th className="text-center py-4 px-6 text-gray-400 font-medium">
                    Professional
                    <span className="ml-2 text-xs bg-blue-600 text-white px-2 py-1 rounded-full">Popular</span>
                  </th>
                  <th className="text-center py-4 px-6 text-gray-400 font-medium">Enterprise</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { feature: 'API Requests', starter: '1,000/month', professional: '10,000/month', enterprise: 'Unlimited' },
                  { feature: 'Rate Limit', starter: '60/minute', professional: '300/minute', enterprise: 'Custom' },
                  { feature: 'Support', starter: 'Community', professional: 'Priority', enterprise: 'Dedicated' },
                  { feature: 'Analytics', starter: 'Basic', professional: 'Advanced', enterprise: 'Custom' },
                  { feature: 'API Keys', starter: '2', professional: '10', enterprise: 'Unlimited' },
                  { feature: 'Webhooks', starter: 'No', professional: 'Yes', enterprise: 'Custom' },
                  { feature: 'SSO', starter: 'No', professional: 'Yes', enterprise: 'Custom' },
                  { feature: 'SLA', starter: 'No', professional: '99.9%', enterprise: '99.99%' },
                ].map((row, index) => (
                  <tr key={index} className="border-b border-gray-700 hover:bg-gray-800/50">
                    <td className="py-4 px-6 text-gray-300 font-medium">{row.feature}</td>
                    <td className="py-4 px-6 text-center text-gray-300">{row.starter}</td>
                    <td className="py-4 px-6 text-center">
                      <span className="text-blue-400 font-medium">{row.professional}</span>
                    </td>
                    <td className="py-4 px-6 text-center">
                      <span className="text-purple-400 font-medium">{row.enterprise}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-xl text-gray-300">
              Got questions? We've got answers.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {FAQ_ITEMS.map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
                className="card"
              >
                <h3 className="text-lg font-semibold text-white mb-3">
                  {item.question}
                </h3>
                <p className="text-gray-300">
                  {item.answer}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Get Started?
            </h2>
            <p className="text-xl text-blue-100 mb-8">
              Join thousands of companies trusting our API platform
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
              <button className="px-8 py-3 bg-white text-blue-600 rounded-lg font-medium hover:bg-gray-100 transition-colors">
                Start Free Trial
              </button>
              <button className="px-8 py-3 bg-transparent border-2 border-white text-white rounded-lg font-medium hover:bg-white hover:text-blue-600 transition-all">
                Contact Sales
              </button>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Payment Modal */}
      {showPaymentModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowPaymentModal(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.2 }}
            className="card max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            {console.log('Payment modal is showing!')} {/* Debug log */}
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-white">Complete Your Purchase</h3>
              <button
                onClick={() => setShowPaymentModal(false)}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400">Selected Plan</span>
                <span className="text-white font-medium">{selectedPlan}</span>
              </div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400">Billing Cycle</span>
                <span className="text-white font-medium capitalize">{billingCycle}</span>
              </div>
              <div className="flex items-center justify-between mb-6">
                <span className="text-lg font-semibold text-white">Total</span>
                <span className="text-2xl font-bold text-white">
                  ${PLANS.find(p => p.name === selectedPlan)?.price || 0}/{billingCycle === 'annual' ? 'year' : 'month'}
                </span>
              </div>
            </div>

            {/* Stripe Payment Form */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
                <input
                  type="email"
                  className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  placeholder="john@example.com"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Card Information</label>
                <div className="space-y-3">
                  <input
                    type="text"
                    className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    placeholder="Card Number"
                  />
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      placeholder="MM/YY"
                    />
                    <input
                      type="text"
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      placeholder="CVC"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 mb-6">
                <Lock className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-400">
                  Your payment information is encrypted and secure
                </span>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  toast.success('Payment processed successfully!')
                  setShowPaymentModal(false)
                }}
                className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                <div className="flex items-center justify-center space-x-2">
                  <CreditCard className="w-5 h-5" />
                  <span>Complete Purchase</span>
                </div>
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}

export default UpgradePlans
