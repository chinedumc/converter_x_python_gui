from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import b64encode, b64decode
import os
from typing import Union
from pathlib import Path
from ..config import config
from ..utils.audit import audit_logger

class AESEncryption:
    def __init__(self):
        self.key = self._derive_key(config.ENCRYPTION_KEY.encode())
        self.backend = default_backend()

    def _derive_key(self, key: bytes, salt: bytes = None) -> bytes:
        """Derive a 32-byte key using PBKDF2."""
        if salt is None:
            # Use a fixed salt for consistent key derivation
            salt = b'converter_x_fixed_salt'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(key)

    def _pad(self, data: bytes) -> bytes:
        """Pad data to be multiple of 16 bytes (AES block size)."""
        pad_length = 16 - (len(data) % 16)
        padding = bytes([pad_length] * pad_length)
        return data + padding

    def _unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        pad_length = data[-1]
        return data[:-pad_length]

    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """Encrypt data using AES-256 in CBC mode with PKCS7 padding."""
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data = data.encode()

            # Generate a random IV
            iv = os.urandom(16)

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=self.backend
            )

            # Encrypt
            encryptor = cipher.encryptor()
            padded_data = self._pad(data)
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            # Combine IV and ciphertext and encode to base64
            encrypted = b64encode(iv + ciphertext).decode('utf-8')

            audit_logger.log_security_event(
                user_id="system",
                action="encrypt_data",
                ip_address="localhost",
                details={"operation": "encrypt", "size": len(data)}
            )

            return encrypted

        except Exception as e:
            audit_logger.log_error(
                user_id="system",
                action="encrypt_data",
                error=e,
                details={"operation": "encrypt"}
            )
            raise

    def decrypt_data(self, encrypted_data: str) -> bytes:
        """Decrypt data using AES-256 in CBC mode with PKCS7 padding."""
        try:
            # Decode from base64
            encrypted_bytes = b64decode(encrypted_data)

            # Extract IV and ciphertext
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=self.backend
            )

            # Decrypt
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            data = self._unpad(padded_data)

            audit_logger.log_security_event(
                user_id="system",
                action="decrypt_data",
                ip_address="localhost",
                details={"operation": "decrypt", "size": len(data)}
            )

            return data

        except Exception as e:
            audit_logger.log_error(
                user_id="system",
                action="decrypt_data",
                error=e,
                details={"operation": "decrypt"}
            )
            raise

    def encrypt_file(self, input_path: Union[str, Path], output_path: Union[str, Path]) -> None:
        """Encrypt a file using AES-256."""
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            # Read file content
            with open(input_path, 'rb') as f:
                data = f.read()

            # Encrypt data
            encrypted_data = self.encrypt_data(data)

            # Write encrypted data
            with open(output_path, 'w') as f:
                f.write(encrypted_data)

            audit_logger.log_security_event(
                user_id="system",
                action="encrypt_file",
                ip_address="localhost",
                details={
                    "input_file": str(input_path),
                    "output_file": str(output_path),
                    "size": len(data)
                }
            )

        except Exception as e:
            audit_logger.log_error(
                user_id="system",
                action="encrypt_file",
                error=e,
                details={"file": str(input_path)}
            )
            raise

    def decrypt_file(self, input_path: Union[str, Path], output_path: Union[str, Path]) -> None:
        """Decrypt a file using AES-256."""
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            # Read encrypted data
            with open(input_path, 'r') as f:
                encrypted_data = f.read()

            # Decrypt data
            decrypted_data = self.decrypt_data(encrypted_data)

            # Write decrypted data
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

            audit_logger.log_security_event(
                user_id="system",
                action="decrypt_file",
                ip_address="localhost",
                details={
                    "input_file": str(input_path),
                    "output_file": str(output_path),
                    "size": len(decrypted_data)
                }
            )

        except Exception as e:
            audit_logger.log_error(
                user_id="system",
                action="decrypt_file",
                error=e,
                details={"file": str(input_path)}
            )
            raise

# Create singleton instance
encryption = AESEncryption()