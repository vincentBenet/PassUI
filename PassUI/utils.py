import os
import gnupg
from pathlib import Path
import yaml


def write_gpg(path_abs_gpg, data_str, path_bin_gpg, gpg_keys_list):
    print("utils.write_gpg")
    print(f"\t{path_abs_gpg = }")
    print(f"\t{data_str = }")
    print(f"\t{path_bin_gpg = }")
    print(f"\t{gpg_keys_list = }")
    with open(path_abs_gpg, 'wb') as f:
        f.write(gnupg.GPG(gpgbinary=path_bin_gpg).encrypt(data_str, gpg_keys_list).data)


def read_gpg(path_abs_gpg, path_bin_gpg):
    print("utils.read_gpg")
    print(f"\t{path_abs_gpg = }")
    print(f"\t{path_bin_gpg = }")
    with open(path_abs_gpg, 'rb') as f:
        data_str = str(gnupg.GPG(gpgbinary=path_bin_gpg).decrypt_file(f))
    print(f"\tOUTPUT: {data_str = }")
    return data_str

def get_config_path():
    return Path.home() / "passui.yml"


def load_config():
    print("utils.load_config:")
    path_config = get_config_path()
    if os.path.isfile(path_config):
        print(f"\tReading user config at {path_config}")
        user_config = yaml.safe_load(Path(path_config).read_text())
    else:
        user_config = {}
    path_config_app = os.path.join(os.path.dirname(__file__), "data", "PassUI.yml")
    print(f"\tReading app config at {path_config_app}")
    app_config = yaml.safe_load(Path(path_config_app).read_text())
    config = app_config | user_config
    print("\tOUTPUT: config =")
    for key1 in app_config:
        print(f"\t\t{key1}")
        for key2 in app_config[key1]:
            c1 = user_config.get(key1, app_config[key1])
            value = c1.get(key2, app_config[key1][key2])
            config[key1][key2] = value
            print(f"\t\t\t{key2} = {value}")
    return config


def data_dict_to_str(data_dict):
    data_str = ""
    if "PASSWORD" in data_dict:
        data_str += data_dict["PASSWORD"] + "\n"
    for key, value in data_dict.items():
        if key == "PASSWORD":
            continue
        data_str += f"{key}: {value}\n"
    return data_str


def data_str_to_dict(data_str):
    splits = data_str.split("\n")
    data_dict = {"PASSWORD": splits[0]}
    seps = [": ", ":"]
    for i, info in enumerate(splits[1:]):
        if not len(info):
            continue
        for sep in seps:
            if sep in info:
                split = info.split(sep)
                data_dict[split[0]] = sep.join(split[1:])
                break
    return data_dict


def rel_to_abs(path_abs_store, path_rel):
    return os.path.join(path_abs_store, path_rel + ".gpg")


def abs_to_rel(path_abs_store, path_abs):
    return abs_to_rel_gpg(path_abs_store, path_abs)[:-len('.gpg')]


def abs_to_rel_gpg(path_abs_store, path_abs):
    return path_abs[len(path_abs_store)+1:]


def rel_paths_gpg(path_abs_store, path_rel_gitdir):
    res = {}
    path_abs_gitdir = os.path.join(path_abs_store, path_rel_gitdir)
    for root, dirs, files in os.walk(path_abs_store):
        if root.startswith(path_abs_gitdir):
            continue
        rel_path = abs_to_rel_gpg(path_abs_store, root)
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
    return res


def overwrite_config(config):
    path_config_user = get_config_path()
    with open(path_config_user, 'w') as outfile:
        print(f"Write user config at {path_config_user}:\n{config=}")
        yaml.dump(config, outfile, default_flow_style=False)


def new_incr(path_abs_dir, name, extension=""):
    i = 0
    while os.path.exists(path := os.path.join(path_abs_dir, key := f"{name}{'_'+str(i) if i > 0 else ''}{extension}")):
        i += 1
    if len(extension):
        key = key[:-len(extension)]
    return path, key

