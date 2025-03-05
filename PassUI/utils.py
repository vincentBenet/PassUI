"""utils.py"""

import os
from pathlib import Path
import yaml


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


def rel_paths_gpg(path_abs_store, ignored_directories, ignored_files):
    """Build a dictionary of GPG paths

    Args:
        path_abs_store: Base path to password store
        ignored_directories: List of directories to ignore
        ignored_files: List of files to ignore

    Returns:
        dict: Dictionary of paths
    """
    # Start with a fresh, empty result dictionary
    res = {}

    # Convert ignored paths to absolute paths for comparison
    paths_ignored_directories = [
        os.path.join(path_abs_store, path_rel) for path_rel in ignored_directories]
    paths_ignored_files = [
        os.path.join(path_abs_store, path_rel) for path_rel in ignored_files]

    # Create a flat structure first to avoid conflicts
    file_entries = {}

    # Walk through the directory structure
    for root, dirs, files in os.walk(path_abs_store):
        # Skip ignored directories
        continue_ignored = False
        for path_abs_ignored in paths_ignored_directories:
            if root.startswith(path_abs_ignored):
                continue_ignored = True
                break
        if continue_ignored:
            continue

        # Get relative path to current directory
        rel_path = abs_to_rel_gpg(path_abs_store, root)

        # Handle files at root level
        if not rel_path:
            for file in files:
                if not file.endswith(".gpg"):
                    continue
                if os.path.join(root, file) in paths_ignored_files:
                    continue
                passkey = file[:-len(".gpg")]
                res[passkey] = passkey
            continue

        # Process .gpg files in current directory
        for file in files:
            if not file.endswith(".gpg"):
                continue
            if os.path.join(root, file) in paths_ignored_files:
                continue

            passkey = file[:-len(".gpg")]
            full_rel_path = os.path.join(rel_path, passkey)

            # Store path components and the full path for later processing
            path_parts = rel_path.split(os.sep)
            file_entries[full_rel_path] = {
                'path_parts': path_parts,
                'passkey': passkey
            }

    # Now build the nested structure from our flat entries
    for full_path, entry in file_entries.items():
        path_parts = entry['path_parts']
        passkey = entry['passkey']

        # Build directory structure
        current = res
        for part in path_parts:
            if part not in current:
                current[part] = {}
            if not isinstance(current[part], dict):
                # Skip if we encounter a file key instead of a directory
                break
            current = current[part]

        # Only add file if we successfully navigated to its directory
        if isinstance(current, dict):
            current[passkey] = full_path

    return res


def write_config(config):
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
