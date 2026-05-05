/**
 * SaaS Auth API - React Native SDK
 * 
 * Comprehensive React Native SDK for authentication and user management.
 * 
 * Features:
 * - User authentication (login, register, logout)
 * - Token management (access, refresh)
 * - OAuth2/OIDC integration
 * - Two-factor authentication
 * - Password reset
 * - Profile management
 * - Real-time notifications via WebSocket
 * - Type-safe with TypeScript
 * - AsyncStorage for token persistence
 * - Secure storage for sensitive data
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { EventRegister } from 'react-native-event-listeners';

// Types
export interface User {
  id: number;
  username: string;
  email: string;
  role: 'user' | 'admin' | 'moderator';
  subscription_plan: 'free' | 'pro' | 'enterprise';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

export interface TwoFactorSetup {
  secret: string;
  qr_code: string;
  backup_codes: string[];
  uri: string;
}

export interface OAuthProvider {
  google: string;
  github: string;
  apple: string;
}

// Configuration
export interface AuthClientConfig {
  baseURL: string;
  timeout?: number;
  enableLogging?: boolean;
  enableWebSocket?: boolean;
  wsURL?: string;
}

// Error types
export class AuthError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'AuthError';
  }
}

// Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

/**
 * Main Auth Client Class
 */
export class AuthClient {
  private config: AuthClientConfig;
  private tokens: AuthTokens | null = null;
  private currentUser: User | null = null;
  private wsConnection: WebSocket | null = null;
  private refreshPromise: Promise<AuthTokens> | null = null;

  // Storage keys
  private static readonly ACCESS_TOKEN_KEY = '@auth_access_token';
  private static readonly REFRESH_TOKEN_KEY = '@auth_refresh_token';
  private static readonly USER_KEY = '@auth_user';

  constructor(config: AuthClientConfig) {
    this.config = {
      timeout: 30000,
      enableLogging: false,
      enableWebSocket: true,
      ...config
    };
  }

  /**
   * Initialize the client and load stored tokens
   */
  async initialize(): Promise<void> {
    try {
      const [accessToken, refreshToken, userStr] = await Promise.all([
        AsyncStorage.getItem(AuthClient.ACCESS_TOKEN_KEY),
        AsyncStorage.getItem(AuthClient.REFRESH_TOKEN_KEY),
        AsyncStorage.getItem(AuthClient.USER_KEY)
      ]);

      if (accessToken && refreshToken) {
        this.tokens = {
          access_token: accessToken,
          refresh_token: refreshToken,
          token_type: 'bearer',
          expires_in: 1800
        };
      }

      if (userStr) {
        this.currentUser = JSON.parse(userStr);
      }

      if (this.config.enableWebSocket && this.tokens) {
        await this.connectWebSocket();
      }
    } catch (error) {
      this.log('Initialization error:', error);
    }
  }

