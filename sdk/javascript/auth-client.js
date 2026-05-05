/**
 * SaaS Auth API - JavaScript/TypeScript SDK
 * 
 * Comprehensive JavaScript SDK for authentication and user management.
 * Works in both browser and Node.js environments.
 */

class AuthClient {
    constructor(config) {
        this.baseURL = config.baseURL || 'http://localhost:8000';
        this.apiKey = config.apiKey;
        this.timeout = config.timeout || 30000;
        this.storage = config.storage || localStorage;
        this.accessToken = null;
        this.refreshToken = null;
        
        // Load tokens from storage
        this._loadTokens();
    }
    
    /**
     * User Authentication
     */
    
    async login(email, password) {
        const response = await this._request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        this.accessToken = response.access_token;
        this.refreshToken = response.refresh_token;
        this._saveTokens();
        
        return response;
    }
    
    async register(username, email, password) {
        const response = await this._request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
        
        return response;
    }
    
    async logout() {
        await this._request('/auth/logout', {
            method: 'POST',
            requiresAuth: true
        });
        
        this.accessToken = null;
        this.refreshToken = null;
        this._clearTokens();
    }
    
    async refreshToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }
        
        const response = await this._request('/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refresh_token: this.refreshToken })
        });
        
        this.accessToken = response.access_token;
        this.refreshToken = response.refresh_token;
        this._saveTokens();
        
        return response;
    }
    
    /**
     * Password Management
     */
    
    async requestPasswordReset(email) {
        return await this._request('/auth/password-reset/request', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    }
    
    async resetPassword(token, newPassword) {
        return await this._request('/auth/password-reset/confirm', {
            method: 'POST',
            body: JSON.stringify({ token, new_password: newPassword })
        });
    }
    
    async changePassword(currentPassword, newPassword) {
        return await this._request('/auth/change-password', {
            method: 'POST',
            requiresAuth: true,
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
        });
    }
    
    /**
     * User Profile
     */
    
    async getProfile() {
        return await this._request('/users/me', {
            method: 'GET',
            requiresAuth: true
        });
    }
    
    async updateProfile(data) {
        return await this._request('/users/me', {
            method: 'PUT',
            requiresAuth: true,
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Two-Factor Authentication
     */
    
    async enable2FA() {
        const response = await this._request('/auth/2fa/enable', {
            method: 'POST',
            requiresAuth: true
        });
        
        return response;
    }
    
    async verify2FA(code) {
        return await this._request('/auth/2fa/verify', {
            method: 'POST',
            requiresAuth: true,
            body: JSON.stringify({ code })
        });
    }
    
    async disable2FA(code) {
        return await this._request('/auth/2fa/disable', {
            method: 'POST',
            requiresAuth: true,
            body: JSON.stringify({ code })
        });
    }
    
    /**
     * OAuth2/OIDC
     */
    
    getOAuthURL(provider, redirectURI) {
        return `${this.baseURL}/auth/oauth/${provider}?redirect_uri=${encodeURIComponent(redirectURI)}`;
    }
    
    async exchangeOAuthCode(provider, code, redirectURI) {
        return await this._request(`/auth/oauth/${provider}/callback`, {
            method: 'POST',
            body: JSON.stringify({ code, redirect_uri: redirectURI })
        });
    }
    
    /**
     * API Keys
     */
    
    async createAPIKey(name, scopes = []) {
        return await this._request('/api-keys', {
            method: 'POST',
            requiresAuth: true,
            body: JSON.stringify({ name, scopes })
        });
    }
    
    async listAPIKeys() {
        return await this._request('/api-keys', {
            method: 'GET',
            requiresAuth: true
        });
    }
    
    async deleteAPIKey(keyId) {
        return await this._request(`/api-keys/${keyId}`, {
            method: 'DELETE',
            requiresAuth: true
        });
    }
    
    /**
     * Webhooks
     */
    
    async createWebhook(url, events, secret) {
        return await this._request('/webhooks', {
            method: 'POST',
            requiresAuth: true,
            body: JSON.stringify({ url, events, secret })
        });
    }
    
    async listWebhooks() {
        return await this._request('/webhooks', {
            method: 'GET',
            requiresAuth: true
        });
    }
    
    async deleteWebhook(webhookId) {
        return await this._request(`/webhooks/${webhookId}`, {
            method: 'DELETE',
            requiresAuth: true
        });
    }
    
    /**
     * Feature Flags
     */
    
    async checkFeatureFlag(flagName, userId = null) {
        return await this._request(`/feature-flags/${flagName}/evaluate`, {
            method: 'POST',
            requiresAuth: true,
            body: JSON.stringify({ user_id: userId })
        });
    }
    
    async listFeatureFlags() {
        return await this._request('/feature-flags', {
            method: 'GET',
            requiresAuth: true
        });
    }
    
    /**
     * WebSocket (Real-time notifications)
     */
    
    connectWebSocket(onMessage, onError) {
        const wsURL = this.baseURL.replace('http', 'ws') + '/ws';
        const ws = new WebSocket(wsURL);
        
        ws.onopen = () => {
            if (this.accessToken) {
                ws.send(JSON.stringify({ type: 'auth', token: this.accessToken }));
            }
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (onMessage) onMessage(data);
        };
        
        ws.onerror = (error) => {
            if (onError) onError(error);
        };
        
        return ws;
    }
    
    /**
     * Private Methods
     */
    
    async _request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        if (options.requiresAuth && this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }
        
        const config = {
            method: options.method || 'GET',
            headers,
            body: options.body
        };
        
        try {
            const response = await fetch(url, config);
            
            if (response.status === 401 && this.refreshToken) {
                await this.refreshToken();
                headers['Authorization'] = `Bearer ${this.accessToken}`;
                return await fetch(url, config);
            }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }
            
            return await response.json();
        } catch (error) {
            throw error;
        }
    }
    
    _saveTokens() {
        this.storage.setItem('access_token', this.accessToken);
        this.storage.setItem('refresh_token', this.refreshToken);
    }
    
    _loadTokens() {
        this.accessToken = this.storage.getItem('access_token');
        this.refreshToken = this.storage.getItem('refresh_token');
    }
    
    _clearTokens() {
        this.storage.removeItem('access_token');
        this.storage.removeItem('refresh_token');
    }
    
    isAuthenticated() {
        return !!this.accessToken;
    }
}

// Node.js export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthClient;
}

// Browser export
if (typeof window !== 'undefined') {
    window.AuthClient = AuthClient;
}
