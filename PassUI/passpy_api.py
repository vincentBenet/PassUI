import subprocess
import os
import sys
from tkinter import filedialog
from tkinter import Tk
from PassUI import utils


class PassPy:
    def __init__(
        self,
        PYPASS_GPG_BIN=None,
        PYPASS_STORE_DIR=None,
        KEY_ID=None,
        GIT_DIR=None,
    ):
        self.KEY_ID = None
        self.GIT_DIR = None
        self.PYPASS_GPG_BIN = None
        self.PYPASS_STORE_DIR = None
        self.config_path = {}
        self.config = self.load_config()
        self.check_paths()
        self.bypass_config(
            PYPASS_GPG_BIN,
            PYPASS_STORE_DIR,
            KEY_ID,
            GIT_DIR,
        )
        self.overwrite_config()

    def bypass_config(
        self,
        PYPASS_GPG_BIN,
        PYPASS_STORE_DIR,
        KEY_ID,
        GIT_DIR,
    ):
        for key, value in locals().items():
            if key not in self.config:
                continue
            self.change_config(key, value)

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

    def check_paths(self):
        self.check_path_store()
        self.check_path_gpg()

    def check_path_store(self):
        while not os.path.isdir(self.PYPASS_STORE_DIR):
            root = Tk()
            root.withdraw()
            self.PYPASS_STORE_DIR = filedialog.askdirectory(
                title="Select storage directory folder for PassUI",
            )

    def check_path_gpg(self):
        if not os.path.isfile(self.PYPASS_GPG_BIN):
            print(f"GPG executable not found at {self.PYPASS_GPG_BIN} with {sys.platform}")
            if sys.platform == "win32":
                command = "where"
                argu = "gpg"
                output_byte = subprocess.check_output(f"{command} {argu}", shell=True)
                output = output_byte.decode()
                paths = output.split("\n")
                for path in paths:
                    path = path.replace("\r", "")
                    if os.path.isfile(path):
                        self.PYPASS_GPG_BIN = path
                        print(f"Get path of GPG at {self.PYPASS_GPG_BIN}")
                        break
                while not os.path.isfile(self.PYPASS_GPG_BIN):
                    print(f"GPG path not found, ask to the user")
                    self.PYPASS_GPG_BIN = filedialog.askopenfilename(
                        initialdir="/",
                        title="Select gpg.exe / gpg2.exe",
                        filetypes=[("GPG executable", "gpg.exe gpg2.exe")]
                    )
            else:
                command = "which"
                argu = "gpg"
                output_byte = subprocess.check_output(f"{command} {argu}", shell=True)
                output = output_byte.decode()
                paths = output.split("\n")
                for path in paths:
                    path = path.replace("\r", "")
                    if os.path.isfile(path):
                        self.PYPASS_GPG_BIN = path
                        break

    @property
    def rel_paths_gpg(self):
        return utils.rel_paths_gpg(
            self.PYPASS_STORE_DIR,
            self.GIT_DIR
        )

    def rel_to_abs(self, rel_path):
        return utils.rel_to_abs(self.PYPASS_STORE_DIR, rel_path)

    def read_key(self, path_rel):
        path_abs_gpg = self.rel_to_abs(path_rel)
        data_str = self.read_gpg(path_abs_gpg)
        data_dict = utils.data_str_to_dict(data_str)
        return data_dict

    def write_key(self, path_rel, data_dict):
        data_str = utils.data_dict_to_str(data_dict)
        self.write_gpg(os.path.join(self.PYPASS_STORE_DIR, path_rel + ".gpg"), data_str)

    def write_gpg(self, path_abs_gpg, data_str):
        utils.write_gpg(path_abs_gpg, data_str, self.PYPASS_GPG_BIN, self.KEY_ID)

    def read_gpg(self, path_abs_gpg):
        return utils.read_gpg(path_abs_gpg, self.PYPASS_GPG_BIN)

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
        return True
