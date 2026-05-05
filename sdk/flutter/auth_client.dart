/// SaaS Auth API - Flutter SDK
///
/// Comprehensive Flutter SDK for authentication and user management.
///
/// Features:
/// - User authentication (login, register, logout)
/// - Token management (access, refresh)
/// - OAuth2/OIDC integration
/// - Two-factor authentication
/// - Password reset
/// - Profile management
/// - Real-time notifications via WebSocket
/// - Type-safe with Dart
/// - Secure storage for tokens
/// - State management integration

library auth_client;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

// ==================== Models ====================

/// User model
class User {
  final int id;
  final String username;
  final String email;
  final String role;
  final String subscriptionPlan;
  final bool isActive;
  final bool emailVerified;
  final DateTime createdAt;
  final DateTime? updatedAt;

  User({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.subscriptionPlan,
    required this.isActive,
    required this.emailVerified,
    required this.createdAt,
    this.updatedAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      username: json['username'],
      email: json['email'],
      role: json['role'],
      subscriptionPlan: json['subscription_plan'] ?? 'free',
      isActive: json['is_active'] ?? false,
      emailVerified: json['email_verified'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
    );

    Map<String, dynamic> toJson() {
      return {
        'id': id,
        'username': username,
        'email': email,
        'role': role,
        'subscription_plan': subscriptionPlan,
        'is_active': isActive,
        'email_verified': emailVerified,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
      };
    }
  }

  /// Auth tokens model
  class AuthTokens {
    final String accessToken;
    final String refreshToken;
    final String tokenType;
    final int expiresIn;

    AuthTokens({
      required this.accessToken,
      required this.refreshToken,
      required this.tokenType,
      required this.expiresIn,
    });

    factory AuthTokens.fromJson(Map<String, dynamic> json) {
      return AuthTokens(
        accessToken: json['access_token'],
        refreshToken: json['refresh_token'],
        tokenType: json['token_type'] ?? 'bearer',
        expiresIn: json['expires_in'] ?? 1800,
      );
    }

    Map<String, dynamic> toJson() {
      return {
        'access_token': accessToken,
        'refresh_token': refreshToken,
        'token_type': tokenType,
        'expires_in': expiresIn,
      };
    }
  }

  /// Login credentials
  class LoginCredentials {
    final String username;
    final String password;

    LoginCredentials({
      required this.username,
      required this.password,
    });

    Map<String, dynamic> toJson() {
      return {
        'username': username,
        'password': password,
      };
    }
  }

  /// Register data
  class RegisterData {
    final String username;
    final String email;
    final String password;

    RegisterData({
      required this.username,
      required this.email,
      required this.password,
    });

    Map<String, dynamic> toJson() {
      return {
        'username': username,
        'email': email,
        'password': password,
      };
    }
  }

  /// Two-factor setup data
  class TwoFactorSetup {
    final String secret;
    final String qrCode;
    final List<String> backupCodes;
    final String uri;

    TwoFactorSetup({
      required this.secret,
      required this.qrCode,
      required this.backupCodes,
      required this.uri,
    });

    factory TwoFactorSetup.fromJson(Map<String, dynamic> json) {
      return TwoFactorSetup(
        secret: json['secret'],
        qrCode: json['qr_code'],
        backupCodes: List<String>.from(json['backup_codes']),
        uri: json['uri'],
      );
    }
  }

  /// API response wrapper
  class ApiResponse<T> {
    final T? data;
    final String? message;
    final String? error;

    ApiResponse({
      this.data,
    this.message,
    this.error,
  });

    factory ApiResponse.fromJson(
      Map<String, dynamic> json,
      T Function(Map<String, dynamic>) fromJsonT,
      ) {
      return ApiResponse<T>(
        data: json['data'] != null ? fromJsonT(json['data']) : null,
        message: json['message'],
        error: json['error'],
      );
    }
  }

  /// Paginated response
  class PaginatedResponse<T> {
    final List<T> items;
    final int total;
    final int page;
    final int pages;

    PaginatedResponse({
      required this.items,
      required this.total,
    required this.page,
    required this.pages,
  });

    factory PaginatedResponse.fromJson(
      Map<String, dynamic> json,
      T Function(Map<String, dynamic>) fromJsonT,
      ) {
    return PaginatedResponse<T>(
      items: (json['items'] as List)
          .map((item) => fromJsonT(item))
          .toList(),
      total: json['total'],
      page: json['page'],
      pages: json['pages'],
    );
  }
}

// ==================== Configuration ====================

/// Auth client configuration
class AuthClientConfig {
  final String baseURL;
  final Duration timeout;
  final bool enableLogging;
  final bool enableWebSocket;
  final String? wsURL;

  AuthClientConfig({
    required this.baseURL,
    this.timeout = const Duration(seconds: 30),
    this.enableLogging = false,
    this.enableWebSocket = true,
    this.wsURL,
  });
}

// ==================== Exceptions ====================

/// Auth error
class AuthError implements Exception {
  final String message;
  final int? statusCode;
  final String? code;

  AuthError({
    required this.message,
    this.statusCode,
    this.code,
  });

  @override
  String toString() => 'AuthError: $message (code: $code, status: $statusCode)';
}

// ==================== Main Client ====================

/// Main Auth Client
class AuthClient {
  final AuthClientConfig config;
  final http.Client _httpClient;
  AuthTokens? _tokens;
  User? _currentUser;
  WebSocketChannel? _wsChannel;
  StreamController<dynamic>? _messageController;
  Future<AuthTokens>? _refreshPromise;

  // Storage keys
  static const String _accessTokenKey = 'auth_access_token';
  static const String _refreshTokenKey = 'auth_refresh_token';
  static const String _userKey = 'auth_user';

  // Event streams
  final StreamController<User> _authEventController = StreamController<User>.broadcast();
  final StreamController<String> _wsEventController = StreamController<String>.broadcast();

  AuthClient({
    required this.config,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  /// Get auth event stream
  Stream<User> get authEvents => _authEventController.stream;

  /// Get WebSocket event stream
  Stream<String> get wsEvents => _wsEventController.stream;

  /// Get current user
  User? get currentUser => _currentUser;

  /// Check if authenticated
  bool get isAuthenticated => _tokens?.accessToken != null;

  /// Get access token
  String? get accessToken => _tokens?.accessToken;

  /// Initialize the client
  Future<void> initialize() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final accessToken = prefs.getString(_accessTokenKey);
      final refreshToken = prefs.getString(_refreshTokenKey);
      final userStr = prefs.getString(_userKey);

      if (accessToken != null && refreshToken != null) {
        _tokens = AuthTokens(
          accessToken: accessToken,
          refreshToken: refreshToken,
          tokenType: 'bearer',
          expiresIn: 1800,
        );
      }

      if (userStr != null) {
        _currentUser = User.fromJson(jsonDecode(userStr));
      }

      if (config.enableWebSocket && _tokens != null) {
        await connectWebSocket();
      }
    } catch (e) {
      _log('Initialization error: $e');
    }
  }

  /// Login with credentials
  Future<User> login(LoginCredentials credentials) async {
    final response = await _request<AuthTokens>(
      '/auth/login',
      method: 'POST',
      body: jsonEncode(credentials.toJson()),
    );

    await _setTokens(response);
    final user = await fetchProfile();
    await _saveUser(user);

    if (config.enableWebSocket) {
      await connectWebSocket();
    }

    _authEventController.add(user);
    return user;
  }

  /// Register new user
  Future<User> register(RegisterData data) async {
    final response = await _request<AuthTokens>(
      '/auth/register',
      method: 'POST',
      body: jsonEncode(data.toJson()),
    );

    await _setTokens(response);
    final user = await fetchProfile();
    await _saveUser(user);

    if (config.enableWebSocket) {
      await connectWebSocket();
    }

    _authEventController.add(user);
    return user;
  }

  /// Logout
  Future<void> logout() async {
    try {
      await _request('/auth/logout', method: 'POST');
    } catch (e) {
      _log('Logout request failed: $e');
    }

    await _clearTokens();
    await disconnectWebSocket();
    _authEventController.add(User(
      id: 0,
      username: '',
      email: '',
      role: '',
      subscriptionPlan: 'free',
      isActive: false,
      emailVerified: false,
      createdAt: DateTime.now(),
    ));
  }

  /// Refresh tokens
  Future<AuthTokens> _refreshTokens() async {
    if (_refreshPromise != null) {
      return _refreshPromise!;
    }

    _refreshPromise = (() async {
      try {
        final response = await _request<AuthTokens>(
          '/auth/refresh',
          method: 'POST',
          body: jsonEncode({
            'refresh_token': _tokens?.refreshToken,
          }),
        );

        await _setTokens(response);
        return response;
      } finally {
        _refreshPromise = null;
      }
    })();

    return _refreshPromise!;
  }

  /// Fetch user profile
  Future<User> fetchProfile() async {
    return _request<User>('/users/profile');
  }

  /// Update user profile
  Future<User> updateProfile(Map<String, dynamic> data) async {
    final user = await _request<User>(
      '/users/profile',
      method: 'PUT',
      body: jsonEncode(data),
    );

    await _saveUser(user);
    return user;
  }

  /// Change password
  Future<void> changePassword(String oldPassword, String newPassword) async {
    await _request(
      '/auth/change-password',
      method: 'POST',
      body: jsonEncode({
        'old_password': oldPassword,
        'new_password': newPassword,
      }),
    );
  }

  /// Request password reset
  Future<void> requestPasswordReset(String email) async {
    await _request(
      '/auth/password-reset/request',
      method: 'POST',
      body: jsonEncode({'email': email}),
    );
  }

  /// Reset password with token
  Future<void> resetPassword(String token, String newPassword) async {
    await _request(
      '/auth/password-reset/reset',
      method: 'POST',
      body: jsonEncode({
        'token': token,
        'new_password': newPassword,
      }),
    );
  }

  /// Setup two-factor authentication
  Future<TwoFactorSetup> setupTwoFactor() async {
    return _request<TwoFactorSetup>(
      '/auth/2fa/setup',
      method: 'POST',
    );
  }

  /// Verify two-factor authentication
  Future<void> verifyTwoFactor(String code) async {
    await _request(
      '/auth/2fa/verify',
      method: 'POST',
      body: jsonEncode({'code': code}),
    );
  }

  /// Disable two-factor authentication
  Future<void> disableTwoFactor(String password) async {
    await _request(
      '/auth/2fa/disable',
      method: 'POST',
      body: jsonEncode({'password': password}),
    );
  }

  /// Get OAuth URL
  Future<String> getOAuthUrl(String provider) async {
    final response = await _request<Map<String, dynamic>>(
      '/auth/oauth/$provider/url',
    );
    return response['url'];
  }

  /// Handle OAuth callback
  Future<User> handleOAuthCallback(String provider, String code) async {
    final response = await _request<AuthTokens>(
      '/auth/oauth/$provider/callback',
      method: 'POST',
      body: jsonEncode({'code': code}),
    );

    await _setTokens(response);
    final user = await fetchProfile();
    await _saveUser(user);

    if (config.enableWebSocket) {
      await connectWebSocket();
    }

    return user;
  }

  /// Connect WebSocket
  Future<void> connectWebSocket() async {
    if (_wsChannel != null) {
      return;
    }

    final wsURL = config.wsURL ?? config.baseURL.replace('http', 'ws');
    final token = _tokens?.accessToken;

    if (token == null) {
      return;
    }

    try {
      _wsChannel = WebSocketChannel.connect(
        Uri.parse('$wsURL/ws?token=$token'),
      );

      _messageController = StreamController<dynamic>.broadcast();

      _wsChannel!.stream.listen(
        (message) {
          _log('WebSocket message: $message');
          _wsEventController.add(message.toString());
          _messageController?.add(message);
        },
        onError: (error) {
          _log('WebSocket error: $error');
          _wsEventController.add('error:$error');
        },
        onDone: () {
          _log('WebSocket closed');
          _wsChannel = null;
          _wsEventController.add('disconnected');
          
          // Attempt reconnection
          Future.delayed(const Duration(seconds: 5), () {
            if (_tokens != null) {
              connectWebSocket();
            }
          });
        },
      );

      _log('WebSocket connected');
      _wsEventController.add('connected');
    } catch (e) {
      _log('WebSocket connection error: $e');
    }
  }

  /// Disconnect WebSocket
  Future<void> disconnectWebSocket() async {
    await _wsChannel?.sink.close();
    _wsChannel = null;
    await _messageController?.close();
    _messageController = null;
  }

  /// Send WebSocket message
  void sendWebSocketMessage(String type, dynamic data) {
    if (_wsChannel != null) {
      _wsChannel!.sink.add(jsonEncode({'type': type, 'data': data}));
    }
  }

  /// Get WebSocket message stream
  Stream<dynamic>? get wsMessages => _messageController?.stream;

  /// Make authenticated API request
  Future<T> _request<T>(
    String endpoint, {
    String method = 'GET',
    String? body,
    Map<String, String>? headers,
  }) async {
    final url = Uri.parse('${config.baseURL}$endpoint');
    final requestHeaders = <String, String>{
      'Content-Type': 'application/json',
      ...?headers,
    };

    if (_tokens?.accessToken != null) {
      requestHeaders['Authorization'] = 'Bearer ${_tokens!.accessToken}';
    }

    http.Response response;

    try {
      // Check connectivity
      final connectivityResult = await Connectivity().checkConnectivity();
      if (connectivityResult == ConnectivityResult.none) {
        throw AuthError(
          message: 'No internet connection',
          code: 'NO_CONNECTION',
        );
      }

      response = await _httpClient
          .send(http.Request(method, url))
          .timeout(config.timeout)
          .then((req) async {
        if (body != null) {
          req.body = body;
        }
        req.headers.addAll(requestHeaders);
        return await _httpClient.send(req);
      });

      // Handle 401 - try refresh
      if (response.statusCode == 401 && _tokens?.refreshToken != null) {
        await _refreshTokens();
        requestHeaders['Authorization'] = 'Bearer ${_tokens!.accessToken}';
        response = await _httpClient
            .send(http.Request(method, url))
            .timeout(config.timeout)
            .then((req) async {
          if (body != null) {
            req.body = body;
          }
          req.headers.addAll(requestHeaders);
          return await _httpClient.send(req);
        });
      }

      if (response.statusCode >= 400) {
        final errorData = jsonDecode(response.body);
        throw AuthError(
          message: errorData['detail'] ?? 'Request failed',
          statusCode: response.statusCode,
          code: errorData['code'],
        );
      }

      final responseData = jsonDecode(response.body);

      if (T == User) {
        return User.fromJson(responseData) as T;
      } else if (T == AuthTokens) {
        return AuthTokens.fromJson(responseData) as T;
      } else if (T == TwoFactorSetup) {
        return TwoFactorSetup.fromJson(responseData) as T;
      } else {
        return responseData as T;
      }
    } on SocketException catch (e) {
      throw AuthError(
        message: 'Network error: ${e.message}',
        code: 'NETWORK_ERROR',
      );
    } on TimeoutException catch (e) {
      throw AuthError(
        message: 'Request timeout',
        code: 'TIMEOUT',
      );
    } on AuthError {
      rethrow;
    } catch (e) {
      throw AuthError(
        message: e.toString(),
        code: 'UNKNOWN_ERROR',
      );
    }
  }

  /// Set and store tokens
  Future<void> _setTokens(AuthTokens tokens) async {
    _tokens = tokens;
    final prefs = await SharedPreferences.getInstance();
    await Future.wait([
      prefs.setString(_accessTokenKey, tokens.accessToken),
      prefs.setString(_refreshTokenKey, tokens.refreshToken),
    ]);
  }

  /// Clear stored tokens
  Future<void> _clearTokens() async {
    _tokens = null;
    _currentUser = null;
    final prefs = await SharedPreferences.getInstance();
    await Future.wait([
      prefs.remove(_accessTokenKey),
      prefs.remove(_refreshTokenKey),
      prefs.remove(_userKey),
    ]);
  }

  /// Save user data
  Future<void> _saveUser(User user) async {
    _currentUser = user;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, jsonEncode(user.toJson()));
  }

  /// Logging helper
  void _log(String message) {
    if (config.enableLogging) {
      debugPrint('[AuthClient] $message');
    }
  }

  /// Dispose resources
  void dispose() {
    disconnectWebSocket();
    _authEventController.close();
    _wsEventController.close();
    _httpClient.close();
  }
}

// ==================== Provider ====================

/// Auth state provider for Flutter
import 'package:flutter/material.dart';

class AuthProvider extends ChangeNotifier {
  final AuthClient client;
  User? _user;
  bool _loading = true;
  AuthError? _error;

  AuthProvider({required this.client}) {
    _initialize();
  }

  User? get user => _user;
  bool get loading => _loading;
  AuthError? get error => _error;
  bool get isAuthenticated => client.isAuthenticated;

  Future<void> _initialize() async {
    await client.initialize();
    _user = client.currentUser;
    _loading = false;
    notifyListeners();

    client.authEvents.listen((user) {
      _user = user;
      notifyListeners();
    });
  }

  Future<User> login(LoginCredentials credentials) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final user = await client.login(credentials);
      _user = user;
      _loading = false;
      notifyListeners();
      return user;
    } on AuthError catch (e) {
      _error = e;
      _loading = false;
      notifyListeners();
      rethrow;
    }
  }

  Future<User> register(RegisterData data) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final user = await client.register(data);
      _user = user;
      _loading = false;
      notifyListeners();
      return user;
    } on AuthError catch (e) {
      _error = e;
      _loading = false;
      notifyListeners();
      rethrow;
    }
  }

  Future<void> logout() async {
    _loading = true;
    notifyListeners();

    try {
      await client.logout();
      _user = null;
      _loading = false;
      notifyListeners();
    } on AuthError catch (e) {
      _error = e;
      _loading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    client.dispose();
    super.dispose();
  }
}
