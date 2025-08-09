"""
Comprehensive security tests for WebSocket communication.
Tests authentication, authorization, input validation, rate limiting, and attack prevention.
"""

import asyncio
import json
import pytest
import time
import websockets
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import secrets
import threading

# Import the security modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from security.websocket_security import WebSocketSecurityManager, SecurityViolation
from security.websocket_auth import WebSocketAuthManager, AuthResult
from security.message_validation import MessageValidator, ValidationResult
from security.audit_logger import SecurityAuditLogger, SecurityEventLevel

class TestWebSocketSecurityManager:
    """Test WebSocket security manager functionality"""
    
    @pytest.fixture
    def security_manager(self):
        """Create security manager for testing"""
        config = Mock()
        config.get.return_value = "test_value"
        config.get_int.return_value = 100
        return WebSocketSecurityManager(config)
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection"""
        websocket = Mock()
        websocket.remote_address = ('192.168.1.100', 12345)
        websocket.request_headers = {}
        websocket.recv = AsyncMock()
        websocket.send = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_successful_authentication(self, security_manager, mock_websocket):
        """Test successful WebSocket authentication"""
        # Mock auth data
        auth_data = {
            'type': 'auth',
            'method': 'jwt',
            'token': 'valid_jwt_token'
        }
        
        mock_websocket.recv.return_value = json.dumps(auth_data)
        
        # Mock auth manager response
        auth_result = AuthResult(
            success=True,
            user_id='test_user',
            role='user',
            permissions=['chat.send', 'chat.read'],
            session_token='session_123'
        )
        
        with patch.object(security_manager.auth_manager, 'authenticate', return_value=auth_result):
            connection_info = await security_manager.authenticate_connection(mock_websocket, '/ws')
            
            assert connection_info is not None
            assert connection_info['user_id'] == 'test_user'
            assert connection_info['role'] == 'user'
            assert 'session_token' in connection_info
            
            # Verify success message was sent
            mock_websocket.send.assert_called_once()
            sent_message = json.loads(mock_websocket.send.call_args[0][0])
            assert sent_message['type'] == 'auth_success'
    
    @pytest.mark.asyncio
    async def test_authentication_timeout(self, security_manager, mock_websocket):
        """Test authentication timeout handling"""
        # Mock timeout
        mock_websocket.recv.side_effect = asyncio.TimeoutError()
        
        connection_info = await security_manager.authenticate_connection(mock_websocket, '/ws')
        
        assert connection_info is None
        
        # Verify error message was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message['type'] == 'error'
        assert sent_message['data']['code'] == 'AUTH_TIMEOUT'
    
    @pytest.mark.asyncio
    async def test_invalid_json_authentication(self, security_manager, mock_websocket):
        """Test handling of invalid JSON in authentication"""
        mock_websocket.recv.return_value = "invalid json"
        
        connection_info = await security_manager.authenticate_connection(mock_websocket, '/ws')
        
        assert connection_info is None
        
        # Verify error message was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message['type'] == 'error'
        assert sent_message['data']['code'] == 'INVALID_JSON'
    
    @pytest.mark.asyncio
    async def test_rate_limiting_auth_attempts(self, security_manager, mock_websocket):
        """Test rate limiting of authentication attempts"""
        client_ip = '192.168.1.100'
        
        # Exceed auth rate limit
        for _ in range(10):  # More than the limit of 5
            security_manager._record_auth_attempt(client_ip)
        
        # Should be rate limited now
        assert not security_manager._check_auth_rate_limit(client_ip)
        
        mock_websocket.recv.return_value = json.dumps({'type': 'auth', 'method': 'jwt'})
        
        connection_info = await security_manager.authenticate_connection(mock_websocket, '/ws')
        
        assert connection_info is None
        
        # Verify rate limit error was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message['type'] == 'error'
        assert sent_message['data']['code'] == 'RATE_LIMITED'
    
    @pytest.mark.asyncio
    async def test_ip_blocking(self, security_manager, mock_websocket):
        """Test IP blocking functionality"""
        client_ip = '192.168.1.100'
        
        # Block the IP
        security_manager.blocked_ips[client_ip] = datetime.utcnow()
        
        connection_info = await security_manager.authenticate_connection(mock_websocket, '/ws')
        
        assert connection_info is None
        
        # Verify blocked IP error was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message['type'] == 'error'
        assert sent_message['data']['code'] == 'IP_BLOCKED'
    
    @pytest.mark.asyncio
    async def test_connection_limit_per_ip(self, security_manager, mock_websocket):
        """Test connection limit per IP"""
        client_ip = '192.168.1.100'
        
        # Fill up connection limit
        for i in range(security_manager.rate_limits['max_connections_per_ip']):
            security_manager.ip_connections[client_ip].add(f'conn_{i}')
        
        connection_info = await security_manager.authenticate_connection(mock_websocket, '/ws')
        
        assert connection_info is None
        
        # Verify connection limit error was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message['type'] == 'error'
        assert sent_message['data']['code'] == 'CONNECTION_LIMIT'
    
    @pytest.mark.asyncio
    async def test_message_validation_success(self, security_manager):
        """Test successful message validation"""
        connection_id = 'test_conn_123'
        
        # Setup connection
        security_manager.active_connections[connection_id] = {
            'user_id': 'test_user',
            'role': 'user',
            'permissions': ['chat.send'],
            'client_ip': '192.168.1.100',
            'websocket': Mock(),
            'last_activity': datetime.utcnow()
        }
        
        message = {
            'type': 'chat_message',
            'text': 'Hello, world!'
        }
        
        with patch.object(security_manager.message_validator, 'validate_message') as mock_validate:
            mock_validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
            
            with patch.object(security_manager.message_validator, 'sanitize_message') as mock_sanitize:
                mock_sanitize.return_value = message
                
                result = await security_manager.validate_message(connection_id, json.dumps(message))
                
                assert result is not None
                assert result['type'] == 'chat_message'
                assert result['text'] == 'Hello, world!'
    
    @pytest.mark.asyncio
    async def test_message_too_large(self, security_manager):
        """Test handling of oversized messages"""
        connection_id = 'test_conn_123'
        
        # Setup connection
        security_manager.active_connections[connection_id] = {
            'user_id': 'test_user',
            'role': 'user',
            'permissions': ['chat.send'],
            'client_ip': '192.168.1.100',
            'websocket': AsyncMock(),
            'last_activity': datetime.utcnow()
        }
        
        # Create oversized message
        large_message = 'x' * (security_manager.rate_limits['max_message_size'] + 1)
        
        result = await security_manager.validate_message(connection_id, large_message)
        
        assert result is None
        
        # Verify error was sent
        websocket = security_manager.active_connections[connection_id]['websocket']
        websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_rate_limiting(self, security_manager):
        """Test message rate limiting"""
        connection_id = 'test_conn_123'
        
        # Setup connection
        security_manager.active_connections[connection_id] = {
            'user_id': 'test_user',
            'role': 'user',
            'permissions': ['chat.send'],
            'client_ip': '192.168.1.100',
            'websocket': AsyncMock(),
            'last_activity': datetime.utcnow()
        }
        
        # Exceed message rate limit
        for _ in range(security_manager.rate_limits['messages_per_minute'] + 1):
            security_manager._record_message(connection_id)
        
        message = json.dumps({'type': 'chat_message', 'text': 'test'})
        result = await security_manager.validate_message(connection_id, message)
        
        assert result is None
        
        # Verify rate limit error was sent
        websocket = security_manager.active_connections[connection_id]['websocket']
        websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_csrf_protection(self, security_manager):
        """Test CSRF token protection"""
        connection_id = 'test_conn_123'
        
        # Setup connection
        security_manager.active_connections[connection_id] = {
            'user_id': 'test_user',
            'role': 'user',
            'permissions': ['tasks.create'],
            'client_ip': '192.168.1.100',
            'websocket': AsyncMock(),
            'last_activity': datetime.utcnow()
        }
        
        # Message requiring CSRF protection
        message = {
            'type': 'create_task',
            'title': 'Test Task'
            # Missing csrf_token
        }
        
        with patch.object(security_manager.message_validator, 'validate_message') as mock_validate:
            mock_validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
            
            result = await security_manager.validate_message(connection_id, json.dumps(message))
            
            assert result is None
            
            # Verify CSRF error was sent
            websocket = security_manager.active_connections[connection_id]['websocket']
            websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_permission_checking(self, security_manager):
        """Test permission checking for messages"""
        connection_id = 'test_conn_123'
        
        # Setup connection with limited permissions
        security_manager.active_connections[connection_id] = {
            'user_id': 'test_user',
            'role': 'user',
            'permissions': ['chat.send'],  # No task permissions
            'client_ip': '192.168.1.100',
            'websocket': AsyncMock(),
            'last_activity': datetime.utcnow()
        }
        
        # Message requiring task permissions
        message = {
            'type': 'create_task',
            'title': 'Test Task',
            'csrf_token': 'valid_token'
        }
        
        # Mock CSRF validation to pass
        security_manager.csrf_tokens[f"{connection_id}:valid_token"] = datetime.utcnow()
        
        with patch.object(security_manager.message_validator, 'validate_message') as mock_validate:
            mock_validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
            
            result = await security_manager.validate_message(connection_id, json.dumps(message))
            
            assert result is None
            
            # Verify permission denied error was sent
            websocket = security_manager.active_connections[connection_id]['websocket']
            websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_timeout(self, security_manager):
        """Test session timeout handling"""
        connection_id = 'test_conn_123'
        
        # Setup expired connection
        expired_time = datetime.utcnow() - timedelta(minutes=35)  # Older than 30 min timeout
        security_manager.active_connections[connection_id] = {
            'user_id': 'test_user',
            'role': 'user',
            'permissions': ['chat.send'],
            'client_ip': '192.168.1.100',
            'websocket': AsyncMock(),
            'last_activity': expired_time
        }
        
        # Check timeout
        is_expired = security_manager.check_session_timeout(connection_id)
        assert is_expired
        
        # Test cleanup of expired sessions
        await security_manager.cleanup_expired_sessions()
        
        # Connection should be removed
        assert connection_id not in security_manager.active_connections
    
    def test_security_stats(self, security_manager):
        """Test security statistics generation"""
        # Add some test data
        security_manager.active_connections['conn1'] = {'user_id': 'user1'}
        security_manager.active_connections['conn2'] = {'user_id': 'user2'}
        security_manager.ip_connections['192.168.1.100'] = {'conn1', 'conn2'}
        security_manager.blocked_ips['192.168.1.200'] = datetime.utcnow()
        
        stats = security_manager.get_security_stats()
        
        assert stats['active_connections'] == 2
        assert '192.168.1.100' in stats['connections_by_ip']
        assert stats['connections_by_ip']['192.168.1.100'] == 2
        assert stats['blocked_ips'] == 1
        assert 'rate_limits' in stats
        assert 'auth_manager_stats' in stats


class TestWebSocketAuthManager:
    """Test WebSocket authentication manager"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing"""
        config = Mock()
        config.get.return_value = "test_secret"
        return WebSocketAuthManager(config)
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_success(self, auth_manager):
        """Test successful JWT authentication"""
        auth_data = {
            'method': 'jwt',
            'token': 'valid_jwt_token'
        }
        
        # Mock JWT verification
        jwt_payload = {
            'username': 'test_user',
            'roles': ['user'],
            'permissions': ['chat.send', 'chat.read']
        }
        
        with patch.object(auth_manager.auth_manager, 'verify_jwt_token', return_value=jwt_payload):
            result = await auth_manager.authenticate(auth_data)
            
            assert result.success
            assert result.user_id == 'test_user'
            assert result.role == 'user'
            assert 'chat.send' in result.permissions
            assert result.session_token is not None
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_failure(self, auth_manager):
        """Test failed JWT authentication"""
        auth_data = {
            'method': 'jwt',
            'token': 'invalid_jwt_token'
        }
        
        # Mock JWT verification failure
        with patch.object(auth_manager.auth_manager, 'verify_jwt_token', return_value=None):
            result = await auth_manager.authenticate(auth_data)
            
            assert not result.success
            assert result.error_message == "Invalid or expired JWT token"
    
    @pytest.mark.asyncio
    async def test_api_key_authentication(self, auth_manager):
        """Test API key authentication"""
        auth_data = {
            'method': 'api_key',
            'api_key': 'valid_api_key'
        }
        
        # Mock API key verification
        key_info = {
            'name': 'test_key',
            'permissions': ['chat.read']
        }
        
        with patch.object(auth_manager.auth_manager, 'verify_api_key', return_value=key_info):
            result = await auth_manager.authenticate(auth_data)
            
            assert result.success
            assert result.user_id == 'api_key_test_key'
            assert result.role == 'user'
            assert 'chat.read' in result.permissions
    
    @pytest.mark.asyncio
    async def test_session_authentication(self, auth_manager):
        """Test session token authentication"""
        # Create a session first
        session_token = await auth_manager._create_session('test_user', 'user', ['chat.send'])
        
        auth_data = {
            'method': 'session',
            'session_token': session_token
        }
        
        result = await auth_manager.authenticate(auth_data)
        
        assert result.success
        assert result.user_id == 'test_user'
        assert result.role == 'user'
    
    @pytest.mark.asyncio
    async def test_session_expiry(self, auth_manager):
        """Test session expiry handling"""
        # Create an expired session
        session_token = await auth_manager._create_session('test_user', 'user', ['chat.send'])
        
        # Manually expire the session
        session_info = auth_manager.active_sessions[session_token]
        session_info['expires_at'] = datetime.utcnow() - timedelta(minutes=1)
        
        auth_data = {
            'method': 'session',
            'session_token': session_token
        }
        
        result = await auth_manager.authenticate(auth_data)
        
        assert not result.success
        assert result.error_message == "Session expired"
        assert session_token not in auth_manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_session_limits(self, auth_manager):
        """Test session limits per user"""
        user_id = 'test_user'
        
        # Create maximum number of sessions
        for i in range(auth_manager.max_sessions_per_user + 2):
            await auth_manager._create_session(f'{user_id}_{i}', 'user', ['chat.send'])
        
        # Should only have max_sessions_per_user sessions
        user_sessions = auth_manager.user_sessions.get(f'{user_id}_0', set())
        assert len(user_sessions) <= auth_manager.max_sessions_per_user
    
    def test_permission_checking(self, auth_manager):
        """Test permission checking logic"""
        # Test exact permission match
        assert auth_manager.check_permission(['chat.send'], 'chat.send')
        
        # Test wildcard permission
        assert auth_manager.check_permission(['chat.*'], 'chat.send')
        assert auth_manager.check_permission(['*'], 'any.permission')
        
        # Test permission denial
        assert not auth_manager.check_permission(['chat.read'], 'chat.send')
        assert not auth_manager.check_permission(['tasks.*'], 'chat.send')
    
    def test_role_hierarchy(self, auth_manager):
        """Test role hierarchy functionality"""
        # Test admin role
        admin_roles = auth_manager.get_user_roles('admin')
        assert 'admin' in admin_roles
        assert 'user' in admin_roles
        
        # Test user role
        user_roles = auth_manager.get_user_roles('user')
        assert 'user' in user_roles
        assert 'admin' not in user_roles
    
    def test_session_token_generation(self, auth_manager):
        """Test session token generation and verification"""
        user_id = 'test_user'
        token = auth_manager._generate_session_token(user_id)
        
        # Token should contain user ID
        assert user_id in token
        
        # Token should be verifiable
        assert auth_manager._verify_session_token(token)
        
        # Invalid token should not verify
        assert not auth_manager._verify_session_token('invalid_token')


