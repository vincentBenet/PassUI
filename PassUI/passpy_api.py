import subprocess
import os
import sys
import yaml
from pathlib import Path
import passpy
from gnupg import GPG

from tkinter import filedialog
from tkinter import Tk


def get_config_path():
    return Path.home() / "passui.yml"


def load_config():
    path_config = get_config_path()
    if not os.path.isfile(path_config):
        path_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "PassUI.yml"))
    print(f"Reading config file at {path_config}")
    return yaml.safe_load(Path(path_config).read_text())


class PassPy(passpy.store.Store):
    def __init__(self):
        self.config = load_config()
        self.PYPASS_STORE_DIR = self.config['variables']['PYPASS_STORE_DIR']
        self.PYPASS_GIT_BIN = self.config['variables']['PYPASS_GIT_BIN']
        self.PYPASS_GPG_BIN = self.config['variables']['PYPASS_GPG_BIN']
        self.git_folder_name = self.config['settings']['git_folder_name']
        self.GIT_DIR = os.path.join(self.PYPASS_STORE_DIR, self.git_folder_name)
        self.platform = sys.platform
        self.check_paths()
        self.overwrite_config()
        super().__init__(
            gpg_bin=self.PYPASS_GPG_BIN,
            git_bin=self.PYPASS_GIT_BIN,
            store_dir=self.PYPASS_STORE_DIR,
            use_agent=True,
            interactive=False,
            verbose=True
        )

    def overwrite_config(self):
        path = get_config_path()
        config = self.config | {
            "settings": {
                "git_folder_name": self.git_folder_name
            },
            "variables": {
                "PYPASS_GIT_BIN": self.PYPASS_GIT_BIN,
                "PYPASS_GPG_BIN": self.PYPASS_GPG_BIN,
                "PYPASS_STORE_DIR": self.PYPASS_STORE_DIR,
            },
        }
        if config != self.config:
            print(f"Writing user config-file to {path}\n{config}")
            with open(path, 'w') as outfile:
                yaml.dump(config, outfile, default_flow_style=False)

    def check_paths(self):
        self.check_path_store()
        self.check_path_git()
        self.check_path_gpg()

    def check_path_store(self):
        while not os.path.isdir(self.PYPASS_STORE_DIR):
            root = Tk()
            root.withdraw()
            self.PYPASS_STORE_DIR = filedialog.askdirectory()

    def check_path_git(self):
        if not os.path.isfile(self.PYPASS_GIT_BIN):
            if self.platform == "win32":
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
            if self.platform == "win32":
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
    def keys(self):
        res = {}
        for root, dirs, files in os.walk(self.PYPASS_STORE_DIR):
            if root.startswith(os.path.abspath(self.GIT_DIR)):
                continue
            print(files)
            rel_path = root[len(self.PYPASS_STORE_DIR)+1:]
            print(rel_path)
            if not len(rel_path):
                for file in files:
                    if not file.endswith(".gpg"):
                        continue
                    passkey = file[:-len(".gpg")]
                    res[passkey] = passkey
                continue
            dico = res
            for key in rel_path.split(os.sep):
                if key not in dico:
                    dico[key] = {}
                dico = dico[key]
            for file in files:
                if not file.endswith(".gpg"):
                    continue
                passkey = file[:-len(".gpg")]
                key_rel_path = os.path.join(rel_path, passkey)
                dico[passkey] = key_rel_path
        print(res)
        return res

    def get_infos(self, key_rel_path):
        dico = {}
        infos = self.get_key(key_rel_path)
        splits = infos.split("\n")
        dico["PASSWORD"] = splits[0]
        seps = [": ", ":"]
        for i, info in enumerate(splits[1:]):
            if not len(info):
                continue
            for sep in seps:
                if sep in info:
                    split = info.split(sep)
                    dico[split[0]] = sep.join(split[1:])
                    break
            else:
                print(f"ERROR ON {key_rel_path}: No separator for line {i}: {info}")
        return dico

    def write_key(self, rel_path, infos):
        key_data = ""
        if "PASSWORD" in infos:
            key_data += infos["PASSWORD"] + "\n"
        for key, value in infos.items():
            if key == "PASSWORD":
                continue
            key_data += f"{key}: {value}\n"
        gpg_id_path = os.path.join(self.PYPASS_STORE_DIR, '.gpg-id')
        if not key_data.endswith('\n'):
            key_data += '\n'
        with open(gpg_id_path) as gpg_id_file:
            gpg_recipients = [line.rstrip('\n') for line in gpg_id_file]
        key_data_enc = GPG(gpgbinary=self.PYPASS_GPG_BIN).encrypt(key_data, gpg_recipients).data
        with open(os.path.join(self.PYPASS_STORE_DIR, rel_path + ".gpg"), 'wb') as key_file:
            key_file.write(key_data_enc)
