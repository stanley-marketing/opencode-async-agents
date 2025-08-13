# SPDX-License-Identifier: MIT
"""
Encryption utilities for OpenCode-Slack API.
Provides data encryption/decryption for sensitive information.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional
import base64
import json
import logging
import secrets

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""

    def __init__(self, password: str = None):
        self.password = password or secrets.token_urlsafe(32)
        self.salt = secrets.token_bytes(16)
        self._fernet = None
        self._initialize_encryption()

        logger.info("Encryption manager initialized")

    def _initialize_encryption(self):
        """Initialize Fernet encryption with password-based key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        self._fernet = Fernet(key)

    def encrypt_data(self, data: Any) -> str:
        """Encrypt data and return base64 encoded string"""
        try:
            # Convert data to JSON string
            json_data = json.dumps(data, default=str)

            # Encrypt the data
            encrypted_data = self._fernet.encrypt(json_data.encode())

            # Return base64 encoded result
            return base64.urlsafe_b64encode(encrypted_data).decode()

        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> Any:
        """Decrypt base64 encoded string and return original data"""
        try:
            # Decode base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())

            # Decrypt the data
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)

            # Parse JSON
            json_data = decrypted_bytes.decode()
            return json.loads(json_data)

        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def encrypt_string(self, text: str) -> str:
        """Encrypt a string and return base64 encoded result"""
        try:
            encrypted_data = self._fernet.encrypt(text.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"String encryption error: {e}")
            raise

    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt base64 encoded string"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"String decryption error: {e}")
            raise

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)

# Global encryption manager instance
encryption_manager = EncryptionManager()

def encrypt_sensitive_fields(data: Dict, fields: list) -> Dict:
    """Encrypt specified fields in a dictionary"""
    encrypted_data = data.copy()

    for field in fields:
        if field in encrypted_data:
            try:
                encrypted_data[field] = encryption_manager.encrypt_string(str(encrypted_data[field]))
                logger.debug(f"Encrypted field: {field}")
            except Exception as e:
                logger.error(f"Failed to encrypt field {field}: {e}")

    return encrypted_data

def decrypt_sensitive_fields(data: Dict, fields: list) -> Dict:
    """Decrypt specified fields in a dictionary"""
    decrypted_data = data.copy()

    for field in fields:
        if field in decrypted_data:
            try:
                decrypted_data[field] = encryption_manager.decrypt_string(decrypted_data[field])
                logger.debug(f"Decrypted field: {field}")
            except Exception as e:
                logger.error(f"Failed to decrypt field {field}: {e}")

    return decrypted_data