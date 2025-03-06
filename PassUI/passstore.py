"""passstore.py"""

import os
import shutil
from pathlib import Path
from PassUI import utils, gpg


class PassStore(gpg.GPG):
    def __init__(self):
        # Initialize attributes with default values before loading config
        self.gpg_exe = None
        self.path_store = str(Path.home())  # Default to home directory
        self.ignored_files = []  # Initialize as empty list
        self.ignored_directories = []  # Initialize as empty list
        self.config_path = {}

        # Load config after initializing attributes
        self.config = self.load_config()

        # Check paths and configurations
        self.check_path_store()
        self.check_ignored_files()
        self.check_ignored_folders()

        # Initialize parent class (GPG)
        super().__init__()

        # Update config and write gpg IDs
        self.overwrite_config()
        self.write_gpg_ids()

    def check_ignored_files(self):
        # Ensure ignored_files is a list before using list methods
        if self.ignored_files is None:
            self.ignored_files = []

        # Create a copy of the list to avoid modifying during iteration
        for path_rel in list(self.ignored_files):
            path_abs_ignored = os.path.join(
                self.path_store,
                path_rel
            )
            if not os.path.isfile(path_abs_ignored):
                self.ignored_files.remove(path_rel)
        self.ignored_files = list(set(self.ignored_files))

    def check_ignored_folders(self):
        # Ensure ignored_directories is a list before using list methods
        if self.ignored_directories is None:
            self.ignored_directories = []

        # Create a copy of the list to avoid modifying during iteration
        for path_rel in list(self.ignored_directories):
            path_abs_ignored = os.path.join(
                self.path_store,
                path_rel
            )
            if not os.path.isdir(path_abs_ignored):
                self.ignored_directories.remove(path_rel)
        self.ignored_directories = list(set(self.ignored_directories))

    def change_path_store(self, path_store):
        print(f"{path_store = }")
        if (
            path_store == self.path_store or
            path_store is None or
            not os.path.isdir(path_store)
        ):
            return False
        self.change_config("path_store", path_store)
        self.write_gpg_ids()
        return True

    def write_gpg_ids(self):
        try:
            path = os.path.join(self.path_store, ".gpg-id")
            # Ensure the directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)

            keys = self.list_keys()
            key_ids = [key["key"] for key in keys] if keys else []

            with open(path, "w") as f:
                f.write("\n".join(key_ids) + "\n")
            return True
        except Exception as e:
            print(f"Error writing GPG IDs: {e}")
            return False

    def overwrite_config(self):
        try:
            # Ensure config dictionary is properly initialized
            if not isinstance(self.config, dict):
                self.config = {}

            for key1, value1 in self.config.items():
                if not isinstance(value1, dict):
                    self.config[key1] = {}
                for key2, value2 in value1.items():
                    # Get attribute safely, using default value if attribute doesn't exist
                    attr_value = getattr(self, key2, value2)
                    self.config[key1][key2] = attr_value
            utils.write_config(self.config)
            return True
        except Exception as e:
            print(f"Error overwriting config: {e}")
            return False

    def load_config(self):
        try:
            config = utils.load_config()
            for key1, value1 in config.items():
                for key2, value2 in value1.items():
                    setattr(self, key2, value2)
                    self.config_path[key2] = key1
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            # Return a default config when loading fails
            return {
                "settings": {
                    "path_store": str(Path.home()),
                    "ignored_files": [],
                    "ignored_directories": [],
                    "disabled_keys": []
                }
            }

    def check_path_store(self):
        if (
            self.path_store is None or
            not os.path.isdir(self.path_store)
        ):
            self.path_store = str(Path.home())
            # Try to create the directory if it doesn't exist
            try:
                os.makedirs(self.path_store, exist_ok=True)
            except Exception as e:
                print(f"Error creating path_store directory: {e}")

    @property
    def rel_paths_gpg(self):
        return utils.rel_paths_gpg(
            self.path_store,
            self.ignored_directories or [],  # Ensure we pass a list
            self.ignored_files or []  # Ensure we pass a list
        )

    def read_key(self, path_rel):
        from PyQt5.QtWidgets import QInputDialog, QLineEdit
        try:
            # Ensure the path exists
            abs_path = utils.rel_to_abs(self.path_store, path_rel)
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"Key file not found: {abs_path}")

            passphrase, ok = QInputDialog.getText(
                None,  # Parent widget (None for a standalone dialog)
                "Passphrase Required",  # Dialog title
                "Enter the passphrase for this key:",  # Dialog message
                QLineEdit.Password,  # Use password field that masks input
                ""  # Default text
            )

            if ok:
                decrypted_data = self.read(abs_path, passphrase=passphrase)
                if decrypted_data:
                    return utils.data_str_to_dict(decrypted_data)
                else:
                    raise ValueError("Failed to decrypt the key")
            else:
                # User canceled the dialog
                raise ValueError("Passphrase entry canceled by user")
        except Exception as e:
            print(f"Error reading key {path_rel}: {e}")
            # Return a minimal dictionary as fallback
            return {"PASSWORD": "", "error": str(e)}

    def write_key(self, path_rel, data_dict):
        try:
            data_str = utils.data_dict_to_str(data_dict)
            # Ensure the directory exists
            full_path = os.path.join(self.path_store, path_rel + ".gpg")
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Get disabled keys with proper default
            disabled_keys = self.config.get("settings", {}).get("disabled_keys", [])

            return self.write(
                full_path,
                data_str,
                disabled_keys=disabled_keys
            )
        except Exception as e:
            print(f"Error writing key {path_rel}: {e}")
            return False

    def change_config(self, key, value):
        if key not in self.config_path:
            return False
        key1 = self.config_path[key]
        if key1 not in self.config:
            return False
        dico = self.config[key1]
        if key not in dico:
            return False
        if value == dico[key]:
            return False
        dico[key] = value
        setattr(self, key, value)
        utils.write_config(self.config)
        return True

    def encrypt_file(self, path_abs, replace=False):
        try:
            if not path_abs or not os.path.exists(path_abs):
                print(f"File not found for encryption: {path_abs}")
                return False

            # Use .bgpg extension for binary GPG files
            output_path = path_abs + ".bgpg"

            # Get disabled keys with proper default
            disabled_keys = self.config.get("settings", {}).get("disabled_keys", [])

            result = self.encrypt(
                output_path,
                path_abs,
                disabled_keys=disabled_keys,
                binary_file=True,
            )

            if result and replace:
                try:
                    os.remove(path_abs)
                except Exception as e:
                    print(f"Error removing original file after encryption: {e}")

            return result
        except Exception as e:
            print(f"Error encrypting file {path_abs}: {e}")
            return False

    def decrypt_file(self, path_abs, replace=False):
        try:
            if not path_abs or not os.path.exists(path_abs):
                print(f"File not found for decryption: {path_abs}")
                return False

            # Remove .bgpg extension for output file
            output_path = path_abs[:-len(".bgpg")] if path_abs.endswith(".bgpg") else path_abs + ".decrypted"

            result = self.decrypt(
                path_abs,
                output_path
            )

            if result and replace:
                try:
                    os.remove(path_abs)
                except Exception as e:
                    print(f"Error removing encrypted file after decryption: {e}")

            return result
        except Exception as e:
            print(f"Error decrypting file {path_abs}: {e}")
            return False

    def encrypt_directory(self, path_abs, replace=False, zip=False):
        try:
            if not path_abs or not os.path.isdir(path_abs):
                print(f"Directory not found for encryption: {path_abs}")
                return False

            if zip:
                # Create a zip archive first
                try:
                    zip_path = path_abs + ".zip"
                    shutil.make_archive(path_abs, 'zip', path_abs)
                    # Encrypt the zip file
                    result = self.encrypt_file(zip_path, replace=replace)

                    # Remove the directory if requested and encryption succeeded
                    if result and replace:
                        try:
                            shutil.rmtree(path_abs)
                        except Exception as e:
                            print(f"Error removing directory after encryption: {e}")

                    # Remove the temporary zip file if not needed
                    if not replace and os.path.exists(zip_path):
                        os.remove(zip_path)

                    return result
                except Exception as e:
                    print(f"Error zipping directory for encryption: {e}")
                    return False
            else:
                # Encrypt each file individually
                success = True
                for root, subdirs, files in os.walk(path_abs):
                    for file in files:
                        path_abs_file = os.path.join(root, file)
                        result = self.encrypt_file(path_abs_file, replace=replace)
                        if not result:
                            success = False
                return success
        except Exception as e:
            print(f"Error encrypting directory {path_abs}: {e}")
            return False

    def decrypt_directory(self, path_abs, replace=False, zip=False):
        try:
            if not path_abs:
                print("No directory specified for decryption")
                return False

            if zip:
                # Path should be a .bgpg encrypted zip file
                if not path_abs.endswith(".bgpg"):
                    print(f"Expected .bgpg file for zip decryption: {path_abs}")
                    return False

                # Decrypt the zip file first
                result = self.decrypt_file(path_abs, replace=replace)
                if result:
                    # Extract the zip archive
                    zip_path = path_abs[:-len(".bgpg")]
                    if not zip_path.endswith(".zip"):
                        print(f"Decrypted file does not have .zip extension: {zip_path}")
                        return False

                    # Get extraction directory
                    extract_dir = zip_path[:-len(".zip")]
                    try:
                        shutil.unpack_archive(zip_path, extract_dir, "zip")

                        # Remove the zip file if requested
                        if replace and os.path.exists(zip_path):
                            os.remove(zip_path)

                        return True
                    except Exception as e:
                        print(f"Error extracting zip archive: {e}")
                        return False
                else:
                    return False
            else:
                # Decrypt each .bgpg file in the directory
                if not os.path.isdir(path_abs):
                    print(f"Directory not found for decryption: {path_abs}")
                    return False

                success = True
                for root, subdirs, files in os.walk(path_abs):
                    for file in files:
                        if file.endswith(".bgpg"):
                            path_abs_file = os.path.join(root, file)
                            result = self.decrypt_file(path_abs_file, replace=replace)
                            if not result:
                                success = False
                return success
        except Exception as e:
            print(f"Error decrypting directory {path_abs}: {e}")
            return False
