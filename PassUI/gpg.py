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
    def __init__(self):
        """Initialize the GPG class with standard OpenPGP support"""
        # Default key directory similar to GPG's location
        self.keystore_dir = os.path.join(os.path.expanduser("~"), ".gnupg")
        self.private_keyring_path = os.path.join(self.keystore_dir, "secring.pgp")
        self.public_keyring_path = os.path.join(self.keystore_dir, "pubring.pgp")

        # Initialize keyring storage
        self.ensure_keystore_exists()

        # Key cache for better performance
        self._private_keys_cache = {}
        self._public_keys_cache = {}

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

        # Load keys if files exist
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
        # Save private keys
        if self._private_keys:
            with open(self.private_keyring_path, 'wb') as f:
                for key_id, key in self._private_keys.items():
                    f.write(bytes(key))

        # Save public keys
        if self._public_keys:
            with open(self.public_keyring_path, 'wb') as f:
                for key_id, key in self._public_keys.items():
                    f.write(bytes(key))

    def list_keys(self) -> List[Dict[str, str]]:
        """List all keys in the keystore in a format compatible with paste-2.txt"""
        results = []

        for key_id, key in self._private_keys.items():
            try:
                # Extract user information from the key
                user_id = None
                for uid in key.userids:
                    user_id = uid
                    break

                if not user_id:
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

        return results

    def import_key(self, path_abs_gpg: str, passphrase: Optional[str] = None):
        """Import a key from a file"""
        try:
            # Read the key file
            with open(path_abs_gpg, 'rb') as f:
                key_data = f.read()

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

    def export_key(self, path_abs_gpg: str, key: str, passphrase: Optional[str] = None):
        """Export a key to a file

        Args:
            path_abs_gpg: The path to export the key to
            key: The key ID to export
            passphrase: Optional passphrase for protected keys
        """
        try:
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

    def create_key(self, name: str, mail: str, passphrase: Optional[str] = None):
        """Create a new RSA key pair"""
        try:
            # Create a new key
            key = PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 2048)

            # Add user ID
            uid = PGPUID.new(name, email=mail)
            key.add_uid(uid, usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
                        hashes=[HashAlgorithm.SHA256],
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

    def remove_key(self, keys=None):
        """Remove one or more keys from the keystore"""
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

    def encrypt(self, path_abs_gpg: str, path_abs_file: str, disabled_keys=None, binary_file=False):
        """Encrypt a file for one or more recipients"""
        if disabled_keys is None:
            disabled_keys = []

        try:
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
            with open(path_abs_gpg, 'w' if not binary_file else 'wb') as f:
                f.write(str(encrypted_message) if not binary_file else bytes(encrypted_message))

            logger.info(f"Encrypted file to {path_abs_gpg}")
            return True

        except Exception as e:
            logger.error(f"Error encrypting file: {e}")
            raise ValueError(f"Error encrypting file: {e}")

    def write(self, path_abs_gpg: str, data_str: str, passphrase=None, disabled_keys=None):
        """Write and encrypt a string to a file"""
        path_abs_dir = os.path.dirname(path_abs_gpg)
        os.makedirs(path_abs_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path_data = tmp.name
            tmp.write(data_str.encode())

        try:
            result = self.encrypt(path_abs_gpg, path_data, disabled_keys)
            return result
        finally:
            # Securely delete the temporary file
            with open(path_data, "wb") as f:
                f.write(b"\0" * len(data_str))
            os.remove(path_data)

    def read(self, path_abs_gpg: str, passphrase: Optional[str] = None) -> str:
        """Decrypt and read a file to a string"""
        try:
            # Read the encrypted file
            with open(path_abs_gpg, 'rb') as f:
                encrypted_data = f.read()

            # Parse the PGP message
            message = PGPMessage.from_blob(encrypted_data)

            # Try to decrypt with any of our private keys
            decrypted = None
            error_messages = []

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

        except Exception as e:
            logger.error(f"Error decrypting file: {e}")
            raise ValueError(f"Error decrypting file: {e}")

    def decrypt(self, path_abs_source: str, path_abs_dest: str, passphrase: Optional[str] = None):
        """Decrypt a file and save to destination"""
        try:
            plaintext = self.read(path_abs_source, passphrase)

            with open(path_abs_dest, 'wb') as f:
                f.write(plaintext.encode())

            logger.info(f"Decrypted file saved to {path_abs_dest}")
            return True

        except Exception as e:
            logger.error(f"Error in decrypt: {e}")
            raise ValueError(f"Error in decrypt: {e}")


# import os
# import re
# import sys
# import subprocess
# import tempfile
# import time
# from tkinter import filedialog


# class GPG:
    # def __init__(self, gpg_exe="gpg"):
        # self.gpg_exe = gpg_exe
        # self.check_path_gpg()

    # def check_path_gpg(self):
        # if os.path.isfile(self.gpg_exe):
            # return True
        # print(f"GPG executable not found at {self.gpg_exe} with {sys.platform}")
        # self.search_gpg_exe()
        # while not os.path.isfile(self.gpg_exe):
            # self.gpg_exe = filedialog.askopenfilename(
                # initialdir="/",
                # title="Select gpg.exe / gpg2.exe",
                # filetypes=[("GPG executable", "gpg.exe gpg2.exe")]
            # )

    # def search_gpg_exe(self):
        # if sys.platform == "win32":
            # command = "where"
            # argu = "gpg"
            # output = subprocess.check_output(
                # f"{command} {argu}", shell=True, encoding="437")
            # paths = output.split("\n")
            # for path in paths:
                # path = path.replace("\r", "")
                # if os.path.isfile(path):
                    # self.gpg_exe = path
                    # print(f"Get path of GPG at {self.gpg_exe}")
                    # break
        # else:
            # command = "which"
            # argu = "gpg"
            # output = subprocess.check_output(
                # f"{command} {argu}", shell=True, encoding="437")
            # paths = output.split("\n")
            # for path in paths:
                # path = path.replace("\r", "")
                # if os.path.isfile(path):
                    # self.gpg_exe = path
                    # break

    # def run(self, commands, gpg_cmd=True):
        # if isinstance(commands, str):
            # commands = [commands]
        # if gpg_cmd:
            # commands = [self.gpg_exe] + commands
        # print(f"GPG:\n\t{commands = }")
        # res = subprocess.check_output(commands, encoding="437")
        # print(f"\t{repr(res)}")
        # return res

    # def list_keys(self):
        # str_list_keys = self.run("--list-secret-keys")
        # filtered_header = "".join(str_list_keys.split("---------\n")[1:])
        # str_keys = filtered_header.split("\n\n")[:-1]
        # res = []
        # for i, str_key in enumerate(str_keys):
            # try:
                # key_infos = {
                    # "encryption": re.findall(r"(?<=  )(\S*)(?= )", str_key.split("\n")[0])[-1],
                    # "created": re.findall(r"[0-9]+-[0-9]+-[0-9]+", str_key)[0],
                    # "key": re.findall(r"(?<= )(\S*)(?=\nuid)", str_key)[0],
                    # "trust": re.findall(r"(?<=\[)(.*)(?=\])", str_key.split("\n")[2])[0].replace(" ", ""),
                    # "mail": re.findall(r"(?<=<)(.*@.*..*)(?=>)", str_key)[0],
                    # "user": re.findall(r"(?<=\] )(.*)(?= <)", str_key)[0],
                    # "expire": re.findall(r"[0-9]+-[0-9]+-[0-9]+", str_key)[-1],
                # }
                # res.append(key_infos)
            # except IndexError:
                # print("_"*50+f"\nERROR key {i}\n{str_key}\n"+"_"*50)
        # return res

    # def import_key(self, path_abs_gpg, passphrase=None):
        # self.run([
            # *(["--pinentry-mode=loopback", "--yes", "--passphrase", f'{passphrase}'] if passphrase is not None else []),
            # "--allow-secret-key-import",
            # "--import",
            # path_abs_gpg
        # ])

    # def export_key(self, path_abs_gpg, key, passphrase=None):
        # self.run([
            # "--batch",
            # "--output", path_abs_gpg,
            # *(["--pinentry-mode=loopback", "--yes", "--passphrase", f'{passphrase}'] if passphrase is not None else []),
            # "--export-secret-key", key,
        # ])

    # def create_key(self, name, mail, passphrase=None):
        # with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # path_tmp = tmp.name
            # tmp.write("\n".join([
                # "Key-Type: 1",
                # "Key-Length: 2048",
                # "Subkey-Type: 1",
                # "Subkey-Length: 2048",
                # f"Name-Real: {name}",
                # f"Name-Email: {mail}",
                # f"Passphrase: {passphrase}" if passphrase is not None else "",
                # "Expire-Date: never",
            # ]).encode())
        # self.run(["--batch", "--gen-key", path_tmp])
        # os.remove(path_tmp)

    # def remove_key(self, keys=None):
        # if keys is None:
            # keys = []
        # if not isinstance(keys, list):
            # keys = [keys]
        # for key in self.list_keys():
            # key_id = key["key"]
            # if key_id not in keys and len(keys):
                # continue
            # self.run([
                # "--batch",
                # "--yes",
                # "--delete-secret-key",
                # key_id
            # ])

    # def encrypt(self, path_abs_gpg, path_abs_file, disabled_keys=None, binary_file=False):
        # if disabled_keys is None:
            # disabled_keys = []
        # recipients = []
        # for key in self.list_keys():
            # if key["key"] in disabled_keys:
                # continue
            # recipients.append("--recipient")
            # recipients.append(key["key"])
        # self.run([
            # "--batch", "--yes",
            # "--output", path_abs_gpg,
            # *(["--armor"] if not binary_file else []),
            # "--encrypt",
            # *recipients,
            # path_abs_file
        # ])

    # def write(self, path_abs_gpg, data_str, passphrase=None, disabled_keys=None):
        # path_abs_dir = os.path.dirname(path_abs_gpg)
        # os.makedirs(path_abs_dir, exist_ok=True)
        # tmp = tempfile.NamedTemporaryFile(delete=False)
        # path_data = tmp.name
        # tmp.write(data_str.encode())
        # tmp.close()
        # self.encrypt(path_abs_gpg, path_data, disabled_keys)
        # tmp = open(path_data, "w")
        # tmp.write("")
        # tmp.close()
        # os.remove(path_data)

    # def read(self, path_abs_gpg, passphrase=None):
        # return self.run([
            # *(["--pinentry-mode=loopback", "--passphrase", f"{passphrase}"] if passphrase is not None else []),
            # "--decrypt", path_abs_gpg,
            # *(),
        # ])

    # def decrypt(self, path_abs_source, path_abs_dest):
        # self.run([
            # "--output", path_abs_dest,
            # "--decrypt", path_abs_source,
        # ])
