import subprocess
import os
import sys
from tkinter import filedialog
from tkinter import Tk
from PassUI import utils, gpg


class PassPy(gpg.GPG):
    def __init__(
        self,
        gpg_exe=None,
        path_store=None,
        ignore_dir=".git",
    ):
        self.ignore_dir = None
        self.gpg_exe = None
        self.path_store = None
        self.config_path = {}
        self.config = self.load_config()

        self.check_path_store()
        self.check_path_gpg()

        self.bypass_config(
            gpg_exe,
            path_store,
            ignore_dir,
        )
        self.overwrite_config()
        super().__init__(self.gpg_exe)
        self.write_gpg_ids()

    def write_gpg_ids(self):
        path = os.path.join(self.path_store, ".gpg-id")
        with open(path, "w") as f:
            f.write("\n".join([
                key["key"]
                for key in self.list_keys()
            ]) + "\n")

    def bypass_config(
        self,
        gpg_exe,
        path_store,
        ignore_dir,
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

    def check_path_store(self):
        while not os.path.isdir(self.path_store):
            root = Tk()
            root.withdraw()
            self.path_store = filedialog.askdirectory(
                title="Select storage directory folder for PassUI",
            )

    def check_path_gpg(self):
        if not os.path.isfile(self.gpg_exe):
            print(f"GPG executable not found at {self.gpg_exe} with {sys.platform}")
            if sys.platform == "win32":
                command = "where"
                argu = "gpg"
                output_byte = subprocess.check_output(f"{command} {argu}", shell=True)
                output = output_byte.decode()
                paths = output.split("\n")
                for path in paths:
                    path = path.replace("\r", "")
                    if os.path.isfile(path):
                        self.gpg_exe = path
                        print(f"Get path of GPG at {self.gpg_exe}")
                        break
                while not os.path.isfile(self.gpg_exe):
                    print(f"GPG path not found, ask to the user")
                    self.gpg_exe = filedialog.askopenfilename(
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
                        self.gpg_exe = path
                        break

    @property
    def rel_paths_gpg(self):
        return utils.rel_paths_gpg(
            self.path_store,
            self.ignore_dir
        )

    def rel_to_abs(self, rel_path):
        return utils.rel_to_abs(self.path_store, rel_path)

    def read_key(self, path_rel):
        path_abs_gpg = self.rel_to_abs(path_rel)
        data_str = self.read_gpg(path_abs_gpg)
        data_dict = utils.data_str_to_dict(data_str)
        return data_dict

    def write_key(self, path_rel, data_dict):
        data_str = utils.data_dict_to_str(data_dict)
        self.write_gpg(os.path.join(self.path_store, path_rel + ".gpg"), data_str)

    def write_gpg(self, path_abs_gpg, data_str):
        self.write(path_abs_gpg, data_str)

    def read_gpg(self, path_abs_gpg):
        return self.read(path_abs_gpg)

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
