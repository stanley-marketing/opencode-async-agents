# OpenCode-Slack Security Implementation

## Overview

This document describes the comprehensive security implementation for the OpenCode-Slack system, including authentication, authorization, rate limiting, input validation, and security headers.

## 🔐 Authentication System

### JWT Token Authentication
- **Implementation**: `src/security/auth.py`
- **Features**:
  - HS256 algorithm with configurable secret key
  - 24-hour token expiry (configurable)
  - Token refresh capability
  - Session management with activity tracking
  - Secure password hashing with salt

### API Key Authentication
- **Alternative authentication method** for service-to-service communication
- **Features**:
  - Prefixed keys (`ocs_`) for easy identification
  - Configurable permissions per key
  - Optional expiration dates
  - Usage tracking and audit logs
  - Easy revocation

### Default Credentials
- **Username**: `admin`
- **Password**: `opencode-admin-2024`
- **⚠️ IMPORTANT**: Change default password in production!

## 🛡️ Authorization System

### Permission-Based Access Control
- **Granular permissions** for different operations:
  - `read` - Basic read access
  - `employees:read/write/delete` - Employee management
  - `tasks:read/write` - Task operations
  - `files:read/write` - File management
  - `chat:read/admin` - Chat system control
  - `monitoring:read` - Monitoring access
  - `admin` - Full administrative access

### Role-Based Access
- **Admin role**: Full access to all endpoints
- **User role**: Limited access based on permissions
- **Custom roles**: Can be created with specific permission sets

## ⏱️ Rate Limiting

### Implementation
- **File**: `src/security/rate_limiter.py`
- **Algorithm**: Sliding window with thread-safe implementation
- **Granularity**: Per-endpoint and per-user limits

### Rate Limits (requests per minute)
- **Unauthenticated users**:
  - Global: 1000
  - Authentication: 10
  - Other endpoints: Category-specific limits
- **Authenticated users** (higher limits):
  - Global: 2000
  - Authentication: 20
  - Employee operations: 120
  - Task operations: 60
  - File operations: 200

### Features
- Automatic cleanup of old request records
- Rate limit headers in responses
- 429 status code with retry-after information
- Different limits for different endpoint categories

## 🔍 Input Validation & Security

### Security Middleware
- **File**: `src/security/middleware.py`
- **Features**:
  - Pattern-based threat detection
  - XSS prevention
  - SQL injection detection
  - Path traversal protection
  - Command injection prevention

### Validation Patterns
- Script tags and JavaScript injection
- SQL injection attempts
- File system access attempts
- Command execution attempts
- Template injection

### IP-Based Access Control
- **IP blocking**: Block specific IP addresses
- **IP whitelisting**: Allow only specific IPs (optional)
- **Automatic threat response**: Can auto-block IPs with repeated violations

## 🔒 Security Headers

### Implemented Headers
- **X-Content-Type-Options**: `nosniff`
- **X-Frame-Options**: `DENY`
- **X-XSS-Protection**: `1; mode=block`
- **Strict-Transport-Security**: `max-age=31536000; includeSubDomains`
- **Content-Security-Policy**: Restrictive policy
- **Referrer-Policy**: `strict-origin-when-cross-origin`
- **Permissions-Policy**: Disable unnecessary browser features

### CORS Configuration
- **Production mode**: Restrictive CORS with specific domain whitelist
- **Development mode**: More permissive for testing
- **Credentials**: Allowed for authenticated requests

## 🔐 Data Encryption

### Encryption Manager
- **File**: `src/security/encryption.py`
- **Algorithm**: Fernet (AES 128 in CBC mode)
- **Key derivation**: PBKDF2 with SHA-256
- **Features**:
  - Encrypt/decrypt arbitrary data structures
  - Secure token generation
  - Field-level encryption for sensitive data

### Use Cases
- Sensitive configuration data
- API keys and tokens
- Personal information
- Audit logs

## 🚀 Secure Server Implementation

### HTTPS Support
- **Self-signed certificates** for development
- **Production**: Use proper SSL certificates
- **Port**: Default 8443 for HTTPS

### Security Middleware Stack
1. **IP filtering** (if configured)
2. **Rate limiting** per endpoint
3. **Input validation** and threat detection
4. **Authentication** verification
5. **Authorization** checks
6. **Security headers** addition

## 📊 Security Monitoring

### Audit Logging
- All requests logged with:
  - Timestamp and IP address
  - Authentication information
  - Request details and response codes
  - Security threats detected
  - Response times

### Security Statistics
- **Endpoint**: `GET /security/stats`
- **Metrics**:
  - Authentication statistics
  - Rate limiting statistics
  - Threat detection counts
  - Active sessions and API keys

### Real-time Monitoring
- Failed authentication attempts
- Rate limit violations
- Security threat detections
- Suspicious IP activity

## 🔧 Configuration

### Environment Variables
```bash
# Authentication
JWT_SECRET_KEY=your-secret-key-here
TOKEN_EXPIRY_HOURS=24

# Security
OPENCODE_SAFE_MODE=false
ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8

# Server
HOST=localhost
PORT=8443
```

