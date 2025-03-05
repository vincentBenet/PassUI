import os
import shutil
from pathlib import Path
from PassUI import utils, gpg


class PassStore(gpg.GPG):
    def __init__(self):
        self.gpg_exe = None
        self.path_store = None
        self.ignored_files = None
        self.ignored_directories = None
        self.config_path = {}
        self.config = self.load_config()
        self.check_path_store()
        self.check_ignored_files()
        self.check_ignored_folders()
        super().__init__()
        self.overwrite_config()
        self.write_gpg_ids()

    def check_ignored_files(self):
        for path_rel in self.ignored_files:
            path_abs_ignored = os.path.join(
                self.path_store,
                path_rel
            )
            if not os.path.isfile(path_abs_ignored):
                self.ignored_files.remove(path_rel)
        self.ignored_files = list(set(self.ignored_files))

    def check_ignored_folders(self):
        for path_rel in self.ignored_directories:
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
        path = os.path.join(self.path_store, ".gpg-id")
        with open(path, "w") as f:
            f.write("\n".join([
                key["key"]
                for key in self.list_keys()
            ]) + "\n")

    def overwrite_config(self):
        for key1, value1 in self.config.items():
            for key2, value2 in value1.items():
                self.config[key1][key2] = getattr(self, key2)
        utils.write_config(self.config)

    def load_config(self):
        config = utils.load_config()
        for key1, value1 in config.items():
            for key2, value2 in value1.items():
                setattr(self, key2, value2)
                self.config_path[key2] = key1
        return config

    def check_path_store(self):
        if (
            self.path_store is None or
            not os.path.isdir(self.path_store)
        ):
            self.path_store = str(Path.home())

    @property
    def rel_paths_gpg(self):
        return utils.rel_paths_gpg(
            self.path_store,
            self.ignored_directories,
            self.ignored_files
        )

    def read_key(self, path_rel):
        from PyQt5.QtWidgets import QInputDialog, QLineEdit
        passphrase, ok = QInputDialog.getText(
            None,  # Parent widget (None for a standalone dialog)
            "Passphrase Required",  # Dialog title
            "Enter the passphrase for this key:",  # Dialog message
            QLineEdit.Password,  # Use password field that masks input
            ""  # Default text
        )
        if ok:
            return utils.data_str_to_dict(
                self.read(
                    utils.rel_to_abs(self.path_store, path_rel),
                    passphrase=passphrase,
                )
            )
        else:
            # User canceled the dialog
            raise ValueError("Passphrase entry canceled by user")

    def write_key(self, path_rel, data_dict):
        data_str = utils.data_dict_to_str(data_dict)
        self.write(
            os.path.join(self.path_store, path_rel + ".gpg"),
            data_str,
            disabled_keys=self.config["settings"]["disabled_keys"]
        )

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
        self.encrypt(
            path_abs + ".bgpg",
            path_abs,
            self.config["settings"]["disabled_keys"],
            binary_file=True,
        )
        if replace:
            os.remove(path_abs)


    def decrypt_file(self, path_abs, replace=False):
        self.decrypt(
            path_abs,
            path_abs[:-len(".bgpg")]
        )
        if replace:
            os.remove(path_abs)

    def encrypt_directory(self, path_abs, replace=False, zip=False):
        if zip:
            shutil.make_archive(path_abs, 'zip', path_abs)
            self.encrypt_file(path_abs + ".zip", replace=replace)
            if replace:
                shutil.rmtree(path_abs)
        else:
            for root, subdirs, files in os.walk(path_abs):
                for file in files:
                    path_abs_file = os.path.join(root, file)
                    self.encrypt_file(path_abs_file, replace=replace)

    def decrypt_directory(self, path_abs, replace=False, zip=False):
        if zip:
            self.decrypt_file(path_abs, replace=replace)
            path_zip = path_abs[:-len(".bgpg")]
            path_dest = path_zip[:-len(".zip")]
            shutil.unpack_archive(path_zip, path_dest, "zip")
            if replace:
                os.remove(path_zip)
        else:
            for root, subdirs, files in os.walk(path_abs):
                for file in files:
                    path_abs_file = os.path.join(root, file)
                    if path_abs_file.endswith(".bgpg"):
                        self.decrypt_file(path_abs_file, replace=replace)