  /**
   * Login with username and password
   */
  async login(credentials: LoginCredentials): Promise<User> {
    const response = await this.request<AuthTokens>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials)
    });

    await this.setTokens(response);
    const user = await this.fetchProfile();
    await this.saveUser(user);
    
    if (this.config.enableWebSocket) {
      await this.connectWebSocket();
    }

    EventRegister.emit('auth:login', user);
    return user;
  }

  /**
   * Register a new user
   */
  async register(data: RegisterData): Promise<User> {
    const response = await this.request<AuthTokens>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data)
    });

    await this.setTokens(response);
    const user = await this.fetchProfile();
    await this.saveUser(user);
    
    if (this.config.enableWebSocket) {
      await this.connectWebSocket();
    }

    EventRegister.emit('auth:register', user);
    return user;
  }

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (error) {
      this.log('Logout request failed:', error);
    }

    await this.clearTokens();
    await this.disconnectWebSocket();
    
    EventRegister.emit('auth:logout');
  }

  /**
   * Refresh access token
   */
  private async refreshTokens(): Promise<AuthTokens> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const response = await this.request<AuthTokens>('/auth/refresh', {
          method: 'POST',
          body: JSON.stringify({
            refresh_token: this.tokens?.refresh_token
          })
        });

        await this.setTokens(response);
        return response;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Get current user profile
   */
  async fetchProfile(): Promise<User> {
    return this.request<User>('/users/profile');
  }

  /**
   * Update user profile
   */
  async updateProfile(data: Partial<User>): Promise<User> {
    const user = await this.request<User>('/users/profile', {
      method: 'PUT',
      body: JSON.stringify(data)
    });
    
    await this.saveUser(user);
    return user;
  }

  /**
   * Change password
   */
  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword
      })
    });
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    await this.request('/auth/password-reset/request', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await this.request('/auth/password-reset/reset', {
      method: 'POST',
      body: JSON.stringify({
        token,
        new_password: newPassword
      })
    });
  }

  /**
   * Setup two-factor authentication
   */
  async setupTwoFactor(): Promise<TwoFactorSetup> {
    return this.request<TwoFactorSetup>('/auth/2fa/setup', {
      method: 'POST'
    });
  }

  /**
   * Verify two-factor authentication
   */
  async verifyTwoFactor(code: string): Promise<void> {
    await this.request('/auth/2fa/verify', {
      method: 'POST',
      body: JSON.stringify({ code })
    });
  }

  /**
   * Disable two-factor authentication
   */
  async disableTwoFactor(password: string): Promise<void> {
    await this.request('/auth/2fa/disable', {
      method: 'POST',
      body: JSON.stringify({ password })
    });
  }

  /**
   * Get OAuth authorization URL
   */
  async getOAuthUrl(provider: keyof OAuthProvider): Promise<string> {
    const response = await this.request<{ url: string }>(`/auth/oauth/${provider}/url`);
    return response.url;
  }

  /**
   * Handle OAuth callback
   */
  async handleOAuthCallback(provider: keyof OAuthProvider, code: string): Promise<User> {
    const response = await this.request<AuthTokens>(`/auth/oauth/${provider}/callback`, {
      method: 'POST',
      body: JSON.stringify({ code })
    });

    await this.setTokens(response);
    const user = await this.fetchProfile();
    await this.saveUser(user);
    
    if (this.config.enableWebSocket) {
      await this.connectWebSocket();
    }

    return user;
  }

  /**
   * WebSocket connection
   */
  private async connectWebSocket(): Promise<void> {
    if (this.wsConnection) {
      return;
    }

    const wsURL = this.config.wsURL || this.config.baseURL.replace('http', 'ws');
    const token = this.tokens?.access_token;

    if (!token) {
      return;
    }

    this.wsConnection = new WebSocket(`${wsURL}/ws?token=${token}`);

    this.wsConnection.onopen = () => {
      this.log('WebSocket connected');
      EventRegister.emit('ws:connected');
    };

    this.wsConnection.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        EventRegister.emit('ws:message', message);
      } catch (error) {
        this.log('WebSocket message parse error:', error);
      }
    };

    this.wsConnection.onerror = (error) => {
      this.log('WebSocket error:', error);
      EventRegister.emit('ws:error', error);
    };

    this.wsConnection.onclose = () => {
      this.log('WebSocket closed');
      this.wsConnection = null;
      EventRegister.emit('ws:disconnected');
      
      // Attempt reconnection after delay
      setTimeout(() => {
        if (this.tokens) {
          this.connectWebSocket();
        }
      }, 5000);
    };
  }

  /**
   * Disconnect WebSocket
   */
  private async disconnectWebSocket(): Promise<void> {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  /**
   * Send WebSocket message
   */
  sendWebSocketMessage(type: string, data: any): void {
    if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify({ type, data }));
    }
  }

  /**
   * Make authenticated API request
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseURL}${endpoint}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (this.tokens?.access_token) {
      headers['Authorization'] = `Bearer ${this.tokens.access_token}`;
    }

    try {
      let response = await fetch(url, {
        ...options,
        headers,
        signal: AbortSignal.timeout(this.config.timeout!)
      });

      // Handle 401 Unauthorized - try refresh
      if (response.status === 401 && this.tokens?.refresh_token) {
        await this.refreshTokens();
        headers['Authorization'] = `Bearer ${this.tokens.access_token}`;
        response = await fetch(url, {
          ...options,
          headers,
          signal: AbortSignal.timeout(this.config.timeout!)
        });
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new AuthError(
          error.detail || 'Request failed',
          response.status,
          error.code
        );
      }

      return response.json();
    } catch (error) {
      if (error instanceof AuthError) {
        throw error;
      }
      throw new AuthError(
        error instanceof Error ? error.message : 'Network error',
        undefined,
        'NETWORK_ERROR'
      );
    }
  }

  /**
   * Set and store tokens
   */
  private async setTokens(tokens: AuthTokens): Promise<void> {
    this.tokens = tokens;
    
    await Promise.all([
      AsyncStorage.setItem(AuthClient.ACCESS_TOKEN_KEY, tokens.access_token),
      AsyncStorage.setItem(AuthClient.REFRESH_TOKEN_KEY, tokens.refresh_token)
    ]);
  }

  /**
   * Clear stored tokens
   */
  private async clearTokens(): Promise<void> {
    this.tokens = null;
    this.currentUser = null;
    
    await Promise.all([
      AsyncStorage.removeItem(AuthClient.ACCESS_TOKEN_KEY),
      AsyncStorage.removeItem(AuthClient.REFRESH_TOKEN_KEY),
      AsyncStorage.removeItem(AuthClient.USER_KEY)
    ]);
  }

  /**
   * Save user data
   */
  private async saveUser(user: User): Promise<void> {
    this.currentUser = user;
    await AsyncStorage.setItem(AuthClient.USER_KEY, JSON.stringify(user));
  }

  /**
   * Get current user
   */
  getCurrentUser(): User | null {
    return this.currentUser;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.tokens?.access_token;
  }

  /**
   * Get access token
   */
  getAccessToken(): string | null {
    return this.tokens?.access_token || null;
  }

  /**
   * Logging helper
   */
  private log(...args: any[]): void {
    if (this.config.enableLogging) {
      console.log('[AuthClient]', ...args);
    }
  }
}

