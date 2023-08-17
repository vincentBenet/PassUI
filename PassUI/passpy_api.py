import subprocess
import os
import sys
from tkinter import filedialog
from tkinter import Tk
from PassUI import utils


class PassPy:
    def __init__(self):
        self.KEY_ID = None
        self.GIT_DIR = None
        self.PYPASS_GPG_BIN = None
        self.PYPASS_STORE_DIR = None
        self.PYPASS_GIT_BIN = None
        self.config = self.load_config()
        self.check_paths()
        self.overwrite_config()

    def overwrite_config(self):
        for key1, value1 in self.config.items():
            for key2, value2 in value1.items():
                self.config[key1][key2] = getattr(self, key2)
        utils.overwrite_config(self.config)

    def load_config(self):
        config = utils.load_config()
        for key1, value1 in config.items():
            for key2, value2 in value1.items():
                setattr(self, key2, value2)
        return config

    def check_paths(self):
        self.check_path_store()
        self.check_path_git()
        self.check_path_gpg()

    def check_path_store(self):
        while not os.path.isdir(self.PYPASS_STORE_DIR):
            root = Tk()
            root.withdraw()
            self.PYPASS_STORE_DIR = filedialog.askdirectory(
                title="Select storage directory folder for PassUI",
            )

    def check_path_git(self):
        if not os.path.isfile(self.PYPASS_GIT_BIN):
            if sys.platform == "win32":
                command = "where"
                argu = "git"
                output_byte = subprocess.check_output(f"{command} {argu}", shell=True)
                output = output_byte.decode()
                paths = output.split("\n")
                for path in paths:
                    path = path.replace("\r", "")
                    if os.path.isfile(path):
                        self.PYPASS_GIT_BIN = path
                        break
                while not os.path.isfile(self.PYPASS_GIT_BIN):
                    self.PYPASS_GIT_BIN = filedialog.askopenfilename(
                        initialdir="/",
                        title="Select git.exe",
                        filetypes=[("GIT executable", "git.exe")]
                    )
            else:
                command = "which"
                argu = "git"
                output_byte = subprocess.check_output(f"{command} {argu}", shell=True)
                output = output_byte.decode()
                paths = output.split("\n")
                for path in paths:
                    path = path.replace("\r", "")
                    if os.path.isfile(path):
                        self.PYPASS_GIT_BIN = path
                        break

    def check_path_gpg(self):
        if not os.path.isfile(self.PYPASS_GPG_BIN):
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
                        break
                while not os.path.isfile(self.PYPASS_GPG_BIN):
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
        utils.write_gpg(path_abs_gpg, data_str, self.PYPASS_GPG_BIN, self.KEY_ID.split(", "))

    def read_gpg(self, path_abs_gpg):
        return utils.read_gpg(path_abs_gpg, self.PYPASS_GPG_BIN)