class TestMessageValidator:
    """Test message validation and sanitization"""
    
    @pytest.fixture
    def validator(self):
        """Create message validator for testing"""
        return MessageValidator()
    
    def test_valid_chat_message(self, validator):
        """Test validation of valid chat message"""
        message = {
            'type': 'chat_message',
            'text': 'Hello, world!'
        }
        
        result = validator.validate_message(message)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_required_field(self, validator):
        """Test validation with missing required field"""
        message = {
            'type': 'chat_message'
            # Missing 'text' field
        }
        
        result = validator.validate_message(message)
        
        assert not result.is_valid
        assert 'Missing required field: text' in result.errors
    
    def test_unknown_message_type(self, validator):
        """Test validation with unknown message type"""
        message = {
            'type': 'unknown_type',
            'data': 'test'
        }
        
        result = validator.validate_message(message)
        
        assert not result.is_valid
        assert 'Unknown message type: unknown_type' in result.errors
    
    def test_message_too_large(self, validator):
        """Test validation of oversized message"""
        message = {
            'type': 'chat_message',
            'text': 'x' * 5000  # Exceeds max length for chat messages
        }
        
        result = validator.validate_message(message)
        
        assert not result.is_valid
        assert any('too large' in error for error in result.errors)
    
    def test_dangerous_content_detection(self, validator):
        """Test detection of dangerous content"""
        dangerous_messages = [
            {
                'type': 'chat_message',
                'text': '<script>alert("xss")</script>'
            },
            {
                'type': 'chat_message',
                'text': 'javascript:alert("xss")'
            },
            {
                'type': 'chat_message',
                'text': 'SELECT * FROM users; DROP TABLE users;'
            }
        ]
        
        for message in dangerous_messages:
            result = validator.validate_message(message)
            assert not result.is_valid
            assert any('Dangerous content detected' in error for error in result.errors)
    
    def test_suspicious_content_detection(self, validator):
        """Test detection of suspicious content"""
        message = {
            'type': 'chat_message',
            'text': '<iframe src="http://evil.com"></iframe>'
        }
        
        result = validator.validate_message(message)
        
        # Should be valid but with warnings
        assert result.is_valid
        assert any('Suspicious content detected' in warning for warning in result.warnings)
    
    def test_field_content_validation(self, validator):
        """Test specific field content validation"""
        # Invalid user_id format
        message = {
            'type': 'auth',
            'method': 'jwt',
            'user_id': 'invalid user id!'  # Contains invalid characters
        }
        
        result = validator.validate_auth_message(message)
        
        assert not result.is_valid
        assert any('Invalid user_id format' in error for error in result.errors)
    
    def test_url_validation(self, validator):
        """Test URL safety validation"""
        # Safe URL
        assert validator._is_safe_url('https://example.com/path')
        assert validator._is_safe_url('http://example.com')
        
        # Unsafe URLs
        assert not validator._is_safe_url('javascript:alert("xss")')
        assert not validator._is_safe_url('http://localhost/admin')
        assert not validator._is_safe_url('https://192.168.1.1/internal')
        assert not validator._is_safe_url('ftp://example.com')
    
    def test_html_sanitization(self, validator):
        """Test HTML content sanitization"""
        # Test allowed HTML
        safe_html = '<b>Bold text</b> and <i>italic text</i>'
        sanitized = validator._sanitize_string(safe_html, 'text')
        assert '<b>' in sanitized
        assert '<i>' in sanitized
        
        # Test dangerous HTML removal
        dangerous_html = '<script>alert("xss")</script><b>Safe content</b>'
        sanitized = validator._sanitize_string(dangerous_html, 'text')
        assert '<script>' not in sanitized
        assert '<b>' in sanitized
        
        # Test non-HTML field escaping
        html_content = '<b>Bold</b>'
        sanitized = validator._sanitize_string(html_content, 'user_id')
        assert '&lt;b&gt;' in sanitized  # Should be escaped
    
    def test_message_sanitization(self, validator):
        """Test complete message sanitization"""
        message = {
            'type': 'chat_message',
            'text': '<b>Safe</b> <script>alert("xss")</script>',
            'user_id': '<script>evil</script>',
            'nested': {
                'content': '<i>Nested</i> <script>bad</script>'
            },
            'list_field': ['<b>item1</b>', '<script>item2</script>']
        }
        
        sanitized = validator.sanitize_message(message)
        
        # Text field should allow safe HTML but remove scripts
        assert '<b>' in sanitized['text']
        assert '<script>' not in sanitized['text']
        
        # User ID should be escaped
        assert '&lt;script&gt;' in sanitized['user_id']
        
        # Nested content should be sanitized
        assert '<i>' in sanitized['nested']['content']
        assert '<script>' not in sanitized['nested']['content']
        
        # List items should be sanitized
        assert '<b>' in sanitized['list_field'][0]
        assert '<script>' not in sanitized['list_field'][1]