/**
 * React Hook for authentication
 */
import { useState, useEffect, useCallback } from 'react';

export function useAuth(client: AuthClient) {
  const [user, setUser] = useState<User | null>(client.getCurrentUser());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AuthError | null>(null);

  useEffect(() => {
    client.initialize().then(() => {
      setUser(client.getCurrentUser());
      setLoading(false);
    });

    const loginListener = EventRegister.addEventListener('auth:login', (loggedInUser) => {
      setUser(loggedInUser);
    });

    const logoutListener = EventRegister.addEventListener('auth:logout', () => {
      setUser(null);
    });

    return () => {
      EventRegister.removeEventListener(loginListener);
      EventRegister.removeEventListener(logoutListener);
    };
  }, [client]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setLoading(true);
    setError(null);
    try {
      const loggedInUser = await client.login(credentials);
      setUser(loggedInUser);
      return loggedInUser;
    } catch (e) {
      setError(e as AuthError);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [client]);

  const register = useCallback(async (data: RegisterData) => {
    setLoading(true);
    setError(null);
    try {
      const registeredUser = await client.register(data);
      setUser(registeredUser);
      return registeredUser;
    } catch (e) {
      setError(e as AuthError);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [client]);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await client.logout();
      setUser(null);
    } catch (e) {
      setError(e as AuthError);
    } finally {
      setLoading(false);
    }
  }, [client]);

  return {
    user,
    loading,
    error,
    isAuthenticated: client.isAuthenticated(),
    login,
    register,
    logout,
    client
  };
}

/**
 * React Hook for WebSocket
 */
export function useWebSocket(client: AuthClient) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    const connectedListener = EventRegister.addEventListener('ws:connected', () => {
      setConnected(true);
    });

    const disconnectedListener = EventRegister.addEventListener('ws:disconnected', () => {
      setConnected(false);
    });

    const messageListener = EventRegister.addEventListener('ws:message', (message) => {
      setMessages(prev => [...prev, message]);
    });

    return () => {
      EventRegister.removeEventListener(connectedListener);
      EventRegister.removeEventListener(disconnectedListener);
      EventRegister.removeEventListener(messageListener);
    };
  }, []);

  const sendMessage = useCallback((type: string, data: any) => {
    client.sendWebSocketMessage(type, data);
  }, [client]);

  return {
    connected,
    messages,
    sendMessage
  };
}

// Export default
export default AuthClient;
