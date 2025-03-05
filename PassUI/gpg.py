"""gpg.py - GPG encryption/decryption module for PassUI

This module provides GPG encryption and decryption functionality for the
PassUI password manager application using the PGPy library.
"""

import os
import tempfile
import logging
from typing import List, Dict, Optional

# Import PGPy for OpenPGP standard compatibility
from pgpy import PGPKey, PGPUID, PGPMessage
from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm
from pgpy.constants import CompressionAlgorithm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PyGPG')


class GPG:
    """GPG class providing OpenPGP standard encryption and decryption capabilities."""

    def __init__(self):
        """Initialize the GPG class with standard OpenPGP support"""
        # Default key directory similar to GPG's location
        self.keystore_dir = os.path.join(os.path.expanduser("~"), ".gnupg")
        self.private_keyring_path = os.path.join(self.keystore_dir, "secring.pgp")
        self.public_keyring_path = os.path.join(self.keystore_dir, "pubring.pgp")

        # Initialize keyring storage
        self.ensure_keystore_exists()

        # Key storage
        self._private_keys = {}
        self._public_keys = {}

        # Load existing keys
        self._load_keys()

    def ensure_keystore_exists(self):
        """Create keystore directory if it doesn't exist"""
        if not os.path.exists(self.keystore_dir):
            os.makedirs(self.keystore_dir)
            logger.info(f"Created keystore directory: {self.keystore_dir}")

    def _load_keys(self):
        """Load keys from the keyring files into memory"""
        # This implementation will maintain its own in-memory keyring
        # but will save/load to standard formats compatible with GPG
        self._private_keys = {}
        self._public_keys = {}

        # Load private keys if file exists
        try:
            if os.path.exists(self.private_keyring_path):
                with open(self.private_keyring_path, 'rb') as f:
                    keydata = f.read()
                    if keydata:
                        key = PGPKey()
                        key.parse(keydata)
                        self._private_keys[key.fingerprint.keyid] = key
                        logger.debug(f"Loaded private key: {key.fingerprint.keyid}")
        except Exception as e:
            logger.warning(f"Error loading private keyring: {e}")

        # Load public keys if file exists
        try:
            if os.path.exists(self.public_keyring_path):
                with open(self.public_keyring_path, 'rb') as f:
                    keydata = f.read()
                    if keydata:
                        key = PGPKey()
                        key.parse(keydata)
                        self._public_keys[key.fingerprint.keyid] = key
                        logger.debug(f"Loaded public key: {key.fingerprint.keyid}")
        except Exception as e:
            logger.warning(f"Error loading public keyring: {e}")

    def _save_keys(self):
        """Save keys to the keyring files"""
        # Ensure directory exists
        os.makedirs(self.keystore_dir, exist_ok=True)

        # Save private keys
        if self._private_keys:
            try:
                with open(self.private_keyring_path, 'wb') as f:
                    for key_id, key in self._private_keys.items():
                        f.write(bytes(key))
            except Exception as e:
                logger.error(f"Error saving private keys: {e}")

        # Save public keys
        if self._public_keys:
            try:
                with open(self.public_keyring_path, 'wb') as f:
                    for key_id, key in self._public_keys.items():
                        f.write(bytes(key))
            except Exception as e:
                logger.error(f"Error saving public keys: {e}")

    def list_keys(self) -> List[Dict[str, str]]:
        """List all keys in the keystore

        Returns:
            List[Dict[str, str]]: List of dictionaries containing key information
        """
        results = []

        # Handle case when no keys are available
        if not self._private_keys and not self._public_keys:
            return results

        # Process private keys first (these are the ones we own)
        for key_id, key in self._private_keys.items():
            try:
                # Extract user information from the key
                user_id = None
                for uid in key.userids:
                    user_id = uid
                    break

                if not user_id:
                    # Skip keys without user ID
                    continue

                # Extract creation and expiration dates
                created = key.created.strftime("%Y-%m-%d")

                # Check if expiration is set
                expire = "never"
                if hasattr(key, 'expiration') and key.expiration:
                    expire_date = key.created + key.expiration
                    expire = expire_date.strftime("%Y-%m-%d")

                # Determine encryption algorithm
                encryption = "RSA"
                if key.key_algorithm == PubKeyAlgorithm.DSA:
                    encryption = "DSA"
                elif key.key_algorithm == PubKeyAlgorithm.ElGamal:
                    encryption = "ELGAMAL"

                # Extract email from user ID
                email = "unknown@example.com"
                username = "Unknown"

                if hasattr(user_id, 'email') and user_id.email:
                    email = user_id.email
                if hasattr(user_id, 'name') and user_id.name:
                    username = user_id.name

                # Add key info to results
                key_info = {
                    "encryption": encryption,
                    "created": created,
                    "key": key_id,
                    "trust": "ultimate",  # Default to ultimate for keys we own
                    "mail": email,
                    "user": username,
                    "expire": expire,
                }

                results.append(key_info)
            except Exception as e:
                logger.warning(f"Error processing key {key_id}: {e}")

        # Process public keys that aren't also private keys
        for key_id, key in self._public_keys.items():
            # Skip keys we already processed as private keys
            if key_id in self._private_keys:
                continue

            try:
                # Extract user information from the key
                user_id = None
                for uid in key.userids:
                    user_id = uid
                    break

                if not user_id:
                    # Skip keys without user ID
                    continue

                # Extract creation and expiration dates
                created = key.created.strftime("%Y-%m-%d")

                # Check if expiration is set
                expire = "never"
                if hasattr(key, 'expiration') and key.expiration:
                    expire_date = key.created + key.expiration
                    expire = expire_date.strftime("%Y-%m-%d")

                # Determine encryption algorithm
                encryption = "RSA"
                if key.key_algorithm == PubKeyAlgorithm.DSA:
                    encryption = "DSA"
                elif key.key_algorithm == PubKeyAlgorithm.ElGamal:
                    encryption = "ELGAMAL"

                # Extract email from user ID
                email = "unknown@example.com"
                username = "Unknown"

                if hasattr(user_id, 'email') and user_id.email:
                    email = user_id.email
                if hasattr(user_id, 'name') and user_id.name:
                    username = user_id.name

                # Add key info to results
                key_info = {
                    "encryption": encryption,
                    "created": created,
                    "key": key_id,
                    "trust": "marginal",  # Default to marginal for public keys
                    "mail": email,
                    "user": username,
                    "expire": expire,
                }

                results.append(key_info)
            except Exception as e:
                logger.warning(f"Error processing public key {key_id}: {e}")

        return results

    def import_key(self, path_abs_gpg: str, passphrase: Optional[str] = None) -> str:
        """Import a key from a file

        Args:
            path_abs_gpg: Path to the key file
            passphrase: Optional passphrase for protected keys

        Returns:
            str: The key ID of the imported key

        Raises:
            ValueError: If there's an error importing the key
        """
        try:
            if not os.path.exists(path_abs_gpg):
                raise FileNotFoundError(f"Key file not found: {path_abs_gpg}")

            # Read the key file
            with open(path_abs_gpg, 'rb') as f:
                key_data = f.read()

            if not key_data:
                raise ValueError("Empty key file")

            # Parse the key
            key = PGPKey()
            key.parse(key_data)

            # If it's a private key and passphrase is provided, unlock it
            if key.is_protected and passphrase:
                with key.unlock(passphrase):
                    logger.info("Private key unlocked successfully")

            # Store the key
            if key.is_public:
                self._public_keys[key.fingerprint.keyid] = key
                logger.info(f"Imported public key: {key.fingerprint.keyid}")
            else:
                self._private_keys[key.fingerprint.keyid] = key
                # Also add the public part
                self._public_keys[key.fingerprint.keyid] = key.pubkey
                logger.info(f"Imported private key: {key.fingerprint.keyid}")

            # Save the updated keyring
            self._save_keys()

            return key.fingerprint.keyid

        except Exception as e:
            logger.error(f"Error importing key: {e}")
            raise ValueError(f"Error importing key: {e}")

    def export_key(self, path_abs_gpg: str, key: str, passphrase: Optional[str] = None) -> bool:
        """Export a key to a file

        Args:
            path_abs_gpg: The path to export the key to
            key: The key ID to export
            passphrase: Optional passphrase for protected keys

        Returns:
            bool: True if the export was successful, False otherwise

        Raises:
            ValueError: If there's an error exporting the key
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path_abs_gpg), exist_ok=True)

            # Find the key
            if key in self._private_keys:
                private_key = self._private_keys[key]

                # For private keys, ensure we can unlock it if it's protected
                if private_key.is_protected and passphrase:
                    with private_key.unlock(passphrase):
                        key_data = bytes(private_key)
                else:
                    key_data = bytes(private_key)

                # Write the key to file
                with open(path_abs_gpg, 'wb') as f:
                    f.write(key_data)

                logger.info(f"Exported private key to {path_abs_gpg}")
                return True

            elif key in self._public_keys:
                public_key = self._public_keys[key]

                # Write the key to file
                with open(path_abs_gpg, 'wb') as f:
                    f.write(bytes(public_key))

                logger.info(f"Exported public key to {path_abs_gpg}")
                return True

            else:
                raise ValueError(f"Key {key} not found")

        except Exception as e:
            logger.error(f"Error exporting key: {e}")
            raise ValueError(f"Error exporting key: {e}")

    def create_key(self, name: str, mail: str, passphrase: Optional[str] = None) -> str:
        """Create a new RSA key pair

        Args:
            name: The name for the key
            mail: The email address for the key
            passphrase: Optional passphrase to protect the key

        Returns:
            str: The key ID of the newly created key

        Raises:
            ValueError: If there's an error creating the key
        """
        try:
            if not name or not mail:
                raise ValueError("Name and email are required for key creation")

            # Create a new key
            key = PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 4096)  # 4096-bit key for better security

            # Add user ID
            uid = PGPUID.new(name, email=mail)
            key.add_uid(uid, usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
                        hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512],
                        ciphers=[SymmetricKeyAlgorithm.AES256],
                        compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP,
                                     CompressionAlgorithm.Uncompressed])

            # Protect the key with passphrase if provided
            if passphrase:
                key.protect(passphrase, SymmetricKeyAlgorithm.AES256, HashAlgorithm.SHA256)

            # Store the key
            key_id = key.fingerprint.keyid
            self._private_keys[key_id] = key
            self._public_keys[key_id] = key.pubkey

            # Save the updated keyring
            self._save_keys()

            logger.info(f"Created new key: {key_id} for {name} <{mail}>")
            return key_id

        except Exception as e:
            logger.error(f"Error creating key: {e}")
            raise ValueError(f"Error creating key: {e}")

    def remove_key(self, keys=None) -> bool:
        """Remove one or more keys from the keystore

        Args:
            keys: Key ID or list of key IDs to remove. If None, removes all keys.

        Returns:
            bool: True if the operation was successful
        """
        try:
            if keys is None:
                # Remove all keys
                self._private_keys = {}
                self._public_keys = {}
                logger.info("Removed all keys")
            else:
                # Convert to list if it's a single key
                if not isinstance(keys, list):
                    keys = [keys]

                # Remove specified keys
                for key_id in keys:
                    if key_id in self._private_keys:
                        del self._private_keys[key_id]
                        logger.info(f"Removed private key: {key_id}")
                    if key_id in self._public_keys:
                        del self._public_keys[key_id]
                        logger.info(f"Removed public key: {key_id}")

            # Save the updated keyring
            self._save_keys()
            return True

        except Exception as e:
            logger.error(f"Error removing keys: {e}")
            return False

    def encrypt(self, path_abs_gpg: str, path_abs_file: str, disabled_keys=None, binary_file=False) -> bool:
        """Encrypt a file for one or more recipients

        Args:
            path_abs_gpg: Path to save the encrypted file
            path_abs_file: Path to the file to encrypt
            disabled_keys: List of key IDs to exclude from encryption
            binary_file: Whether the file contains binary data

        Returns:
            bool: True if encryption was successful

        Raises:
            ValueError: If there's an error during encryption
        """
        if disabled_keys is None:
            disabled_keys = []

        try:
            # Check if file exists
            if not os.path.exists(path_abs_file):
                raise FileNotFoundError(f"Source file not found: {path_abs_file}")

            # Ensure output directory exists
            os.makedirs(os.path.dirname(path_abs_gpg), exist_ok=True)

            # Read the file to be encrypted
            with open(path_abs_file, 'rb') as f:
                plaintext = f.read()

            # Create a new PGP message
            message = PGPMessage.new(plaintext, file=True)

            # Encrypt for each recipient
            recipients = []
            for key_id, pubkey in self._public_keys.items():
                if key_id in disabled_keys:
                    continue
                recipients.append(pubkey)

            if not recipients:
                raise ValueError("No recipients found for encryption")

            # Encrypt the message
            encrypted_message = message
            for recipient in recipients:
                encrypted_message = recipient.encrypt(encrypted_message)

            # Write the encrypted message to file
            with open(path_abs_gpg, 'wb') as f:
                # Always write binary data for consistency
                f.write(bytes(encrypted_message))

            logger.info(f"Encrypted file to {path_abs_gpg}")
            return True

        except Exception as e:
            logger.error(f"Error encrypting file: {e}")
            raise ValueError(f"Error encrypting file: {e}")

    def write(self, path_abs_gpg: str, data_str: str, passphrase=None, disabled_keys=None) -> bool:
        """Write and encrypt a string to a file

        Args:
            path_abs_gpg: Path to save the encrypted file
            data_str: String data to encrypt
            passphrase: Optional passphrase (not used in this implementation)
            disabled_keys: List of key IDs to exclude from encryption

        Returns:
            bool: True if the operation was successful
        """
        if disabled_keys is None:
            disabled_keys = []

        try:
            # Ensure output directory exists
            path_abs_dir = os.path.dirname(path_abs_gpg)
            os.makedirs(path_abs_dir, exist_ok=True)

            # Create a temporary file for the data
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                path_data = tmp.name
                tmp.write(data_str.encode('utf-8'))

            # Encrypt the temporary file
            result = self.encrypt(path_abs_gpg, path_data, disabled_keys)
            return result
        except Exception as e:
            logger.error(f"Error writing encrypted data: {e}")
            return False
        finally:
            # Securely delete the temporary file
            if 'path_data' in locals():
                try:
                    with open(path_data, "wb") as f:
                        f.write(b"\0" * len(data_str))
                    os.remove(path_data)
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {e}")

    def read(self, path_abs_gpg: str, passphrase: Optional[str] = None) -> str:
        """Decrypt and read a file to a string

        Args:
            path_abs_gpg: Path to the encrypted file
            passphrase: Optional passphrase for protected keys

        Returns:
            str: The decrypted content as a string

        Raises:
            ValueError: If decryption fails
        """
        try:
            # Check if file exists
            if not os.path.exists(path_abs_gpg):
                raise FileNotFoundError(f"Encrypted file not found: {path_abs_gpg}")

            # Read the encrypted file
            with open(path_abs_gpg, 'rb') as f:
                encrypted_data = f.read()

            # Parse the PGP message
            message = PGPMessage.from_blob(encrypted_data)

            # Try to decrypt with any of our private keys
            decrypted = None
            error_messages = []

            # If no private keys available, return appropriate error
            if not self._private_keys:
                raise ValueError("No private keys available for decryption")

            for key_id, privkey in self._private_keys.items():
                try:
                    # Unlock the key if necessary
                    if privkey.is_protected:
                        if passphrase:
                            with privkey.unlock(passphrase):
                                decrypted = privkey.decrypt(message)
                        else:
                            error_messages.append(f"Key {key_id} is protected but no passphrase provided")
                            continue
                    else:
                        decrypted = privkey.decrypt(message)

                    if decrypted:
                        logger.info(f"Successfully decrypted with key {key_id}")
                        break

                except Exception as e:
                    error_messages.append(f"Failed to decrypt with key {key_id}: {e}")

            if not decrypted:
                if error_messages:
                    error_detail = "\n".join(error_messages)
                    raise ValueError(f"Decryption failed with all keys:\n{error_detail}")
                else:
                    raise ValueError("Could not decrypt with any of the available keys")

            # Return the decrypted content as a string
            # Handle different types of return values from PGPy
            try:
                if hasattr(decrypted, 'message'):
                    # If decrypted.message is bytes or bytearray, decode it
                    if isinstance(decrypted.message, (bytes, bytearray)):
                        return decrypted.message.decode('utf-8')
                    # If it's already a string, return it directly
                    return str(decrypted.message)
                elif isinstance(decrypted, (bytes, bytearray)):
                    return decrypted.decode('utf-8')
                else:
                    # Sometimes PGPy returns the string directly or other object
                    return str(decrypted)
            except UnicodeDecodeError:
                # Fallback for binary content
                logger.warning("Binary content detected, returning base64 encoded string")
                import base64
                if hasattr(decrypted, 'message') and isinstance(decrypted.message, (bytes, bytearray)):
                    binary_data = decrypted.message
                elif isinstance(decrypted, (bytes, bytearray)):
                    binary_data = decrypted
                else:
                    binary_data = str(decrypted).encode('utf-8')
                return f"[binary content: {base64.b64encode(binary_data).decode('ascii')}]"

        except Exception as e:
            logger.error(f"Error decrypting file: {e}")
            raise ValueError(f"Error decrypting file: {e}")

    def decrypt(self, path_abs_source: str, path_abs_dest: str, passphrase: Optional[str] = None) -> bool:
        """Decrypt a file and save to destination

        Args:
            path_abs_source: Path to the encrypted file
            path_abs_dest: Path to save the decrypted file
            passphrase: Optional passphrase for protected keys

        Returns:
            bool: True if decryption was successful
        """
        try:
            # Check if source file exists
            if not os.path.exists(path_abs_source):
                raise FileNotFoundError(f"Source file not found: {path_abs_source}")

            # Ensure output directory exists
            os.makedirs(os.path.dirname(path_abs_dest), exist_ok=True)

            # Read encrypted content
            with open(path_abs_source, 'rb') as f:
                encrypted_data = f.read()

            if not encrypted_data:
                raise ValueError("Empty encrypted file")

            # Parse the PGP message
            message = PGPMessage.from_blob(encrypted_data)

            # Try to decrypt with any of our private keys
            decrypted = None
            error_messages = []

            # If no private keys available, return appropriate error
            if not self._private_keys:
                raise ValueError("No private keys available for decryption")

            for key_id, privkey in self._private_keys.items():
                try:
                    # Unlock the key if necessary
                    if privkey.is_protected:
                        if passphrase:
                            with privkey.unlock(passphrase):
                                decrypted = privkey.decrypt(message)
                        else:
                            error_messages.append(f"Key {key_id} is protected but no passphrase provided")
                            continue
                    else:
                        decrypted = privkey.decrypt(message)

                    if decrypted:
                        logger.info(f"Successfully decrypted with key {key_id}")
                        break

                except Exception as e:
                    error_messages.append(f"Failed to decrypt with key {key_id}: {e}")

            if not decrypted:
                if error_messages:
                    error_detail = "\n".join(error_messages)
                    raise ValueError(f"Decryption failed with all keys:\n{error_detail}")
                else:
                    raise ValueError("Could not decrypt with any of the available keys")

            # Write the decrypted content to the destination file
            # Handle binary or text content appropriately
            if hasattr(decrypted, 'message'):
                data = decrypted.message
            else:
                data = decrypted

            with open(path_abs_dest, 'wb') as f:
                if isinstance(data, str):
                    f.write(data.encode('utf-8'))
                elif isinstance(data, (bytes, bytearray)):
                    f.write(data)
                else:
                    f.write(str(data).encode('utf-8'))

            logger.info(f"Decrypted file saved to {path_abs_dest}")
            return True

        except Exception as e:
            logger.error(f"Error in decrypt: {e}")
            return False