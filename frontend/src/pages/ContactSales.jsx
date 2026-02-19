import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  Mail, 
  Phone, 
  MessageSquare, 
  Send, 
  Users, 
  Building, 
  Globe,
  Clock,
  CheckCircle,
  ArrowRight,
  Headphones,
  Award,
  Shield,
  Zap,
  TrendingUp,
  Star,
  ArrowLeft,
  Sparkles,
  Flame
} from 'lucide-react'
import toast from 'react-hot-toast'

const ContactSales = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    employees: '',
    industry: '',
    currentStack: '',
    requirements: '',
    timeline: '',
    budget: ''
  })

  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    toast.success('Your inquiry has been submitted! Our sales team will contact you within 24 hours.')
    setFormData({
      name: '',
      email: '',
      company: '',
      phone: '',
      employees: '',
      industry: '',
      currentStack: '',
      requirements: '',
      timeline: '',
      budget: ''
    })
    setIsSubmitting(false)
  }

  const teamMembers = [
    {
      name: 'Sarah Johnson',
      role: 'Enterprise Sales Manager',
      email: 'sarah@company.com',
      phone: '+1 (555) 123-4567',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=sarah',
      expertise: 'Large-scale API implementations, custom integrations'
    },
    {
      name: 'Michael Chen',
      role: 'Solutions Architect',
      email: 'michael@company.com',
      phone: '+1 (555) 234-5678',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=michael',
      expertise: 'Technical consulting, API design, architecture'
    },
    {
      name: 'Emily Rodriguez',
      role: 'Customer Success Lead',
      email: 'emily@company.com',
      phone: '+1 (555) 345-6789',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=emily',
      expertise: 'Onboarding, support, training, success stories'
    }
  ]

  const testimonials = [
    {
      name: 'Alex Thompson',
      company: 'TechCorp Inc.',
      role: 'CTO',
      content: 'The enterprise solution transformed our API infrastructure. The custom rate limits and dedicated support have been game-changers for our scaling needs.',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=alex',
      rating: 5
    },
    {
      name: 'Jessica Martinez',
      company: 'DataFlow Systems',
      role: 'VP Engineering',
      content: 'Outstanding service from day one. The implementation team went above and beyond to ensure our migration was seamless.',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=jessica',
      rating: 5
    },
    {
      name: 'David Kim',
      company: 'GlobalStart LLC',
      role: 'Founder',
      content: 'Best decision we made. The enterprise features and SLA guarantees give us the confidence to build our entire platform on their API.',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=david',
      rating: 5
    }
  ]

  return (
    <div className="min-h-screen bg-dark">
      <style>{`
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
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-900 via-purple-900 to-dark pt-20 pb-16">
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
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 mb-6">
              <CheckCircle className="w-4 h-4 text-green-400 mr-2" />
              <span className="text-sm font-medium text-green-300">Enterprise Sales Team Available</span>
            </div>
            
            <h1 className="text-5xl font-bold text-white mb-6">
              Let's Build Your Enterprise Solution
            </h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto mb-8">
              Get custom pricing, dedicated support, and enterprise-grade features tailored to your organization's needs. 
              Our sales team is ready to help you scale.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-6">
              <div className="flex items-center space-x-3">
                <Phone className="w-5 h-5 text-green-400" />
                <span className="text-white font-medium">+92 342 6386433</span>
              </div>
              <div className="flex items-center space-x-3">
                <Mail className="w-5 h-5 text-blue-400" />
                <span className="text-white font-medium">artasyaskar@gmail.com</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          {/* Contact Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="lg:col-span-2"
          >
            <div className="card">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white mb-2">Get a Custom Quote</h2>
                <p className="text-gray-400">
                  Tell us about your requirements and we'll create a tailored solution for your business.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Full Name *</label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      placeholder="John Doe"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Work Email *</label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      placeholder="john@company.com"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Company Name *</label>
                    <input
                      type="text"
                      name="company"
                      value={formData.company}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      placeholder="TechCorp Inc."
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Company Size</label>
                    <select
                      name="employees"
                      value={formData.employees}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="">Select company size</option>
                      <option value="1-10">1-10 employees</option>
                      <option value="11-50">11-50 employees</option>
                      <option value="51-200">51-200 employees</option>
                      <option value="201-1000">201-1000 employees</option>
                      <option value="1000+">1000+ employees</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Industry</label>
                    <select
                      name="industry"
                      value={formData.industry}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="">Select industry</option>
                      <option value="technology">Technology</option>
                      <option value="finance">Finance</option>
                      <option value="healthcare">Healthcare</option>
                      <option value="ecommerce">E-commerce</option>
                      <option value="education">Education</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Current Tech Stack</label>
                  <input
                    type="text"
                    name="currentStack"
                    value={formData.currentStack}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    placeholder="React, Node.js, AWS, etc."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Project Requirements</label>
                  <textarea
                    name="requirements"
                    value={formData.requirements}
                    onChange={handleInputChange}
                    rows={4}
                    required
                    className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    placeholder="Describe your API requirements, expected volume, and specific needs..."
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Implementation Timeline</label>
                    <select
                      name="timeline"
                      value={formData.timeline}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="">Select timeline</option>
                      <option value="immediate">Immediate (0-30 days)</option>
                      <option value="1-3months">1-3 months</option>
                      <option value="3-6months">3-6 months</option>
                      <option value="6+months">6+ months</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Estimated Budget</label>
                    <select
                      name="budget"
                      value={formData.budget}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 bg-dark-100 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="">Select budget range</option>
                      <option value="5k-10k">$5,000 - $10,000</option>
                      <option value="10k-25k">$10,000 - $25,000</option>
                      <option value="25k-50k">$25,000 - $50,000</option>
                      <option value="50k-100k">$50,000 - $100,000</option>
                      <option value="100k+">$100,000+</option>
                    </select>
                  </div>
                </div>

                <motion.button
                  type="submit"
                  disabled={isSubmitting}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center justify-center space-x-2">
                    {isSubmitting ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-5 h-5" />
                        <span>Submit Inquiry</span>
                      </>
                    )}
                  </div>
                </motion.button>
              </form>
            </div>
          </motion.div>

          {/* Team & Contact Info */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="space-y-8"
          >
            {/* Quick Contact */}
            <div className="card">
              <h3 className="text-xl font-semibold text-white mb-6">Get in Touch</h3>
              <div className="space-y-4">
                <div className="flex items-center space-x-3 p-3 glass-morphism rounded-lg">
                  <Phone className="w-5 h-5 text-green-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Sales Hotline</p>
                    <p className="text-gray-400">+92 342 6386433</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 glass-morphism rounded-lg">
                  <Mail className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Email Support</p>
                    <p className="text-gray-400">artasyaskar@gmail.com</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 glass-morphism rounded-lg">
                  <Headphones className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Live Chat</p>
                    <p className="text-gray-400">Available 24/7</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 glass-morphism rounded-lg">
                  <Clock className="w-5 h-5 text-yellow-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Response Time</p>
                    <p className="text-gray-400">Under 2 hours</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Meet the Team */}
            <div className="card">
              <h3 className="text-xl font-semibold text-white mb-6">Enterprise Sales Team</h3>
              <div className="space-y-4">
                {teamMembers.map((member, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.3 + index * 0.1 }}
                    className="flex items-center space-x-3 p-3 glass-morphism rounded-lg"
                  >
                    <img
                      src={member.avatar}
                      alt={member.name}
                      className="w-12 h-12 rounded-full"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{member.name}</p>
                      <p className="text-xs text-gray-400">{member.role}</p>
                      <p className="text-xs text-gray-500">{member.expertise}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Benefits Section */}
      <div className="bg-dark-50 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Why Choose Enterprise?
            </h2>
            <p className="text-xl text-gray-300">
              Enterprise features designed for scale, security, and reliability
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Shield,
                title: 'Advanced Security',
                description: 'Enterprise-grade security with SOC 2 compliance and custom authentication'
              },
              {
                icon: Zap,
                title: 'Unlimited Scale',
                description: 'Custom rate limits and unlimited API requests for your growth'
              },
              {
                icon: Users,
                title: 'Dedicated Support',
                description: '24/7 dedicated support team with 99.99% SLA guarantee'
              },
              {
                icon: Award,
                title: 'Custom Solutions',
                description: 'Tailored features and custom integrations for your specific needs'
              }
            ].map((benefit, index) => {
              const Icon = benefit.icon
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
                  className="card text-center"
                >
                  <div className={`w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-4`}>
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{benefit.title}</h3>
                  <p className="text-gray-400 text-sm">{benefit.description}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Testimonials */}
      <div className="py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Trusted by Leading Companies
            </h2>
            <p className="text-xl text-gray-300">
              See what our enterprise customers have to say about their experience
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.7 + index * 0.1 }}
                className="card"
              >
                <div className="flex items-center space-x-3 mb-4">
                  <img
                    src={testimonial.avatar}
                    alt={testimonial.name}
                    className="w-12 h-12 rounded-full"
                  />
                  <div>
                    <p className="text-sm font-medium text-white">{testimonial.name}</p>
                    <p className="text-xs text-gray-400">{testimonial.role} at {testimonial.company}</p>
                    <div className="flex items-center space-x-1">
                      {[...Array(testimonial.rating)].map((_, i) => (
                        <Star key={i} className="w-3 h-3 text-yellow-400 fill-current" />
                      ))}
                    </div>
                  </div>
                </div>
                <p className="text-gray-300 italic">"{testimonial.content}"</p>
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
            transition={{ duration: 0.5, delay: 0.8 }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Transform Your Business?
            </h2>
            <p className="text-xl text-blue-100 mb-8">
              Join thousands of enterprises that trust our platform for their critical API needs
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
              <button className="px-8 py-3 bg-white text-blue-600 rounded-lg font-medium hover:bg-gray-100 transition-colors">
                Schedule a Demo
              </button>
              <button className="px-8 py-3 bg-transparent border-2 border-white text-white rounded-lg font-medium hover:bg-white hover:text-blue-600 transition-all">
                <div className="flex items-center space-x-2">
                  <Phone className="w-4 h-4" />
                  <span>Call Sales Team</span>
                </div>
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

export default ContactSales
