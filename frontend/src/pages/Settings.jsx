import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Settings as SettingsIcon, 
  Bell, 
  Moon, 
  Sun,
  Globe,
  Palette,
  Save,
  RefreshCw
} from 'lucide-react'
import toast from 'react-hot-toast'

const AppSettings = () => {
  const [settings, setSettings] = useState({
    theme: 'dark',
    language: 'en',
    notifications: {
      email: true,
      push: false,
      sms: false
    },
    api: {
      timeout: 30000,
      retries: 3
    },
    ui: {
      compactMode: false,
      showAnimations: true,
      sidebarCollapsed: false
    }
  })

  const [isSaving, setIsSaving] = useState(false)

  const handleSettingChange = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }))
  }

  const handleThemeChange = (theme) => {
    setSettings(prev => ({ ...prev, theme }))
    toast.success(`Theme changed to ${theme} mode 🎨`)
  }

  const handleLanguageChange = (language) => {
    setSettings(prev => ({ ...prev, language }))
    toast.success(`Language changed to ${language} 🌍`)
  }

  const handleSaveSettings = async () => {
    setIsSaving(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    setIsSaving(false)
    toast.success('Settings saved successfully! 💾')
  }

  const handleResetSettings = () => {
    setSettings({
      theme: 'dark',
      language: 'en',
      notifications: {
        email: true,
        push: false,
        sms: false
      },
      api: {
        timeout: 30000,
        retries: 3
      },
      ui: {
        compactMode: false,
        showAnimations: true,
        sidebarCollapsed: false
      }
    })
    toast.success('Settings reset to defaults 🔄')
  }

  return (
    <div className="min-h-screen bg-dark">
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold gradient-text mb-2">
              Application Settings
            </h1>
            <p className="text-dark-400">
              Customize your application preferences and behavior
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Appearance Settings */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="card"
            >
              <div className="flex items-center mb-6">
                <Palette className="w-5 h-5 text-accent-50 mr-2" />
                <h2 className="text-xl font-semibold text-dark-200">
                  Appearance
                </h2>
              </div>
              
              <div className="space-y-6">
                {/* Theme */}
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-3">
                    Theme
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => handleThemeChange('light')}
                      className={`p-4 rounded-lg border-2 transition-all duration-300 ${
                        settings.theme === 'light'
                          ? 'border-accent-50 bg-accent-50/10 text-accent-50'
                          : 'border-dark-200/30 text-dark-400 hover:border-dark-200/50'
                      }`}
                    >
                      <Sun className="w-6 h-6 mx-auto mb-2" />
                      <p className="text-sm font-medium">Light</p>
                    </button>
                    
                    <button
                      onClick={() => handleThemeChange('dark')}
                      className={`p-4 rounded-lg border-2 transition-all duration-300 ${
                        settings.theme === 'dark'
                          ? 'border-accent-50 bg-accent-50/10 text-accent-50'
                          : 'border-dark-200/30 text-dark-400 hover:border-dark-200/50'
                      }`}
                    >
                      <Moon className="w-6 h-6 mx-auto mb-2" />
                      <p className="text-sm font-medium">Dark</p>
                    </button>
                  </div>
                </div>

                {/* Language */}
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-3">
                    Language
                  </label>
                  <select
                    value={settings.language}
                    onChange={(e) => handleLanguageChange(e.target.value)}
                    className="w-full bg-dark-50/50 border border-dark-200/30 rounded-lg px-4 py-3 text-dark-200 focus:outline-none focus:ring-2 focus:ring-accent-50/50 focus:border-accent-50 transition-all duration-300"
                  >
                    <option value="en">English</option>
                    <option value="es">Español</option>
                    <option value="fr">Français</option>
                    <option value="de">Deutsch</option>
                    <option value="zh">中文</option>
                    <option value="ja">日本語</option>
                  </select>
                </div>
              </div>
            </motion.div>

            {/* Notification Settings */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="card"
            >
              <div className="flex items-center mb-6">
                <Bell className="w-5 h-5 text-accent-50 mr-2" />
                <h2 className="text-xl font-semibold text-dark-200">
                  Notifications
                </h2>
              </div>
              
              <div className="space-y-4">
                <label className="flex items-center justify-between p-3 glass-morphism rounded-lg cursor-pointer hover:bg-dark-100/30 transition-colors">
                  <span className="text-sm font-medium text-dark-200">
                    Email Notifications
                  </span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.email}
                    onChange={(e) => handleSettingChange('notifications', 'email', e.target.checked)}
                    className="w-5 h-5 text-accent-50 rounded focus:ring-2 focus:ring-accent-50/50"
                  />
                </label>
                
                <label className="flex items-center justify-between p-3 glass-morphism rounded-lg cursor-pointer hover:bg-dark-100/30 transition-colors">
                  <span className="text-sm font-medium text-dark-200">
                    Push Notifications
                  </span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.push}
                    onChange={(e) => handleSettingChange('notifications', 'push', e.target.checked)}
                    className="w-5 h-5 text-accent-50 rounded focus:ring-2 focus:ring-accent-50/50"
                  />
                </label>
                
                <label className="flex items-center justify-between p-3 glass-morphism rounded-lg cursor-pointer hover:bg-dark-100/30 transition-colors">
                  <span className="text-sm font-medium text-dark-200">
                    SMS Notifications
                  </span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.sms}
                    onChange={(e) => handleSettingChange('notifications', 'sms', e.target.checked)}
                    className="w-5 h-5 text-accent-50 rounded focus:ring-2 focus:ring-accent-50/50"
                  />
                </label>
              </div>
            </motion.div>

            {/* API Settings */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="card"
            >
              <div className="flex items-center mb-6">
                <Globe className="w-5 h-5 text-accent-50 mr-2" />
                <h2 className="text-xl font-semibold text-dark-200">
                  API Configuration
                </h2>
              </div>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Request Timeout (ms)
                  </label>
                  <input
                    type="number"
                    value={settings.api.timeout}
                    onChange={(e) => handleSettingChange('api', 'timeout', parseInt(e.target.value))}
                    className="w-full bg-dark-50/50 border border-dark-200/30 rounded-lg px-4 py-3 text-dark-200 focus:outline-none focus:ring-2 focus:ring-accent-50/50 focus:border-accent-50 transition-all duration-300"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Max Retries
                  </label>
                  <input
                    type="number"
                    value={settings.api.retries}
                    onChange={(e) => handleSettingChange('api', 'retries', parseInt(e.target.value))}
                    className="w-full bg-dark-50/50 border border-dark-200/30 rounded-lg px-4 py-3 text-dark-200 focus:outline-none focus:ring-2 focus:ring-accent-50/50 focus:border-accent-50 transition-all duration-300"
                  />
                </div>
              </div>
            </motion.div>

            {/* UI Settings */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="card"
            >
              <div className="flex items-center mb-6">
                <Settings className="w-5 h-5 text-accent-50 mr-2" />
                <h2 className="text-xl font-semibold text-dark-200">
                  User Interface
                </h2>
              </div>
              
              <div className="space-y-4">
                <label className="flex items-center justify-between p-3 glass-morphism rounded-lg cursor-pointer hover:bg-dark-100/30 transition-colors">
                  <span className="text-sm font-medium text-dark-200">
                    Compact Mode
                  </span>
                  <input
                    type="checkbox"
                    checked={settings.ui.compactMode}
                    onChange={(e) => handleSettingChange('ui', 'compactMode', e.target.checked)}
                    className="w-5 h-5 text-accent-50 rounded focus:ring-2 focus:ring-accent-50/50"
                  />
                </label>
                
                <label className="flex items-center justify-between p-3 glass-morphism rounded-lg cursor-pointer hover:bg-dark-100/30 transition-colors">
                  <span className="text-sm font-medium text-dark-200">
                    Show Animations
                  </span>
                  <input
                    type="checkbox"
                    checked={settings.ui.showAnimations}
                    onChange={(e) => handleSettingChange('ui', 'showAnimations', e.target.checked)}
                    className="w-5 h-5 text-accent-50 rounded focus:ring-2 focus:ring-accent-50/50"
                  />
                </label>
              </div>
            </motion.div>
          </div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="mt-8 flex justify-end space-x-4"
          >
            <button
              onClick={handleResetSettings}
              className="px-6 py-3 bg-dark-100 text-dark-400 rounded-lg hover:bg-dark-200 transition-colors flex items-center"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Reset to Defaults
            </button>
            
            <button
              onClick={handleSaveSettings}
              disabled={isSaving}
              className="btn-primary flex items-center"
            >
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

export default AppSettings