### Security Configuration
```python
# In your application
from src.security.auth import auth_manager
from src.security.rate_limiter import rate_limiter
from src.security.middleware import security_middleware

# Configure rate limits
rate_limiter.default_limits["auth"] = 5  # Stricter auth limits

# Configure IP restrictions
security_middleware.set_allowed_ips(["192.168.1.100", "10.0.0.50"])

# Create additional users
auth_manager.create_user("developer", "dev-password", ["user"], ["read", "tasks:write"])
```

## 🧪 Testing

### Comprehensive Security Tests
- **File**: `test_security_comprehensive.py`
- **Coverage**:
  - Authentication and authorization
  - Rate limiting effectiveness
  - Input validation and XSS prevention
  - Security headers presence
  - Error handling security

### Quick API Tests
- **File**: `test_secure_api.py`
- **Features**:
  - Basic functionality verification
  - Authentication flow testing
  - API key creation and usage
  - Rate limiting validation

### Running Tests
```bash
# Install dependencies
pip install -r requirements.txt

# Start secure server
python src/secure_server.py

# Run comprehensive tests
python test_security_comprehensive.py --url https://localhost:8443

# Run quick tests
python test_secure_api.py --url https://localhost:8443
```

## 🚨 Security Best Practices

### Production Deployment
1. **Change default credentials** immediately
2. **Use proper SSL certificates** (not self-signed)
3. **Configure IP whitelisting** if possible
4. **Set strong JWT secret key**
5. **Enable audit logging**
6. **Monitor security statistics**
7. **Regular security updates**

### API Usage
1. **Use HTTPS only** in production
2. **Store tokens securely** (not in localStorage)
3. **Implement token refresh** in clients
4. **Use API keys** for service-to-service communication
5. **Respect rate limits**
6. **Validate all inputs** on client side too

### Monitoring
1. **Set up alerts** for security events
2. **Monitor rate limit violations**
3. **Track failed authentication attempts**
4. **Review audit logs regularly**
5. **Monitor for unusual patterns**

## 🔄 Migration from Unsecured Version

### Step-by-Step Migration
1. **Install security dependencies**:
   ```bash
   pip install PyJWT cryptography pyopenssl
   ```

2. **Update imports** in your code:
   ```python
   from src.security.auth import require_auth
   from src.security.rate_limiter import rate_limit
   from src.security.middleware import security_headers, validate_request
   ```

3. **Add authentication decorators** to protected endpoints:
   ```python
   @app.route('/employees', methods=['GET'])
   @require_auth(permission="employees:read")
   @rate_limit()
   @security_headers()
   def list_employees():
       # Your existing code
   ```

4. **Update client code** to include authentication:
   ```python
   headers = {"Authorization": f"Bearer {token}"}
   response = requests.get("/employees", headers=headers)
   ```

5. **Test thoroughly** with the provided test suites

## 📚 API Reference

### Authentication Endpoints

#### POST /auth/login
Authenticate user and receive JWT token.
```json
{
  "username": "admin",
  "password": "opencode-admin-2024"
}
```

#### POST /auth/refresh
Refresh JWT token (requires valid token).

#### POST /auth/api-keys
Create new API key (admin only).
```json
{
  "name": "service-key",
  "permissions": ["read", "employees:read"],
  "expires_days": 30
}
```

#### GET /auth/api-keys
List all API keys (admin only).

#### DELETE /auth/api-keys/{key}
Revoke API key (admin only).

### Security Management Endpoints

#### GET /security/stats
Get security statistics (admin only).

#### POST /security/blocked-ips
Block IP address (admin only).
```json
{
  "ip": "192.168.1.100"
}
```

#### DELETE /security/blocked-ips/{ip}
Unblock IP address (admin only).

## 🆘 Troubleshooting

### Common Issues

1. **"Authentication required" errors**
   - Ensure you're sending the Authorization header
   - Check token expiry
   - Verify token format: `Bearer <token>`

2. **Rate limit exceeded**
   - Implement exponential backoff
   - Check rate limit headers in response
   - Consider using API keys for higher limits

3. **SSL certificate errors**
   - Use `verify=False` for self-signed certificates in testing
   - Install proper certificates for production

4. **Permission denied errors**
   - Check user permissions
   - Verify endpoint permission requirements
   - Ensure user has necessary roles

### Debug Mode
Set environment variable for additional logging:
```bash
export OPENCODE_DEBUG=true
```

## 🔮 Future Enhancements

### Planned Features
- **OAuth 2.0 integration** for third-party authentication
- **Multi-factor authentication** (MFA) support
- **Advanced threat detection** with machine learning
- **Audit log export** and analysis tools
- **Role-based UI** with different access levels
- **API versioning** with security policies per version

### Security Roadmap
- **Penetration testing** integration
- **Vulnerability scanning** automation
- **Security compliance** reporting (SOC 2, ISO 27001)
- **Advanced encryption** for data at rest
- **Zero-trust architecture** implementation

---

For questions or security concerns, please contact the development team or create an issue in the repository.