class TestSecurityAuditLogger:
    """Test security audit logging functionality"""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing"""
        config = Mock()
        config.get.return_value = "/tmp/test_logs"
        config.get_int.return_value = 100
        return SecurityAuditLogger(config)
    
    def test_log_security_event(self, audit_logger):
        """Test logging of security events"""
        audit_logger.log_security_event(
            'test_event',
            '192.168.1.100',
            {'detail': 'test'},
            SecurityEventLevel.WARNING,
            'test_user'
        )
        
        # Check event was recorded
        assert len(audit_logger.event_buffer) > 0
        event = audit_logger.event_buffer[-1]
        
        assert event['event_type'] == 'test_event'
        assert event['source_ip'] == '192.168.1.100'
        assert event['user_id'] == 'test_user'
        assert event['level'] == 'warning'
        assert event['details']['detail'] == 'test'
    
    def test_authentication_event_logging(self, audit_logger):
        """Test authentication event logging"""
        # Successful auth
        audit_logger.log_authentication_event(
            True, 'test_user', '192.168.1.100', 'jwt'
        )
        
        # Failed auth
        audit_logger.log_authentication_event(
            False, 'test_user', '192.168.1.100', 'jwt'
        )
        
        assert len(audit_logger.event_buffer) == 2
        
        success_event = audit_logger.event_buffer[0]
        assert success_event['event_type'] == 'auth_success'
        assert success_event['level'] == 'info'
        
        failure_event = audit_logger.event_buffer[1]
        assert failure_event['event_type'] == 'auth_failure'
        assert failure_event['level'] == 'warning'
    
    def test_security_summary(self, audit_logger):
        """Test security summary generation"""
        # Add some test events
        for i in range(5):
            audit_logger.log_security_event(
                'test_event',
                f'192.168.1.{100 + i}',
                {},
                SecurityEventLevel.INFO,
                f'user_{i}'
            )
        
        summary = audit_logger.get_security_summary(24)
        
        assert summary['total_events'] == 5
        assert 'test_event' in summary['events_by_type']
        assert summary['events_by_type']['test_event'] == 5
        assert summary['unique_ips'] == 5
        assert summary['unique_users'] == 5
    
    def test_compliance_report(self, audit_logger):
        """Test compliance report generation"""
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        # Add compliance events
        audit_logger.log_data_access(
            'test_user', '192.168.1.100', 'user_data', 'read'
        )
        audit_logger.log_admin_action(
            'admin_user', '192.168.1.101', 'delete_user', 'test_user'
        )
        
        report = audit_logger.get_compliance_report(start_date, end_date)
        
        assert report['total_compliance_events'] == 2
        assert 'data_access' in report['events_by_type']
        assert 'admin_action' in report['events_by_type']
        assert 'test_user' in report['user_activity']
        assert 'admin_user' in report['user_activity']
    
    def test_event_search(self, audit_logger):
        """Test event search functionality"""
        # Add test events
        audit_logger.log_security_event(
            'auth_failure', '192.168.1.100', {}, SecurityEventLevel.WARNING, 'user1'
        )
        audit_logger.log_security_event(
            'auth_success', '192.168.1.101', {}, SecurityEventLevel.INFO, 'user2'
        )
        
        # Search by event type
        results = audit_logger.search_events({'event_type': 'auth_failure'})
        assert len(results) == 1
        assert results[0]['event_type'] == 'auth_failure'
        
        # Search by IP
        results = audit_logger.search_events({'source_ip': '192.168.1.100'})
        assert len(results) == 1
        assert results[0]['source_ip'] == '192.168.1.100'
        
        # Search by user
        results = audit_logger.search_events({'user_id': 'user2'})
        assert len(results) == 1
        assert results[0]['user_id'] == 'user2'
    
    def test_anomaly_detection(self, audit_logger):
        """Test anomaly detection"""
        ip = '192.168.1.100'
        
        # Generate many auth failures to trigger anomaly detection
        for _ in range(60):  # More than threshold
            audit_logger.log_security_event(
                'auth_failures', ip, {}, SecurityEventLevel.WARNING
            )
        
        # Should have triggered anomaly detection
        anomaly_events = [
            event for event in audit_logger.event_buffer
            if event['event_type'] == 'anomaly_detected'
        ]
        
        assert len(anomaly_events) > 0
        anomaly_event = anomaly_events[0]
        assert anomaly_event['details']['anomaly_type'] == 'high_frequency'
        assert anomaly_event['details']['event_type'] == 'auth_failures'


# Integration tests
class TestWebSocketSecurityIntegration:
    """Integration tests for complete WebSocket security flow"""
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self):
        """Test complete authentication and message flow"""
        # This would require a running WebSocket server
        # For now, we'll test the components work together
        
        config = Mock()
        config.get.return_value = "test_value"
        config.get_int.return_value = 100
        
        security_manager = WebSocketSecurityManager(config)
        
        # Test that all components are properly initialized
        assert security_manager.auth_manager is not None
        assert security_manager.message_validator is not None
        assert security_manager.audit_logger is not None
        
        # Test security stats include all components
        stats = security_manager.get_security_stats()
        assert 'auth_manager_stats' in stats
        assert 'rate_limits' in stats
        assert 'active_connections' in stats


# Performance and stress tests
class TestWebSocketSecurityPerformance:
    """Performance tests for security components"""
    
    def test_message_validation_performance(self):
        """Test message validation performance under load"""
        validator = MessageValidator()
        
        message = {
            'type': 'chat_message',
            'text': 'Test message with some content'
        }
        
        start_time = time.time()
        
        # Validate 1000 messages
        for _ in range(1000):
            result = validator.validate_message(message)
            assert result.is_valid
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second)
        assert duration < 1.0
        
        # Calculate messages per second
        mps = 1000 / duration
        print(f"Message validation rate: {mps:.2f} messages/second")
        
        # Should handle at least 1000 messages per second
        assert mps > 1000
    
    def test_concurrent_authentication(self):
        """Test concurrent authentication handling"""
        config = Mock()
        config.get.return_value = "test_value"
        config.get_int.return_value = 100
        
        auth_manager = WebSocketAuthManager(config)
        
        def create_session_worker():
            """Worker function for creating sessions"""
            for i in range(10):
                asyncio.run(auth_manager._create_session(f'user_{i}', 'user', ['chat.send']))
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_session_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have created sessions without errors
        assert len(auth_manager.active_sessions) > 0
    
    def test_audit_logging_performance(self):
        """Test audit logging performance under load"""
        config = Mock()
        config.get.return_value = "/tmp/test_logs"
        config.get_int.return_value = 100
        
        audit_logger = SecurityAuditLogger(config)
        
        start_time = time.time()
        
        # Log 1000 events
        for i in range(1000):
            audit_logger.log_security_event(
                'test_event',
                f'192.168.1.{i % 255}',
                {'index': i},
                SecurityEventLevel.INFO,
                f'user_{i % 100}'
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 2.0
        
        # Calculate events per second
        eps = 1000 / duration
        print(f"Audit logging rate: {eps:.2f} events/second")
        
        # Should handle at least 500 events per second
        assert eps > 500


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])