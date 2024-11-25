import os
import re
import sys
import subprocess
import tempfile
import time
from tkinter import filedialog


class GPG:
    def __init__(self, gpg_exe="gpg"):
        self.gpg_exe = gpg_exe
        self.check_path_gpg()

    def check_path_gpg(self):
        if os.path.isfile(self.gpg_exe):
            return True
        print(f"GPG executable not found at {self.gpg_exe} with {sys.platform}")
        self.search_gpg_exe()
        while not os.path.isfile(self.gpg_exe):
            self.gpg_exe = filedialog.askopenfilename(
                initialdir="/",
                title="Select gpg.exe / gpg2.exe",
                filetypes=[("GPG executable", "gpg.exe gpg2.exe")]
            )

    def search_gpg_exe(self):
        if sys.platform == "win32":
            command = "where"
            argu = "gpg"
            output = subprocess.check_output(
                f"{command} {argu}", shell=True, encoding="437")
            paths = output.split("\n")
            for path in paths:
                path = path.replace("\r", "")
                if os.path.isfile(path):
                    self.gpg_exe = path
                    print(f"Get path of GPG at {self.gpg_exe}")
                    break
        else:
            command = "which"
            argu = "gpg"
            output = subprocess.check_output(
                f"{command} {argu}", shell=True, encoding="437")
            paths = output.split("\n")
            for path in paths:
                path = path.replace("\r", "")
                if os.path.isfile(path):
                    self.gpg_exe = path
                    break

    def run(self, commands, gpg_cmd=True):
        if isinstance(commands, str):
            commands = [commands]
        if gpg_cmd:
            commands = [self.gpg_exe] + commands
        # print(f"GPG:\n\t{commands = }")
        res = subprocess.check_output(commands, encoding="437")
        # print(f"\t{repr(res)}")
        return res

    def list_keys(self):
        str_list_keys = self.run("--list-secret-keys")
        filtered_header = "".join(str_list_keys.split("---------\n")[1:])
        str_keys = filtered_header.split("\n\n")[:-1]
        res = []
        for i, str_key in enumerate(str_keys):
            try:
                key_infos = {
                    "encryption": re.findall(r"(?<=  )(\S*)(?= )", str_key.split("\n")[0])[-1],
                    "created": re.findall(r"[0-9]+-[0-9]+-[0-9]+", str_key)[0],
                    "key": re.findall(r"(?<= )(\S*)(?=\nuid)", str_key)[0],
                    "trust": re.findall(r"(?<=\[)(.*)(?=\])", str_key.split("\n")[2])[0].replace(" ", ""),
                    "mail": re.findall(r"(?<=<)(.*@.*..*)(?=>)", str_key)[0],
                    "user": re.findall(r"(?<=\] )(.*)(?= <)", str_key)[0],
                    "expire": re.findall(r"[0-9]+-[0-9]+-[0-9]+", str_key)[-1],
                }
                res.append(key_infos)
            except IndexError:
                print("_"*50+f"\nERROR key {i}\n{str_key}\n"+"_"*50)
        return res

    def import_key(self, path_abs_gpg, passphrase=None):
        self.run([
            *(["--pinentry-mode=loopback", "--yes", "--passphrase", f'{passphrase}'] if passphrase is not None else []),
            "--allow-secret-key-import",
            "--import",
            path_abs_gpg
        ])

    def export_key(self, path_abs_gpg, key, passphrase=None):
        self.run([
            "--batch",
            "--output", path_abs_gpg,
            *(["--pinentry-mode=loopback", "--yes", "--passphrase", f'{passphrase}'] if passphrase is not None else []),
            "--export-secret-key", key,
        ])

    def create_key(self, name, mail, passphrase=None):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path_tmp = tmp.name
            tmp.write("\n".join([
                "Key-Type: 1",
                "Key-Length: 2048",
                "Subkey-Type: 1",
                "Subkey-Length: 2048",
                f"Name-Real: {name}",
                f"Name-Email: {mail}",
                f"Passphrase: {passphrase}" if passphrase is not None else "",
                # "Expire-Date: never",
            ]).encode())
        self.run(["--batch", "--gen-key", path_tmp])
        os.remove(path_tmp)

    def remove_key(self, keys=None):
        if keys is None:
            keys = []
        if not isinstance(keys, list):
            keys = [keys]
        for key in self.list_keys():
            key_id = key["key"]
            if key_id not in keys and len(keys):
                continue
            self.run([
                "--batch",
                "--yes",
                "--delete-secret-key",
                key_id
            ])

    def encrypt(self, path_abs_gpg, path_abs_file, disabled_keys=None, binary_file=False):
        if disabled_keys is None:
            disabled_keys = []
        recipients = []
        for key in self.list_keys():
            if key["key"] in disabled_keys:
                continue
            recipients.append("--recipient")
            recipients.append(key["key"])
        self.run([
            "--batch", "--yes",
            "--output", path_abs_gpg,
            *(["--armor"] if not binary_file else []),
            "--encrypt",
            *recipients,
            path_abs_file
        ])

    def write(self, path_abs_gpg, data_str, passphrase=None, disabled_keys=None):
        path_abs_dir = os.path.dirname(path_abs_gpg)
        os.makedirs(path_abs_dir, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(delete=False)
        path_data = tmp.name
        tmp.write(data_str.encode())
        tmp.close()
        self.encrypt(path_abs_gpg, path_data, disabled_keys)
        tmp = open(path_data, "w")
        tmp.write("")
        tmp.close()
        os.remove(path_data)

    def read(self, path_abs_gpg, passphrase=None):
        return self.run([
            *(["--pinentry-mode=loopback", "--passphrase", f"{passphrase}"] if passphrase is not None else []),
            "--decrypt", path_abs_gpg,
            *(),
        ])

    def decrypt(self, path_abs_source, path_abs_dest):
        self.run([
            "--output", path_abs_dest,
            "--decrypt", path_abs_source,
        ])
